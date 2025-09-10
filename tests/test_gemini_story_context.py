"""Tests for story context in GeminiClient."""

import pytest

from reviewer.gemini_client import GeminiClient


class TestGeminiStoryContext:
    """Test story context formatting in GeminiClient."""

    def test_format_initial_context_with_story(self):
        """Test that story context is properly included in the prompt."""
        # Create client (API key will be mocked)
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("GEMINI_API_KEY", "test-key")
            client = GeminiClient(debug=False)
        
        # Test data
        changed_files = {'modified': ['test.py']}
        codebase_summary = "Test codebase summary"
        diffs = {'test.py': 'diff content'}
        story = "Implement user authentication with JWT tokens"
        
        # Format context with story
        context = client.format_initial_context(
            changed_files=changed_files,
            codebase_summary=codebase_summary,
            diffs=diffs,
            show_all=False,
            design_doc=None,
            story=story
        )
        
        # Verify story is included
        assert "## Story/Change Context" in context
        assert story in context
        assert "The following describes the purpose and intent of these changes:" in context

    def test_format_initial_context_without_story(self):
        """Test that context works without story."""
        # Create client
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("GEMINI_API_KEY", "test-key")
            client = GeminiClient(debug=False)
        
        # Test data
        changed_files = {'modified': ['test.py']}
        codebase_summary = "Test codebase summary"
        diffs = {'test.py': 'diff content'}
        
        # Format context without story
        context = client.format_initial_context(
            changed_files=changed_files,
            codebase_summary=codebase_summary,
            diffs=diffs,
            show_all=False,
            design_doc=None,
            story=None
        )
        
        # Verify story section is not included
        assert "## Story/Change Context" not in context

    def test_format_initial_context_story_and_design_doc(self):
        """Test that both story and design doc can be included."""
        # Create client
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("GEMINI_API_KEY", "test-key")
            client = GeminiClient(debug=False)
        
        # Test data
        changed_files = {'modified': ['test.py']}
        codebase_summary = "Test codebase summary"
        diffs = {'test.py': 'diff content'}
        story = "Add rate limiting to API endpoints"
        design_doc = "Architecture principles: Use middleware for cross-cutting concerns"
        
        # Format context with both
        context = client.format_initial_context(
            changed_files=changed_files,
            codebase_summary=codebase_summary,
            diffs=diffs,
            show_all=False,
            design_doc=design_doc,
            story=story
        )
        
        # Verify both are included
        assert "## Project Design Document" in context
        assert design_doc in context
        assert "## Story/Change Context" in context
        assert story in context
        
        # Verify order: design doc comes before story
        design_pos = context.index("## Project Design Document")
        story_pos = context.index("## Story/Change Context")
        assert design_pos < story_pos