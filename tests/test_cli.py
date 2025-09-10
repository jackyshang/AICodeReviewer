"""Tests for CLI functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import git
import pytest
from click.testing import CliRunner

from reviewer.cli import main


class TestCLIFlags:
    """Test CLI flag parsing and behavior."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            repo = git.Repo.init(repo_path)
            
            # Configure git user for commits
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()
            
            yield repo_path, repo
    
    @pytest.fixture
    def mock_gemini_client(self):
        """Mock GeminiClient to avoid actual API calls."""
        with patch('llm_review.cli.GeminiClient') as mock:
            client_instance = Mock()
            mock.return_value = client_instance
            
            # Mock the methods we use
            client_instance.setup_navigation_tools = Mock()
            client_instance.format_initial_context = Mock(return_value="mock context")
            client_instance.review_code = Mock(return_value={
                "review": "Mock review",
                "navigation_summary": {"files_read": 0, "total_tokens_estimate": 100},
                "token_details": {"total_tokens": 100, "input_tokens": 50, "output_tokens": 50}
            })
            
            yield client_instance
    
    def test_cli_ai_generated_flag(self, temp_repo, mock_gemini_client):
        """Test that --ai-generated flag is parsed correctly."""
        repo_path, repo = temp_repo
        
        # Create a simple file
        test_file = repo_path / "test.py"
        test_file.write_text("def hello(): pass")
        repo.git.add(A=True)
        repo.index.commit("Initial commit")
        
        # Make a change
        test_file.write_text("def hello():\n    # TODO: implement\n    pass")
        
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            result = runner.invoke(main, ['--ai-generated'])
        finally:
            os.chdir(old_cwd)
        
        # Check that format_initial_context was called with ai_generated=True
        mock_gemini_client.format_initial_context.assert_called()
        call_args = mock_gemini_client.format_initial_context.call_args
        assert call_args.kwargs.get('ai_generated') is True
        assert call_args.kwargs.get('prototype') is False
    
    def test_cli_prototype_flag(self, temp_repo, mock_gemini_client):
        """Test that --prototype flag is parsed correctly."""
        repo_path, repo = temp_repo
        
        # Create a simple file
        test_file = repo_path / "test.py"
        test_file.write_text("def hello(): pass")
        repo.git.add(A=True)
        repo.index.commit("Initial commit")
        
        # Make a change
        test_file.write_text("def hello():\n    print('hello')")
        
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            result = runner.invoke(main, ['--prototype'])
        finally:
            os.chdir(old_cwd)
        
        # Check that format_initial_context was called with prototype=True
        mock_gemini_client.format_initial_context.assert_called()
        call_args = mock_gemini_client.format_initial_context.call_args
        assert call_args.kwargs.get('ai_generated') is False
        assert call_args.kwargs.get('prototype') is True
    
    def test_cli_combined_flags(self, temp_repo, mock_gemini_client):
        """Test that both flags can be used together."""
        repo_path, repo = temp_repo
        
        # Create a simple file
        test_file = repo_path / "test.py"
        test_file.write_text("def hello(): pass")
        repo.git.add(A=True)
        repo.index.commit("Initial commit")
        
        # Make a change
        test_file.write_text("def hello():\n    # TODO: implement\n    pass")
        
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            result = runner.invoke(main, ['--ai-generated', '--prototype'])
        finally:
            os.chdir(old_cwd)
        
        # Check that both flags were passed
        mock_gemini_client.format_initial_context.assert_called()
        call_args = mock_gemini_client.format_initial_context.call_args
        assert call_args.kwargs.get('ai_generated') is True
        assert call_args.kwargs.get('prototype') is True