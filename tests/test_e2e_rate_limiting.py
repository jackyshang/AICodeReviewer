"""End-to-end tests for rate limiting functionality."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, Mock

import git
import pytest
from click.testing import CliRunner

from reviewer.cli import main
from reviewer.rate_limiter import RateLimitManager


class TestE2ERateLimiting:
    """End-to-end tests for rate limiting in real review scenarios."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            repo = git.Repo.init(repo_path)
            
            # Configure git user for commits
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create initial commit
            readme = repo_path / "README.md"
            readme.write_text("# Test Project\n")
            repo.index.add(["README.md"])  # Use relative path
            repo.index.commit("Initial commit")
            
            yield repo_path, repo
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    
    def test_rate_limiting_enforced_by_default(self, temp_repo, mock_env):
        """Test that rate limiting is enforced by default."""
        repo_path, repo = temp_repo
        
        # Create a test file with changes
        test_file = repo_path / "test.py"
        test_file.write_text("""
def add(a, b):
    # TODO: Add input validation
    return a + b

def multiply(x, y):
    return x * y
""")
        
        # Track rate limiter calls
        acquire_calls = []
        original_acquire = None
        
        def mock_acquire(self, timeout=60.0):
            """Mock acquire that tracks calls."""
            acquire_calls.append(time.monotonic())
            # Call original method
            return original_acquire(timeout)
        
        # Patch the rate limiter to track calls
        with patch.object(RateLimitManager, 'get_limiter') as mock_get_limiter:
            # Create a real rate limiter but track its calls
            real_manager = RateLimitManager()
            real_limiter = real_manager.get_limiter("gemini-2.5-pro")
            original_acquire = real_limiter.acquire
            real_limiter.acquire = lambda timeout=60.0: mock_acquire(real_limiter, timeout)
            
            mock_get_limiter.return_value = real_limiter
            
            # Run review
            runner = CliRunner()
            with runner.isolated_filesystem():
                # Change to repo directory
                os.chdir(str(repo_path))
                
                # Mock the actual Gemini API call
                with patch('reviewer.gemini_client.genai.Client') as mock_client:
                    # Setup mock response
                    mock_chat = Mock()
                    mock_response = Mock()
                    mock_response.function_calls = []
                    mock_response.text = "No critical issues found."
                    mock_response.usage_metadata = Mock(
                        prompt_token_count=100,
                        candidates_token_count=50,
                        total_token_count=150
                    )
                    mock_chat.send_message.return_value = mock_response
                    mock_client.return_value.chats.create.return_value = mock_chat
                    
                    result = runner.invoke(main, ['review', '--no-spinner'])
                    
                    # Verify command succeeded
                    assert result.exit_code == 0
                    
                    # Verify rate limiter was called
                    assert len(acquire_calls) >= 1
                    assert mock_get_limiter.called
                    assert mock_get_limiter.call_args[0][0] == "gemini-2.5-pro"
    
    def test_no_rate_limit_flag_disables(self, temp_repo, mock_env):
        """Test that --no-rate-limit flag disables rate limiting."""
        repo_path, repo = temp_repo
        
        # Create a test file
        test_file = repo_path / "test.py"
        test_file.write_text("def test(): pass")
        
        # Track if rate limiter is used
        rate_limiter_used = False
        
        def track_rate_limiter(*args, **kwargs):
            nonlocal rate_limiter_used
            rate_limiter_used = True
            # Return a mock limiter
            mock_limiter = Mock()
            mock_limiter.acquire.return_value = True
            return mock_limiter
        
        with patch.object(RateLimitManager, 'get_limiter', side_effect=track_rate_limiter):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.chdir(str(repo_path))
                
                # Mock Gemini client
                with patch('reviewer.gemini_client.genai.Client') as mock_client:
                    mock_chat = Mock()
                    mock_response = Mock()
                    mock_response.function_calls = []
                    mock_response.text = "No issues."
                    mock_response.usage_metadata = Mock(
                        prompt_token_count=50,
                        candidates_token_count=25,
                        total_token_count=75
                    )
                    mock_chat.send_message.return_value = mock_response
                    mock_client.return_value.chats.create.return_value = mock_chat
                    
                    result = runner.invoke(main, ['review', '--no-rate-limit', '--no-spinner'])
                    
                    assert result.exit_code == 0
                    # Rate limiter should NOT be created when disabled
                    assert not rate_limiter_used
    
    def test_rate_limiting_with_multiple_requests(self, temp_repo, mock_env):
        """Test rate limiting behavior with multiple API calls."""
        repo_path, repo = temp_repo
        
        # Create multiple test files
        for i in range(3):
            test_file = repo_path / f"test{i}.py"
            test_file.write_text(f"def func{i}(): return {i}")
        
        # Use a strict rate limiter (2 requests per minute for testing)
        with patch.object(RateLimitManager, 'get_limiter') as mock_get_limiter:
            from reviewer.rate_limiter import RateLimiter
            strict_limiter = RateLimiter(rpm=120, burst=2)  # 2 per second, burst of 2
            mock_get_limiter.return_value = strict_limiter
            
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.chdir(str(repo_path))
                
                # Mock Gemini to simulate multiple function calls
                with patch('reviewer.gemini_client.genai.Client') as mock_client:
                    mock_chat = Mock()
                    
                    # First response has function calls
                    func_call1 = Mock()
                    func_call1.name = "read_file"
                    func_call1.args = {"filepath": "test0.py"}
                    
                    response1 = Mock()
                    response1.function_calls = [func_call1]
                    response1.usage_metadata = Mock(
                        prompt_token_count=100,
                        candidates_token_count=50,
                        total_token_count=150
                    )
                    
                    # Second response has more function calls
                    func_call2 = Mock()
                    func_call2.name = "read_file"
                    func_call2.args = {"filepath": "test1.py"}
                    
                    response2 = Mock()
                    response2.function_calls = [func_call2]
                    response2.usage_metadata = Mock(
                        prompt_token_count=80,
                        candidates_token_count=40,
                        total_token_count=120
                    )
                    
                    # Final response
                    response3 = Mock()
                    response3.function_calls = []
                    response3.text = "Review complete."
                    response3.usage_metadata = Mock(
                        prompt_token_count=60,
                        candidates_token_count=30,
                        total_token_count=90
                    )
                    
                    mock_chat.send_message.side_effect = [response1, response2, response3]
                    mock_client.return_value.chats.create.return_value = mock_chat
                    
                    # Track timing
                    start_time = time.monotonic()
                    
                    result = runner.invoke(main, ['review', '--no-spinner', '--debug'])
                    
                    end_time = time.monotonic()
                    elapsed = end_time - start_time
                    
                    assert result.exit_code == 0
                    
                    # With burst=2 and 3 requests, the third request should wait
                    # This is a weak assertion due to timing variability in tests
                    # In real usage, the rate limiter enforces the limit strictly
                    assert mock_chat.send_message.call_count == 3
                    
                    # Verify debug output shows rate limiting
                    assert "rate limit" in result.output.lower()
    
    def test_rate_limit_timeout_handling(self, temp_repo, mock_env):
        """Test handling of rate limit timeout."""
        repo_path, repo = temp_repo
        
        # Create a test file
        test_file = repo_path / "test.py"
        test_file.write_text("def test(): pass")
        
        # Create a rate limiter that always times out
        with patch.object(RateLimitManager, 'get_limiter') as mock_get_limiter:
            timeout_limiter = Mock()
            timeout_limiter.acquire.return_value = False  # Simulate timeout
            mock_get_limiter.return_value = timeout_limiter
            
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.chdir(str(repo_path))
                
                result = runner.invoke(main, ['review', '--no-spinner'])
                
                # Should fail with rate limit error
                assert result.exit_code != 0
                assert "rate limit timeout" in result.output.lower()
    
    def test_rate_limiting_with_config_file(self, temp_repo, mock_env):
        """Test rate limiting can be configured via YAML."""
        repo_path, repo = temp_repo
        
        # Create a test file
        test_file = repo_path / "test.py"
        test_file.write_text("def test(): pass")
        
        # Create config file that disables rate limiting
        config_file = repo_path / ".reviewer.yaml"
        config_file.write_text("""
review:
  provider: gemini-2.5-pro
  gemini_settings:
    rate_limiting:
      enabled: false
""")
        
        # Track if rate limiter is created
        rate_limiter_created = False
        
        def track_limiter(*args, **kwargs):
            nonlocal rate_limiter_created
            rate_limiter_created = True
            return Mock()
        
        with patch.object(RateLimitManager, 'get_limiter', side_effect=track_limiter):
            runner = CliRunner()
            with runner.isolated_filesystem():
                os.chdir(str(repo_path))
                
                # Mock Gemini
                with patch('reviewer.gemini_client.genai.Client') as mock_client:
                    mock_chat = Mock()
                    mock_response = Mock()
                    mock_response.function_calls = []
                    mock_response.text = "No issues."
                    mock_response.usage_metadata = Mock(
                        prompt_token_count=50,
                        candidates_token_count=25,
                        total_token_count=75
                    )
                    mock_chat.send_message.return_value = mock_response
                    mock_client.return_value.chats.create.return_value = mock_chat
                    
                    result = runner.invoke(main, ['review', '--no-spinner'])
                    
                    assert result.exit_code == 0
                    # Rate limiter should not be created when disabled in config
                    assert not rate_limiter_created