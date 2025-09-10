"""End-to-end tests for MCP server functionality."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import requests

from reviewer.mcp.protocol import JSONRPCProtocol


class MCPTestClient:
    """Test client for interacting with MCP server."""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.request_id = 0
    
    def send_request(self, method: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Send an MCP request and return the response."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/mcp",
                json=request,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def initialize(self) -> bool:
        """Initialize the MCP connection."""
        response = self.send_request(
            "initialize",
            {
                "protocolVersion": "1.0.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        )
        return response is not None and "result" in response
    
    def list_tools(self) -> Optional[Dict[str, Any]]:
        """List available tools."""
        response = self.send_request("tools/list", {})
        return response.get("result") if response else None
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call a tool with arguments."""
        response = self.send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments}
        )
        return response.get("result") if response else None


@pytest.fixture
def mcp_server_process(monkeypatch):
    """Start the MCP server as a subprocess."""
    # Set test environment variables
    monkeypatch.setenv("LLM_REVIEW_SERVICE_HOST", "localhost")
    monkeypatch.setenv("LLM_REVIEW_SERVICE_PORT", "8765")
    
    # Start the MCP server
    server_process = subprocess.Popen(
        [sys.executable, "-m", "llm_review.mcp_server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(2)
    
    # Verify server is running
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8765/health", timeout=1)
            if response.status_code == 200:
                break
        except:
            if i == max_retries - 1:
                server_process.terminate()
                pytest.fail("MCP server failed to start")
            time.sleep(0.5)
    
    yield server_process
    
    # Cleanup
    server_process.terminate()
    server_process.wait(timeout=5)


@pytest.fixture
def service_process():
    """Start the review service."""
    # Start the service
    service_process = subprocess.Popen(
        [sys.executable, "-m", "llm_review.service"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for service to start
    time.sleep(2)
    
    # Verify service is running
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8080/health", timeout=1)
            if response.status_code == 200:
                break
        except:
            if i == max_retries - 1:
                service_process.terminate()
                pytest.fail("Review service failed to start")
            time.sleep(0.5)
    
    yield service_process
    
    # Cleanup
    service_process.terminate()
    service_process.wait(timeout=5)


class TestE2EMCPServer:
    """End-to-end tests for MCP server functionality."""
    
    @pytest.mark.integration
    def test_mcp_server_basic_flow(self, mcp_server_process, service_process):
        """Test basic MCP server flow: initialize, list tools, and verify response."""
        client = MCPTestClient()
        
        # Initialize connection
        assert client.initialize(), "Failed to initialize MCP connection"
        
        # List available tools
        tools_result = client.list_tools()
        assert tools_result is not None, "Failed to list tools"
        assert "tools" in tools_result, "No tools array in response"
        assert len(tools_result["tools"]) > 0, "No tools available"
        
        # Verify expected tools are present
        tool_names = [tool["name"] for tool in tools_result["tools"]]
        expected_tools = [
            "review_changes",
            "list_review_sessions",
            "manage_review_service",
            "get_session_details",
            "clear_session"
        ]
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not found"
    
    @pytest.mark.integration
    def test_mcp_review_changes_tool(self, temp_git_repo, mcp_server_process, service_process, mock_gemini_for_e2e):
        """Test the review_changes tool through MCP."""
        repo_path = temp_git_repo
        
        # Create a Python file with an issue
        test_file = repo_path / "test_security.py"
        test_file.write_text("""
import subprocess

def run_command(user_input):
    # Security issue: command injection
    subprocess.run(user_input, shell=True)
    
def another_function():
    pass
""")
        
        # Stage the file
        subprocess.run(["git", "add", "test_security.py"], cwd=repo_path, check=True)
        
        # Initialize MCP client
        client = MCPTestClient()
        assert client.initialize()
        
        # Call review_changes tool
        result = client.call_tool(
            "review_changes",
            {
                "directory": str(repo_path),
                "mode": "critical",
                "output_format": "compact",
                "no_session": True
            }
        )
        
        assert result is not None, "Failed to call review_changes tool"
        assert "content" in result, "No content in response"
        assert len(result["content"]) > 0, "No content returned"
        
        # Verify the review found the security issue
        review_text = result["content"][0]["text"]
        assert "security" in review_text.lower() or "injection" in review_text.lower(), \
            "Review did not identify security issue"
    
    @pytest.mark.integration
    def test_mcp_session_management(self, temp_git_repo, mcp_server_process, service_process, mock_gemini_for_e2e):
        """Test session management through MCP: create, list, and clear sessions."""
        repo_path = temp_git_repo
        session_name = "test-mcp-session"
        
        # Create a simple file
        test_file = repo_path / "simple.py"
        test_file.write_text("def hello(): return 'world'")
        subprocess.run(["git", "add", "simple.py"], cwd=repo_path, check=True)
        
        # Initialize MCP client
        client = MCPTestClient()
        assert client.initialize()
        
        # Create a session by running a review
        result = client.call_tool(
            "review_changes",
            {
                "directory": str(repo_path),
                "session_name": session_name,
                "mode": "critical"
            }
        )
        assert result is not None, "Failed to create session"
        
        # List sessions
        list_result = client.call_tool("list_review_sessions", {})
        assert list_result is not None, "Failed to list sessions"
        sessions_text = list_result["content"][0]["text"]
        assert session_name in sessions_text, "Session not found in list"
        
        # Get session details
        details_result = client.call_tool(
            "get_session_details",
            {
                "session_name": session_name,
                "project_root": str(repo_path)
            }
        )
        assert details_result is not None, "Failed to get session details"
        details_text = details_result["content"][0]["text"]
        assert "Created:" in details_text, "Session details missing creation time"
        
        # Clear the session
        clear_result = client.call_tool(
            "clear_session",
            {
                "session_name": session_name,
                "project_root": str(repo_path),
                "confirm": True
            }
        )
        assert clear_result is not None, "Failed to clear session"
        assert "deleted successfully" in clear_result["content"][0]["text"], "Session not deleted"
        
        # Verify session is gone
        list_result2 = client.call_tool("list_review_sessions", {})
        if list_result2:
            sessions_text2 = list_result2["content"][0]["text"]
            assert session_name not in sessions_text2, "Session still exists after deletion"
    
    @pytest.mark.integration
    def test_mcp_service_management(self, mcp_server_process, service_process):
        """Test service management through MCP."""
        client = MCPTestClient()
        assert client.initialize()
        
        # Check service status
        status_result = client.call_tool(
            "manage_review_service",
            {"action": "status"}
        )
        assert status_result is not None, "Failed to get service status"
        status_text = status_result["content"][0]["text"]
        assert "running" in status_text.lower(), "Service not reported as running"
        
        # Get service logs
        logs_result = client.call_tool(
            "manage_review_service",
            {"action": "logs", "tail_lines": 10}
        )
        assert logs_result is not None, "Failed to get service logs"
        assert len(logs_result["content"][0]["text"]) > 0, "No logs returned"
    
    @pytest.mark.integration
    def test_mcp_error_handling(self, mcp_server_process, service_process):
        """Test MCP server error handling."""
        client = MCPTestClient()
        assert client.initialize()
        
        # Test with invalid directory
        result = client.call_tool(
            "review_changes",
            {
                "directory": "/nonexistent/path",
                "no_session": True
            }
        )
        assert result is not None, "Should return error result"
        error_text = result["content"][0]["text"]
        assert "error" in error_text.lower() or "failed" in error_text.lower(), \
            "Error not properly reported"
        
        # Test with invalid tool name
        response = client.send_request(
            "tools/call",
            {"name": "nonexistent_tool", "arguments": {}}
        )
        # The server should return an error
        assert response is not None, "Should return response"
        assert "error" in response, "Should have error field"
    
    @pytest.mark.integration
    def test_mcp_concurrent_clients(self, temp_git_repo, mcp_server_process, service_process, mock_gemini_for_e2e):
        """Test MCP server handles multiple concurrent clients."""
        import threading
        import queue
        
        repo_path = temp_git_repo
        
        # Create a test file
        test_file = repo_path / "concurrent.py"
        test_file.write_text("def test(): pass")
        subprocess.run(["git", "add", "concurrent.py"], cwd=repo_path, check=True)
        
        results_queue = queue.Queue()
        
        def client_worker(client_id: int):
            """Worker function for concurrent client."""
            client = MCPTestClient()
            
            try:
                # Initialize
                if not client.initialize():
                    results_queue.put((client_id, "init_failed", None))
                    return
                
                # Call review
                result = client.call_tool(
                    "review_changes",
                    {
                        "directory": str(repo_path),
                        "no_session": True,
                        "session_name": f"client-{client_id}"
                    }
                )
                
                if result:
                    results_queue.put((client_id, "success", result))
                else:
                    results_queue.put((client_id, "failed", None))
                    
            except Exception as e:
                results_queue.put((client_id, "error", str(e)))
        
        # Start multiple client threads
        threads = []
        num_clients = 3
        
        for i in range(num_clients):
            thread = threading.Thread(target=client_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Check results
        successful_clients = 0
        while not results_queue.empty():
            client_id, status, result = results_queue.get()
            if status == "success":
                successful_clients += 1
            else:
                print(f"Client {client_id} failed with status: {status}")
        
        assert successful_clients == num_clients, \
            f"Only {successful_clients}/{num_clients} clients succeeded"