"""Tests for the story context feature in llm-review CLI."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from reviewer.cli import main


class TestStoryContext:
    """Test the story context functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch('llm_review.cli.GitOperations') as mock_git, \
             patch('llm_review.cli.CodebaseIndexer') as mock_indexer, \
             patch('llm_review.cli.NavigationTools') as mock_nav, \
             patch('llm_review.cli.GeminiClient') as mock_gemini, \
             patch('llm_review.cli.ReviewFormatter') as mock_formatter:
            
            # Setup mock git operations
            mock_git_instance = MagicMock()
            mock_git_instance.has_uncommitted_changes.return_value = True
            mock_git_instance.get_repo_info.return_value = {
                'repo_path': '/test/repo',
                'branch': 'main'
            }
            mock_git_instance.get_uncommitted_files.return_value = {
                'modified': ['test.py']
            }
            mock_git_instance.get_all_diffs.return_value = {
                'test.py': 'diff content'
            }
            mock_git.return_value = mock_git_instance
            
            # Setup mock indexer
            mock_index = MagicMock()
            mock_index.stats = {
                'total_files': 10,
                'unique_symbols': 20,
            }
            mock_index.build_time = 0.1
            mock_indexer_instance = MagicMock()
            mock_indexer_instance.build_index.return_value = mock_index
            mock_indexer_instance.get_index_summary.return_value = "Index summary"
            mock_indexer.return_value = mock_indexer_instance
            
            # Setup mock Gemini client
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.format_initial_context = MagicMock()
            mock_gemini_instance.review_code.return_value = {
                'review_content': 'No issues found',
                'navigation_summary': {'total_tokens_estimate': 1000},
                'token_details': {'total_tokens': 1000, 'input_tokens': 800, 'output_tokens': 200}
            }
            mock_gemini.return_value = mock_gemini_instance
            
            # Setup mock formatter
            mock_formatter_instance = mock_formatter.return_value
            
            yield {
                'git': mock_git_instance,
                'indexer': mock_indexer_instance,
                'gemini': mock_gemini_instance,
                'formatter': mock_formatter_instance
            }

    def test_story_as_direct_text(self, runner, mock_dependencies):
        """Test passing story as direct text."""
        story_text = "Implement JWT authentication for user login"
        
        result = runner.invoke(main, [story_text])
        
        # Check that the story was passed to format_initial_context
        mock_dependencies['gemini'].format_initial_context.assert_called_once()
        call_args = mock_dependencies['gemini'].format_initial_context.call_args
        assert call_args.kwargs['story'] == story_text

    def test_story_from_file_in_repo(self, runner, mock_dependencies):
        """Test reading story from a file within the repository."""
        # Create a temporary directory to simulate repo
        with tempfile.TemporaryDirectory() as temp_dir:
            # Update mock to return our temp directory as repo path
            mock_dependencies['git'].get_repo_info.return_value = {
                'repo_path': temp_dir,
                'branch': 'main'
            }
            
            # Create a story file
            story_file = Path(temp_dir) / "story.md"
            story_content = "This is the story content from file"
            story_file.write_text(story_content)
            
            result = runner.invoke(main, [str(story_file)])
            
            # Check that the file content was passed
            mock_dependencies['gemini'].format_initial_context.assert_called_once()
            call_args = mock_dependencies['gemini'].format_initial_context.call_args
            assert call_args.kwargs['story'] == story_content

    def test_story_file_outside_repo_exits_with_error(self, runner, mock_dependencies):
        """Test that files outside repo cause security error and exit."""
        # Create a file outside the repo
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("Should not be read")
            outside_file = f.name
        
        try:
            # Set up a different repo path than where the file is
            mock_dependencies['git'].get_repo_info.return_value = {
                'repo_path': '/fake/repo/path',
                'branch': 'main'
            }
            
            result = runner.invoke(main, [outside_file])
            
            # Should exit with error
            assert result.exit_code != 0
            # Check that the security error was reported
            mock_dependencies['formatter'].print_error.assert_called()
            error_msg = mock_dependencies['formatter'].print_error.call_args[0][0]
            assert "Security error" in error_msg
            assert "outside the repository" in error_msg
            # Should not have called format_initial_context
            mock_dependencies['gemini'].format_initial_context.assert_not_called()
        finally:
            Path(outside_file).unlink()

    def test_story_nonexistent_file_treated_as_text(self, runner, mock_dependencies):
        """Test that non-existent file paths are treated as literal text."""
        story_path = "/this/does/not/exist.md"
        
        result = runner.invoke(main, [story_path])
        
        # Check that the path string was passed as literal text
        mock_dependencies['gemini'].format_initial_context.assert_called_once()
        call_args = mock_dependencies['gemini'].format_initial_context.call_args
        assert call_args.kwargs['story'] == story_path

    def test_no_story_provided(self, runner, mock_dependencies):
        """Test that story is None when not provided."""
        result = runner.invoke(main, [])
        
        # Check that story was None
        mock_dependencies['gemini'].format_initial_context.assert_called_once()
        call_args = mock_dependencies['gemini'].format_initial_context.call_args
        assert call_args.kwargs['story'] is None

    def test_story_with_other_options(self, runner, mock_dependencies):
        """Test story context works with other CLI options."""
        story_text = "Add rate limiting to API"
        
        result = runner.invoke(main, [story_text, '--full', '--human'])
        
        # Check that all options were processed correctly
        mock_dependencies['gemini'].format_initial_context.assert_called_once()
        call_args = mock_dependencies['gemini'].format_initial_context.call_args
        assert call_args.kwargs['story'] == story_text
        assert call_args.kwargs['show_all'] is True

    def test_story_file_read_error_exits(self, runner, mock_dependencies):
        """Test that file read errors cause the program to exit."""
        # Create a temporary directory and file
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_dependencies['git'].get_repo_info.return_value = {
                'repo_path': temp_dir,
                'branch': 'main'
            }
            
            # Create a file and then make it unreadable by changing permissions
            story_file = Path(temp_dir) / "story.md"
            story_file.write_text("Story content")
            story_file.chmod(0o000)  # Remove all permissions
            
            try:
                result = runner.invoke(main, [str(story_file)])
                
                # The program should exit with non-zero status
                assert result.exit_code != 0
                # Check that the error was reported
                mock_dependencies['formatter'].print_error.assert_called()
                error_call = mock_dependencies['formatter'].print_error.call_args[0][0]
                assert "Failed to read story file" in error_call
                # Should not have called format_initial_context
                mock_dependencies['gemini'].format_initial_context.assert_not_called()
            finally:
                # Restore permissions so cleanup can work
                story_file.chmod(0o644)