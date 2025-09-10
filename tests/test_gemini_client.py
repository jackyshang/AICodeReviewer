"""Tests for GeminiClient functionality."""

import pytest

from reviewer.gemini_client import GeminiClient


class TestGeminiClientPromptSelection:
    """Test the prompt selection logic in GeminiClient."""
    
    def test_ai_generated_prompt_selection(self):
        """Test that AI-generated mode selects the correct prompt."""
        client = GeminiClient(model_name="gemini-2.5-pro-preview-05-20", debug=False)
        
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=True,
            prototype=False
        )
        
        # Check for AI-specific content
        assert "AI-generated code quality assessment" in context
        assert "HALLUCINATION DETECTION" in context
        assert "TEST REALITY CHECK" in context
        assert "OVER-ENGINEERING" in context
    
    def test_prototype_prompt_selection(self):
        """Test that prototype mode selects the correct prompt."""
        client = GeminiClient(model_name="gemini-2.5-pro-preview-05-20", debug=False)
        
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=False,
            prototype=True
        )
        
        # Check for prototype-specific content
        assert "small-scale prototype (2-5 users)" in context
        assert "evolve into production code" in context
        assert "DEFERRED (Not critical for 2-5 users)" in context
    
    def test_combined_mode_prompt_selection(self):
        """Test that combined mode selects the correct prompt."""
        client = GeminiClient(model_name="gemini-2.5-pro-preview-05-20", debug=False)
        
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=True,
            prototype=True
        )
        
        # Check for combined mode content
        assert "AI-generated code for a small-scale prototype" in context
        assert "AI IMPLEMENTATION VERIFICATION" in context
        assert "CODE QUALITY FOR FUTURE PRODUCTION" in context
        assert "DEFERRED (Not critical for prototypes)" in context
    
    def test_navigation_strategy_for_ai_modes(self):
        """Test that AI modes include enhanced navigation strategy."""
        client = GeminiClient(model_name="gemini-2.5-pro-preview-05-20", debug=False)
        
        # Test AI-generated mode
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=True,
            prototype=False
        )
        
        assert "NAVIGATION STRATEGY FOR AI CODE" in context
        assert "Analyze complexity of critical functions" in context
        assert "Count abstraction layers" in context
        
        # Test combined mode
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=True,
            prototype=True
        )
        
        assert "NAVIGATION STRATEGY FOR AI CODE" in context
    
    def test_regular_mode_unchanged(self):
        """Test that regular mode (no flags) still works as before."""
        client = GeminiClient(model_name="gemini-2.5-pro-preview-05-20", debug=False)
        
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=False,
            prototype=False,
            show_all=False
        )
        
        # Should use the original critical-only prompt
        assert "expert code reviewer focused on identifying issues that must be fixed" in context
        assert "HALLUCINATION DETECTION" not in context  # AI-specific content should not appear
    
    def test_full_review_mode(self):
        """Test that full review mode still works correctly."""
        client = GeminiClient(model_name="gemini-2.5-pro-preview-05-20", debug=False)
        
        context = client._get_context(
            changed_files={"modified": ["test.py"]},
            codebase_summary="Test codebase",
            diffs={"test.py": "diff content"},
            ai_generated=False,
            prototype=False,
            show_all=True
        )
        
        # Should use the full review prompt
        assert "expert code reviewer providing comprehensive feedback" in context
        assert "HIGH PRIORITY (Must fix)" in context
        assert "MEDIUM PRIORITY (Should consider)" in context
        assert "DEFER (Note for future)" in context