"""Tests for MCP protocol handling."""

import pytest
import json
from reviewer.mcp.protocol import JSONRPCProtocol


class TestJSONRPCProtocol:
    """Test JSON-RPC protocol handling."""
    
    def test_parse_valid_message(self):
        """Test parsing valid JSON-RPC message."""
        protocol = JSONRPCProtocol()
        message = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
        
        parsed = protocol.parse_message(message)
        assert parsed is not None
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["method"] == "initialize"
        
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        protocol = JSONRPCProtocol()
        message = '{"invalid json'
        
        parsed = protocol.parse_message(message)
        assert parsed is None
        
    def test_parse_wrong_version(self):
        """Test parsing message with wrong JSON-RPC version."""
        protocol = JSONRPCProtocol()
        message = '{"jsonrpc": "1.0", "id": 1, "method": "test"}'
        
        parsed = protocol.parse_message(message)
        assert parsed is None
        
    def test_extract_multiple_messages(self):
        """Test extracting multiple messages from stream."""
        protocol = JSONRPCProtocol()
        
        data = '{"jsonrpc": "2.0", "id": 1, "method": "test1"}\n{"jsonrpc": "2.0", "id": 2, "method": "test2"}\n'
        messages = protocol.extract_messages(data)
        
        assert len(messages) == 2
        assert messages[0]["id"] == 1
        assert messages[1]["id"] == 2
        
    def test_extract_partial_message(self):
        """Test handling partial messages."""
        protocol = JSONRPCProtocol()
        
        # Send partial message
        messages = protocol.extract_messages('{"jsonrpc": "2.0", "id": 1, ')
        assert len(messages) == 0
        # The buffer may have stripped spaces, so check the content exists
        assert '{"jsonrpc": "2.0", "id": 1,' in protocol.buffer
        
        # Complete the message
        messages = protocol.extract_messages('"method": "test"}\n')
        assert len(messages) == 1
        assert messages[0]["method"] == "test"
        assert protocol.buffer == ""
        
    def test_create_response(self):
        """Test creating JSON-RPC response."""
        protocol = JSONRPCProtocol()
        response = protocol.create_response(123, {"result": "success"})
        
        parsed = json.loads(response)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 123
        assert parsed["result"]["result"] == "success"
        
    def test_create_error(self):
        """Test creating JSON-RPC error response."""
        protocol = JSONRPCProtocol()
        response = protocol.create_error(456, -32600, "Invalid Request", {"details": "test"})
        
        parsed = json.loads(response)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 456
        assert parsed["error"]["code"] == -32600
        assert parsed["error"]["message"] == "Invalid Request"
        assert parsed["error"]["data"]["details"] == "test"
        
    def test_create_notification(self):
        """Test creating JSON-RPC notification."""
        protocol = JSONRPCProtocol()
        notification = protocol.create_notification("progress", {"percent": 50})
        
        parsed = json.loads(notification)
        assert parsed["jsonrpc"] == "2.0"
        assert "id" not in parsed  # Notifications have no id
        assert parsed["method"] == "progress"
        assert parsed["params"]["percent"] == 50