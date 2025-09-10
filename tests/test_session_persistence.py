"""Tests for session persistence functionality."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from fastapi.testclient import TestClient

from reviewer.service import ReviewerService, ReviewRequest
from reviewer.cli import SessionAwareGeminiClient, check_service_available, list_active_sessions


class TestService:
    """Test the session persistence service."""
    
    @pytest.fixture
    def service(self):
        """Create a test service instance."""
        service = ReviewerService()
        return service
    
    @pytest.fixture
    def client(self, service):
        """Create a test client for the service."""
        return TestClient(service.app)
    
    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "active_sessions" in data
        assert "timestamp" in data
        assert "uptime" in data
        assert isinstance(data["uptime"], (int, float))
        assert data["uptime"] > 0
    
    def test_list_sessions_empty(self, client):
        """Test listing sessions when none exist."""
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
    
    def test_get_session_not_found(self, client):
        """Test getting a non-existent session."""
        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_clear_session_not_found(self, client):
        """Test clearing a non-existent session."""
        response = client.delete("/sessions/nonexistent")
        assert response.status_code == 404
    
    @patch('llm_review.service.GeminiClient')
    @patch('llm_review.service.CodebaseIndexer')
    @patch('llm_review.service.NavigationTools')
    def test_create_new_session(self, mock_nav_tools, mock_indexer, mock_gemini, client):
        """Test creating a new review session."""
        import tempfile
        import os
        
        # Create a real temp directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini_instance.format_initial_context.return_value = "Test context"
            mock_gemini_instance.review_code.return_value = {
                'review_content': 'Test review',
                'navigation_history': [],
                'iterations': 1,
                'token_details': {'total_tokens': 100}
            }
            mock_gemini_instance.chat = Mock()
            mock_gemini_instance.chat.get_history.return_value = []
            mock_gemini.return_value = mock_gemini_instance
            
            mock_indexer_instance = Mock()
            mock_indexer_instance.build_index.return_value = {}
            mock_indexer.return_value = mock_indexer_instance
            
            # Make request with real temp directory
            request_data = {
                "session_name": "test-feature",
                "project_root": tmpdir,
                "initial_context": "Review this",
                "codebase_summary": "Test codebase",
                "changed_files": {"modified": ["test.py"]},
                "diffs": {"test.py": "diff content"}
            }
            
            response = client.post("/review", json=request_data)
            if response.status_code != 200:
                print(f"Error response: {response.json()}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["session_info"]["name"] == "test-feature"
            assert data["session_info"]["status"] == "new"
            assert data["session_info"]["iteration"] == 1
    
    @patch('llm_review.service.GeminiClient')
    @patch('llm_review.service.CodebaseIndexer')
    @patch('llm_review.service.NavigationTools')
    def test_continue_session(self, mock_nav_tools, mock_indexer, mock_gemini, client):
        """Test continuing an existing session."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini_instance.format_initial_context.return_value = "Test context"
            mock_gemini_instance.review_code.return_value = {
                'review_content': 'Test review 2',
                'navigation_history': [],
                'iterations': 1,
                'token_details': {'total_tokens': 150}
            }
            mock_gemini_instance.chat = Mock()
            mock_gemini_instance.chat.get_history.return_value = []
            mock_gemini.return_value = mock_gemini_instance
            
            mock_indexer_instance = Mock()
            mock_indexer_instance.build_index.return_value = {}
            mock_indexer.return_value = mock_indexer_instance
            
            request_data = {
                "session_name": "test-feature",
                "project_root": tmpdir,
                "initial_context": "Review this",
                "codebase_summary": "Test codebase",
                "changed_files": {"modified": ["test.py"]},
                "diffs": {"test.py": "diff content"}
            }
        
            # First request - creates session
            response1 = client.post("/review", json=request_data)
            assert response1.status_code == 200
            assert response1.json()["session_info"]["status"] == "new"
            
            # Second request - continues session
            response2 = client.post("/review", json=request_data)
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["session_info"]["status"] == "continued"
            assert data2["session_info"]["iteration"] == 2
    
    def test_project_scoped_sessions(self, client):
        """Test that sessions are scoped to projects."""
        import tempfile
        
        # Create mock that returns an existing client from active_sessions
        with patch('llm_review.service.GeminiClient') as mock_gemini, \
             patch('llm_review.service.CodebaseIndexer') as mock_indexer, \
             patch('llm_review.service.NavigationTools'), \
             tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:
            
            mock_gemini_instance = Mock()
            mock_gemini_instance.format_initial_context.return_value = "Test context"
            mock_gemini_instance.review_code.return_value = {
                'review_content': 'Test review',
                'navigation_history': [],
                'iterations': 1,
                'token_details': {'total_tokens': 100}
            }
            mock_gemini_instance.chat = Mock()
            mock_gemini_instance.chat.get_history.return_value = []
            mock_gemini.return_value = mock_gemini_instance
            
            mock_indexer_instance = Mock()
            mock_indexer_instance.build_index.return_value = {}
            mock_indexer.return_value = mock_indexer_instance
            
            # Same session name, different projects
            request1 = {
                "session_name": "feature-x",
                "project_root": tmpdir1,
                "initial_context": "Review",
                "codebase_summary": "Test",
                "changed_files": {},
                "diffs": {}
            }
            
            request2 = {
                "session_name": "feature-x",
                "project_root": tmpdir2,
                "initial_context": "Review",
                "codebase_summary": "Test",
                "changed_files": {},
                "diffs": {}
            }
            
            # Both should create new sessions (not reuse)
            response1 = client.post("/review", json=request1)
            assert response1.json()["session_info"]["status"] == "new"
            
            response2 = client.post("/review", json=request2)
            assert response2.json()["session_info"]["status"] == "new"  # Not continued!


class TestCLI:
    """Test CLI session functionality."""
    
    def test_check_service_available_running(self):
        """Test checking if service is available when running."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            assert check_service_available() is True
    
    def test_check_service_available_not_running(self):
        """Test checking if service is available when not running."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")
            assert check_service_available() is False
    
    @patch('llm_review.cli.check_service_available')
    @patch('requests.get')
    def test_list_active_sessions(self, mock_get, mock_check, capsys):
        """Test listing active sessions."""
        mock_check.return_value = True
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "sessions": [
                {
                    "name": "test-feature",
                    "iteration": 2,
                    "last_reviewed": "2024-01-06T10:00:00"
                }
            ]
        }
        
        list_active_sessions()
        captured = capsys.readouterr()
        assert "test-feature" in captured.out
        assert "iteration 2" in captured.out
    
    @patch('llm_review.cli.check_service_available')
    def test_list_active_sessions_no_service(self, mock_check, capsys):
        """Test listing sessions when service is not running."""
        mock_check.return_value = False
        list_active_sessions()
        captured = capsys.readouterr()
        assert "service is not running" in captured.out.lower()
    
    def test_session_aware_client_init(self):
        """Test SessionAwareGeminiClient initialization."""
        client = SessionAwareGeminiClient(
            session_name="test",
            model_name="gemini-2.5-pro",
            debug=False
        )
        assert client.session_name == "test"
        assert client.kwargs["model_name"] == "gemini-2.5-pro"
    
    def test_session_aware_client_format_context(self):
        """Test SessionAwareGeminiClient format_initial_context."""
        client = SessionAwareGeminiClient("test")
        context = client.format_initial_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test",
            diffs={"test.py": "diff"}
        )
        assert context == "Session-based review"
        assert hasattr(client, 'changed_files')
        assert hasattr(client, 'diffs')
    
    @patch('requests.post')
    def test_session_aware_client_review_new_session(self, mock_post):
        """Test SessionAwareGeminiClient review with new session."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session_info": {
                "name": "test",
                "status": "new",
                "iteration": 1,
                "chat_messages_count": 0,
                "last_reviewed": "2024-01-06T10:00:00Z"
            },
            "review_result": {"review_content": "Test review"}
        }
        mock_post.return_value = mock_response
        
        client = SessionAwareGeminiClient("test")
        client.nav_tools = Mock(repo_path="/test/repo")
        
        result = client.review_code("Test context")
        assert result["review_content"] == "Test review"
    
    @patch('requests.post')
    def test_session_aware_client_review_continued_session(self, mock_post, capsys):
        """Test SessionAwareGeminiClient review with continued session."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session_info": {
                "name": "test",
                "status": "continued",
                "iteration": 2,
                "chat_messages_count": 15,
                "last_reviewed": "2024-01-06T09:30:00Z",
                "previous_issues_count": 3
            },
            "review_result": {"review_content": "Test review 2"}
        }
        mock_post.return_value = mock_response
        
        client = SessionAwareGeminiClient("test")
        client.nav_tools = Mock(repo_path="/test/repo")
        
        result = client.review_code("Test context")
        captured = capsys.readouterr()
        
        assert "CONTINUING review session" in captured.out
        assert "iteration 2" in captured.out
        assert result["review_content"] == "Test review 2"
    
    def test_format_time_ago(self):
        """Test time formatting in SessionAwareGeminiClient."""
        client = SessionAwareGeminiClient("test")
        
        # Test various time formats
        now = datetime.now().isoformat()
        assert client._format_time_ago(now) == "just now"
        
        # Test invalid format
        assert client._format_time_ago("invalid") == "invalid"
    
    @patch('requests.post')
    def test_session_aware_client_connection_error_fallback(self, mock_post):
        """Test SessionAwareGeminiClient handles connection errors gracefully."""
        from requests.exceptions import ConnectionError
        
        # Mock connection error
        mock_post.side_effect = ConnectionError("Service unavailable")
        
        client = SessionAwareGeminiClient("test")
        client.nav_tools = Mock(repo_path="/test/repo")
        
        # Should return None to signal fallback needed
        result = client.review_code("Test context")
        assert result is None
    
