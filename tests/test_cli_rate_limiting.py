"""Tests for CLI rate limiting configuration."""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import yaml

from click.testing import CliRunner
import pytest

from reviewer.cli import review_command


class TestCLIRateLimiting:
    """Test rate limiting configuration through CLI."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        # Mock environment variable
        os.environ['GEMINI_API_KEY'] = 'test-key'
    
    def teardown_method(self):
        """Clean up test environment."""
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
    
    @patch('reviewer.cli.CodebaseIndexer')
    @patch('reviewer.cli.NavigationTools')
    @patch('reviewer.cli.GitOperations')
    @patch('reviewer.cli.GeminiClient')
    def test_rate_limiting_enabled_by_default(self, mock_gemini_client, mock_git_ops, mock_nav_tools, mock_indexer):
        """Test that rate limiting is enabled by default without flags or config."""
        # Setup mocks
        mock_git_ops.return_value.has_uncommitted_changes.return_value = True
        mock_git_ops.return_value.get_repo_info.return_value = {"repo_path": "/tmp/test"}
        mock_git_ops.return_value.get_uncommitted_files.return_value = {"modified": ["test.py"]}
        mock_git_ops.return_value.get_all_diffs.return_value = {"test.py": "diff content"}
        
        # Mock indexer
        mock_index = Mock()
        mock_index.stats = {'total_files': 10, 'unique_symbols': 20}
        mock_index.build_time = 1.0
        mock_indexer.return_value.build_index.return_value = mock_index
        mock_indexer.return_value.get_index_summary.return_value = "Index summary"
        
        # Mock GeminiClient instance
        mock_client_instance = MagicMock()
        mock_client_instance.format_initial_context.return_value = "context"
        mock_client_instance.review_code.return_value = {
            'review_content': 'No issues found',
            'navigation_history': [],
            'iterations': 1,
            'navigation_summary': {},
            'token_details': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
        }
        mock_gemini_client.return_value = mock_client_instance
        
        # Run command
        with self.runner.isolated_filesystem():
            Path("test.py").touch()
            result = self.runner.invoke(review_command, [])
        
        # Verify GeminiClient was called with rate limiting enabled
        mock_gemini_client.assert_called_once()
        call_kwargs = mock_gemini_client.call_args[1]
        assert call_kwargs['enable_rate_limiting'] is True
    
    @patch('reviewer.cli.CodebaseIndexer')
    @patch('reviewer.cli.NavigationTools')
    @patch('reviewer.cli.GitOperations')
    @patch('reviewer.cli.GeminiClient')
    def test_no_rate_limit_flag_disables(self, mock_gemini_client, mock_git_ops, mock_nav_tools, mock_indexer):
        """Test that --no-rate-limit flag disables rate limiting."""
        # Setup mocks
        mock_git_ops.return_value.has_uncommitted_changes.return_value = True
        mock_git_ops.return_value.get_repo_info.return_value = {"repo_path": "/tmp/test"}
        mock_git_ops.return_value.get_uncommitted_files.return_value = {"modified": ["test.py"]}
        mock_git_ops.return_value.get_all_diffs.return_value = {"test.py": "diff content"}
        
        # Mock indexer
        mock_index = Mock()
        mock_index.stats = {'total_files': 10, 'unique_symbols': 20}
        mock_index.build_time = 1.0
        mock_indexer.return_value.build_index.return_value = mock_index
        mock_indexer.return_value.get_index_summary.return_value = "Index summary"
        
        # Mock GeminiClient instance
        mock_client_instance = MagicMock()
        mock_client_instance.format_initial_context.return_value = "context"
        mock_client_instance.review_code.return_value = {
            'review_content': 'No issues found',
            'navigation_history': [],
            'iterations': 1,
            'navigation_summary': {},
            'token_details': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
        }
        mock_gemini_client.return_value = mock_client_instance
        
        # Run command with --no-rate-limit
        with self.runner.isolated_filesystem():
            Path("test.py").touch()
            result = self.runner.invoke(review_command, ['--no-rate-limit'])
        
        # Verify GeminiClient was called with rate limiting disabled
        mock_gemini_client.assert_called_once()
        call_kwargs = mock_gemini_client.call_args[1]
        assert call_kwargs['enable_rate_limiting'] is False
    
    @patch('reviewer.cli.CodebaseIndexer')
    @patch('reviewer.cli.NavigationTools')
    @patch('reviewer.cli.GitOperations')
    @patch('reviewer.cli.GeminiClient')
    def test_config_file_enables_rate_limiting(self, mock_gemini_client, mock_git_ops, mock_nav_tools, mock_indexer):
        """Test that config file can enable rate limiting."""
        # Setup mocks
        mock_git_ops.return_value.has_uncommitted_changes.return_value = True
        mock_git_ops.return_value.get_repo_info.return_value = {"repo_path": "/tmp/test"}
        mock_git_ops.return_value.get_uncommitted_files.return_value = {"modified": ["test.py"]}
        mock_git_ops.return_value.get_all_diffs.return_value = {"test.py": "diff content"}
        
        # Mock indexer
        mock_index = Mock()
        mock_index.stats = {'total_files': 10, 'unique_symbols': 20}
        mock_index.build_time = 1.0
        mock_indexer.return_value.build_index.return_value = mock_index
        mock_indexer.return_value.get_index_summary.return_value = "Index summary"
        
        # Mock GeminiClient instance
        mock_client_instance = MagicMock()
        mock_client_instance.format_initial_context.return_value = "context"
        mock_client_instance.review_code.return_value = {
            'review_content': 'No issues found',
            'navigation_history': [],
            'iterations': 1,
            'navigation_summary': {},
            'token_details': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
        }
        mock_gemini_client.return_value = mock_client_instance
        
        # Create config file with rate limiting enabled
        config = {
            'review': {
                'provider': 'gemini-2.5-pro',
                'gemini_settings': {
                    'rate_limiting': {
                        'enabled': True
                    }
                }
            }
        }
        
        # Run command with config
        with self.runner.isolated_filesystem():
            Path("test.py").touch()
            with open('.reviewer.yaml', 'w') as f:
                yaml.dump(config, f)
            
            result = self.runner.invoke(review_command, [])
        
        # Verify GeminiClient was called with rate limiting enabled
        mock_gemini_client.assert_called_once()
        call_kwargs = mock_gemini_client.call_args[1]
        assert call_kwargs['enable_rate_limiting'] is True
    
    @patch('reviewer.cli.CodebaseIndexer')
    @patch('reviewer.cli.NavigationTools')
    @patch('reviewer.cli.GitOperations')
    @patch('reviewer.cli.GeminiClient')
    def test_config_file_disables_rate_limiting(self, mock_gemini_client, mock_git_ops, mock_nav_tools, mock_indexer):
        """Test that config file can disable rate limiting."""
        # Setup mocks
        mock_git_ops.return_value.has_uncommitted_changes.return_value = True
        mock_git_ops.return_value.get_repo_info.return_value = {"repo_path": "/tmp/test"}
        mock_git_ops.return_value.get_uncommitted_files.return_value = {"modified": ["test.py"]}
        mock_git_ops.return_value.get_all_diffs.return_value = {"test.py": "diff content"}
        
        # Mock indexer
        mock_index = Mock()
        mock_index.stats = {'total_files': 10, 'unique_symbols': 20}
        mock_index.build_time = 1.0
        mock_indexer.return_value.build_index.return_value = mock_index
        mock_indexer.return_value.get_index_summary.return_value = "Index summary"
        
        # Mock GeminiClient instance
        mock_client_instance = MagicMock()
        mock_client_instance.format_initial_context.return_value = "context"
        mock_client_instance.review_code.return_value = {
            'review_content': 'No issues found',
            'navigation_history': [],
            'iterations': 1,
            'navigation_summary': {},
            'token_details': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
        }
        mock_gemini_client.return_value = mock_client_instance
        
        # Create config file with rate limiting disabled
        config = {
            'review': {
                'provider': 'gemini-2.5-pro',
                'gemini_settings': {
                    'rate_limiting': {
                        'enabled': False
                    }
                }
            }
        }
        
        # Run command with config
        with self.runner.isolated_filesystem():
            Path("test.py").touch()
            with open('.reviewer.yaml', 'w') as f:
                yaml.dump(config, f)
            
            result = self.runner.invoke(review_command, [])
        
        # Verify GeminiClient was called with rate limiting disabled
        mock_gemini_client.assert_called_once()
        call_kwargs = mock_gemini_client.call_args[1]
        assert call_kwargs['enable_rate_limiting'] is False
    
    @patch('reviewer.cli.CodebaseIndexer')
    @patch('reviewer.cli.NavigationTools')
    @patch('reviewer.cli.GitOperations')
    @patch('reviewer.cli.GeminiClient')
    def test_cli_flag_overrides_config(self, mock_gemini_client, mock_git_ops, mock_nav_tools, mock_indexer):
        """Test that CLI flag overrides config file setting."""
        # Setup mocks
        mock_git_ops.return_value.has_uncommitted_changes.return_value = True
        mock_git_ops.return_value.get_repo_info.return_value = {"repo_path": "/tmp/test"}
        mock_git_ops.return_value.get_uncommitted_files.return_value = {"modified": ["test.py"]}
        mock_git_ops.return_value.get_all_diffs.return_value = {"test.py": "diff content"}
        
        # Mock indexer
        mock_index = Mock()
        mock_index.stats = {'total_files': 10, 'unique_symbols': 20}
        mock_index.build_time = 1.0
        mock_indexer.return_value.build_index.return_value = mock_index
        mock_indexer.return_value.get_index_summary.return_value = "Index summary"
        
        # Mock GeminiClient instance
        mock_client_instance = MagicMock()
        mock_client_instance.format_initial_context.return_value = "context"
        mock_client_instance.review_code.return_value = {
            'review_content': 'No issues found',
            'navigation_history': [],
            'iterations': 1,
            'navigation_summary': {},
            'token_details': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
        }
        mock_gemini_client.return_value = mock_client_instance
        
        # Create config file with rate limiting enabled
        config = {
            'review': {
                'provider': 'gemini-2.5-pro',
                'gemini_settings': {
                    'rate_limiting': {
                        'enabled': True  # Config says enabled
                    }
                }
            }
        }
        
        # Run command with --no-rate-limit flag (should override config)
        with self.runner.isolated_filesystem():
            Path("test.py").touch()
            with open('.reviewer.yaml', 'w') as f:
                yaml.dump(config, f)
            
            result = self.runner.invoke(review_command, ['--no-rate-limit'])
        
        # Verify GeminiClient was called with rate limiting disabled (flag wins)
        mock_gemini_client.assert_called_once()
        call_kwargs = mock_gemini_client.call_args[1]
        assert call_kwargs['enable_rate_limiting'] is False
    
    @patch('reviewer.cli.CodebaseIndexer')
    @patch('reviewer.cli.NavigationTools')
    @patch('reviewer.cli.GitOperations')
    @patch('reviewer.cli.GeminiClient')
    def test_config_string_false_values(self, mock_gemini_client, mock_git_ops, mock_nav_tools, mock_indexer):
        """Test that string 'false' values in config are handled correctly."""
        # Setup mocks
        mock_git_ops.return_value.has_uncommitted_changes.return_value = True
        mock_git_ops.return_value.get_repo_info.return_value = {"repo_path": "/tmp/test"}
        mock_git_ops.return_value.get_uncommitted_files.return_value = {"modified": ["test.py"]}
        mock_git_ops.return_value.get_all_diffs.return_value = {"test.py": "diff content"}
        
        # Mock indexer
        mock_index = Mock()
        mock_index.stats = {'total_files': 10, 'unique_symbols': 20}
        mock_index.build_time = 1.0
        mock_indexer.return_value.build_index.return_value = mock_index
        
        # Mock navigation tools
        mock_nav_tools.return_value.to_dict.return_value = {
            'read_file': 'read_file', 
            'search_symbol': 'search_symbol',
            'find_usages': 'find_usages',
            'get_imports': 'get_imports',
            'get_file_tree': 'get_file_tree',
            'search_text': 'search_text'
        }
        
        # Mock client review
        mock_client_instance = Mock()
        mock_client_instance.review_code.return_value = {
            'high_priority_issues': [],
            'medium_priority_issues': [],
            'deferred_issues': [],
            'review_content': 'No issues found',
            'navigation_history': [],
            'iterations': 1,
            'navigation_summary': {},
            'token_details': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}
        }
        mock_gemini_client.return_value = mock_client_instance
        
        # Test various string representations of false
        false_values = ["false", "False", "FALSE", "no", "No", "0", "off", "OFF"]
        
        for false_val in false_values:
            mock_gemini_client.reset_mock()
            
            config = {
                'review': {
                    'provider': 'gemini-2.5-pro',
                    'gemini_settings': {
                        'rate_limiting': {
                            'enabled': false_val  # String value
                        }
                    }
                }
            }
            
            with self.runner.isolated_filesystem():
                Path("test.py").touch()
                with open('.reviewer.yaml', 'w') as f:
                    yaml.dump(config, f)
                
                result = self.runner.invoke(review_command)
            
            # Verify client was created with rate limiting disabled
            mock_gemini_client.assert_called_once()
            call_kwargs = mock_gemini_client.call_args[1]
            assert call_kwargs['enable_rate_limiting'] is False, f"Rate limiting should be disabled for value: {false_val}"