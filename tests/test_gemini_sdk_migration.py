"""Integration tests for the new google-genai SDK migration."""

import os
import sys
from pathlib import Path
import pytest
from reviewer.gemini_client import GeminiClient
from reviewer.navigation_tools import NavigationTools
from reviewer.codebase_indexer import CodebaseIndexer


class TestGeminiSDKMigration:
    """Test the migrated Gemini client with new SDK."""
    
    @pytest.mark.integration
    def test_gemini_client_initialization(self):
        """Test that GeminiClient initializes correctly with new SDK."""
        # This test uses real API key from environment
        client = GeminiClient(debug=False)
        assert client.api_key is not None
        assert client.model_name == "gemini-2.5-pro"
        assert client.client is not None
    
    @pytest.mark.integration
    def test_navigation_tools_integration(self):
        """Test that navigation tools work with new SDK."""
        client = GeminiClient(debug=False)
        
        # Set up navigation tools
        repo_path = Path.cwd()
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        nav_tools = NavigationTools(repo_path, index, debug=False)
        
        client.setup_navigation_tools(nav_tools)
        assert client.navigation_tools is not None
        assert client.tool is not None
        assert len(client.tool.function_declarations) == 6  # We have 6 navigation functions
    
    @pytest.mark.integration
    def test_simple_review_with_new_sdk(self):
        """Test a simple code review with the new SDK."""
        client = GeminiClient(debug=False)
        
        # Set up navigation tools
        repo_path = Path.cwd()
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        nav_tools = NavigationTools(repo_path, index, debug=False)
        client.setup_navigation_tools(nav_tools)
        
        # Create a simple context
        context = """
        You are testing the new SDK integration.
        
        ## Changed Files
        - tests/test_gemini_sdk_migration.py (this file)
        
        ## Available Tools
        - read_file(filepath): Read any file
        - get_file_tree(): Get project structure
        
        Please read this test file and confirm the integration is working.
        Just provide a brief confirmation, no need for detailed review.
        """
        
        # Run review with limited iterations
        result = client.review_code(context, max_iterations=2)
        
        # Verify response structure
        assert 'review_content' in result
        assert 'navigation_history' in result
        assert 'iterations' in result
        assert 'token_details' in result
        
        # Verify token accumulation
        assert result['token_details']['input_tokens'] > 0
        assert result['token_details']['output_tokens'] > 0
        assert result['token_details']['total_tokens'] > 0
        
        # Verify some navigation occurred
        assert result['iterations'] >= 1
        assert len(result['navigation_history']) >= 1
    
    @pytest.mark.integration
    def test_multiple_function_calls_handling(self):
        """Test that multiple function calls in one response are handled correctly."""
        client = GeminiClient(debug=False)
        
        # Set up navigation tools
        repo_path = Path.cwd()
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        nav_tools = NavigationTools(repo_path, index, debug=False)
        client.setup_navigation_tools(nav_tools)
        
        # Create context that might trigger multiple function calls
        context = """
        You need to check multiple files.
        
        ## Task
        Please read both the gemini_client.py and cli.py files to verify they work together.
        Use multiple read_file calls if needed.
        
        ## Available Tools
        - read_file(filepath): Read any file
        
        Just confirm you can read both files successfully.
        """
        
        # Run review
        result = client.review_code(context, max_iterations=3)
        
        # Check that we got results
        assert result['review_content'] != ""
        assert result['iterations'] >= 1
        
        # Verify token counts are accumulated properly
        # If there were multiple iterations, tokens should reflect that
        if result['iterations'] > 1:
            # Each iteration should add tokens
            assert result['token_details']['total_tokens'] > result['token_details']['input_tokens']
    
    @pytest.mark.integration
    def test_token_accumulation_across_iterations(self):
        """Test that tokens are properly accumulated across multiple API calls."""
        client = GeminiClient(debug=False)
        
        # Set up navigation tools
        repo_path = Path.cwd()
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        nav_tools = NavigationTools(repo_path, index, debug=False)
        client.setup_navigation_tools(nav_tools)
        
        # Create context that will require multiple iterations
        context = """
        Perform a multi-step investigation.
        
        ## Steps
        1. First, use get_file_tree() to see the project structure
        2. Then read the README.md file
        3. Finally, provide a one-sentence summary
        
        ## Available Tools
        - get_file_tree(): Get project structure
        - read_file(filepath): Read any file
        """
        
        # Run review
        result = client.review_code(context, max_iterations=5)
        
        # Verify multiple iterations occurred
        assert result['iterations'] >= 2
        
        # Verify tokens were accumulated
        # Total tokens should be approximately sum of all input + output tokens
        # Allow for small discrepancies in how the API reports tokens
        calculated_total = result['token_details']['input_tokens'] + result['token_details']['output_tokens']
        actual_total = result['token_details']['total_tokens']
        
        # Allow up to 5% difference due to API reporting variations
        tolerance = 0.05
        assert abs(actual_total - calculated_total) / calculated_total <= tolerance
        
        # With multiple iterations, we expect substantial token usage
        assert result['token_details']['total_tokens'] > 1000