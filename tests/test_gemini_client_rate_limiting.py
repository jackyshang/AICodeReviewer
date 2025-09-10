"""Tests for GeminiClient rate limiting functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from reviewer.gemini_client import GeminiClient
from reviewer.rate_limiter import RateLimiter


class TestGeminiClientRateLimiting:
    """Test rate limiting integration in GeminiClient."""
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiting_enabled_by_default(self, mock_manager, mock_genai_client):
        """Test that rate limiting is enabled by default."""
        # Setup mock rate limiter
        mock_limiter = Mock(spec=RateLimiter)
        mock_manager.get_limiter.return_value = mock_limiter
        
        # Create client
        client = GeminiClient(api_key="test-key")
        
        # Verify rate limiter was created
        assert client.enable_rate_limiting is True
        assert client.rate_limiter == mock_limiter
        mock_manager.get_limiter.assert_called_once_with("gemini-2.5-pro")
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiting_can_be_disabled(self, mock_manager, mock_genai_client):
        """Test that rate limiting can be disabled."""
        # Create client with rate limiting disabled
        client = GeminiClient(api_key="test-key", enable_rate_limiting=False)
        
        # Verify rate limiter was not created
        assert client.enable_rate_limiting is False
        assert not hasattr(client, 'rate_limiter')
        mock_manager.get_limiter.assert_not_called()
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiter_acquire_success(self, mock_manager, mock_genai_client):
        """Test successful token acquisition from rate limiter."""
        # Setup mock rate limiter
        mock_limiter = Mock(spec=RateLimiter)
        mock_limiter.acquire.return_value = True
        mock_limiter.available_tokens.return_value = 5.0
        mock_manager.get_limiter.return_value = mock_limiter
        
        # Setup mock navigation tools
        mock_nav_tools = Mock()
        
        # Setup mock chat
        mock_chat = Mock()
        mock_response = Mock()
        mock_response.function_calls = []  # No function calls, so it exits loop
        mock_response.text = "Test review"
        # Mock usage metadata
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150
        mock_chat.send_message.return_value = mock_response
        mock_genai_client.return_value.chats.create.return_value = mock_chat
        
        # Create client and setup
        client = GeminiClient(api_key="test-key", debug=False)
        client.setup_navigation_tools(mock_nav_tools)
        
        # Call review_code
        result = client.review_code("test context")
        
        # Verify rate limiter was called
        mock_limiter.acquire.assert_called_once_with(timeout=30.0)
        assert result['review_content'] == "Test review"
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiter_acquire_timeout(self, mock_manager, mock_genai_client):
        """Test rate limiter timeout raises RuntimeError."""
        # Setup mock rate limiter that times out
        mock_limiter = Mock(spec=RateLimiter)
        mock_limiter.acquire.return_value = False  # Timeout
        mock_manager.get_limiter.return_value = mock_limiter
        
        # Setup mock navigation tools
        mock_nav_tools = Mock()
        
        # Create client and setup
        client = GeminiClient(api_key="test-key")
        client.setup_navigation_tools(mock_nav_tools)
        
        # Call review_code and expect RuntimeError
        with pytest.raises(RuntimeError, match="Rate limit timeout for gemini-2.5-pro"):
            client.review_code("test context")
        
        # Verify rate limiter was called
        mock_limiter.acquire.assert_called_once_with(timeout=30.0)
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiting_disabled_skips_acquire(self, mock_manager, mock_genai_client):
        """Test that disabled rate limiting skips token acquisition."""
        # Setup mock chat
        mock_chat = Mock()
        mock_response = Mock()
        mock_response.function_calls = []  # No function calls
        mock_response.text = "Test review"
        # Mock usage metadata
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150
        mock_chat.send_message.return_value = mock_response
        mock_genai_client.return_value.chats.create.return_value = mock_chat
        
        # Setup mock navigation tools
        mock_nav_tools = Mock()
        
        # Create client with rate limiting disabled
        client = GeminiClient(api_key="test-key", enable_rate_limiting=False)
        client.setup_navigation_tools(mock_nav_tools)
        
        # Call review_code
        result = client.review_code("test context")
        
        # Verify rate limiter was never used
        mock_manager.get_limiter.assert_not_called()
        assert result['review_content'] == "Test review"
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiting_with_debug_logging(self, mock_manager, mock_genai_client):
        """Test debug logging during rate limiting."""
        # Setup mock rate limiter
        mock_limiter = Mock(spec=RateLimiter)
        mock_limiter.acquire.return_value = True
        mock_limiter.available_tokens.return_value = 10.5
        mock_manager.get_limiter.return_value = mock_limiter
        
        # Setup mock navigation tools
        mock_nav_tools = Mock()
        
        # Setup mock chat
        mock_chat = Mock()
        mock_response = Mock()
        mock_response.function_calls = []
        mock_response.text = "Test review"
        # Mock usage metadata
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.usage_metadata.total_token_count = 150
        mock_chat.send_message.return_value = mock_response
        mock_genai_client.return_value.chats.create.return_value = mock_chat
        
        # Create client with debug enabled
        client = GeminiClient(api_key="test-key", debug=True)
        client.setup_navigation_tools(mock_nav_tools)
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            result = client.review_code("test context")
        
        # Verify debug messages were printed
        debug_calls = [call for call in mock_print.call_args_list if 'rate limit' in str(call).lower()]
        assert len(debug_calls) >= 2  # Should have "acquiring" and "acquired" messages
        
        # Verify rate limiter was called
        mock_limiter.acquire.assert_called_once_with(timeout=30.0)
        mock_limiter.available_tokens.assert_called_once()
    
    @patch('reviewer.gemini_client.genai.Client')
    @patch('reviewer.gemini_client._rate_limit_manager')
    def test_rate_limiting_on_function_responses(self, mock_manager, mock_genai_client):
        """Test rate limiting is applied before sending function responses."""
        # Setup mock rate limiter
        mock_limiter = Mock(spec=RateLimiter)
        mock_limiter.acquire.side_effect = [True, True]  # Success for both calls
        mock_limiter.available_tokens.return_value = 5.0
        mock_manager.get_limiter.return_value = mock_limiter
        
        # Setup mock navigation tools
        mock_nav_tools = Mock()
        mock_nav_tools.read_file.return_value = "file content"
        
        # Setup tool
        mock_tool = Mock()
        
        # Setup mock chat with function calls
        mock_chat = Mock()
        
        # First response has function calls
        mock_response1 = Mock()
        mock_function_call = Mock()
        mock_function_call.name = "read_file"
        mock_function_call.args = {"filepath": "test.py"}
        mock_response1.function_calls = [mock_function_call]
        # Mock usage metadata for first response
        mock_response1.usage_metadata = Mock()
        mock_response1.usage_metadata.prompt_token_count = 100
        mock_response1.usage_metadata.candidates_token_count = 50
        mock_response1.usage_metadata.total_token_count = 150
        
        # Second response has no function calls
        mock_response2 = Mock()
        mock_response2.function_calls = []
        mock_response2.text = "Test review"
        # Mock usage metadata for second response
        mock_response2.usage_metadata = Mock()
        mock_response2.usage_metadata.prompt_token_count = 80
        mock_response2.usage_metadata.candidates_token_count = 40
        mock_response2.usage_metadata.total_token_count = 120
        
        mock_chat.send_message.side_effect = [mock_response1, mock_response2]
        mock_genai_client.return_value.chats.create.return_value = mock_chat
        
        # Create client
        client = GeminiClient(api_key="test-key")
        client.setup_navigation_tools(mock_nav_tools)
        client.tool = mock_tool  # Set the tool directly
        
        # Call review_code
        result = client.review_code("test context")
        
        # Verify rate limiter was called twice (initial + function response)
        assert mock_limiter.acquire.call_count == 2
        assert result['review_content'] == "Test review"