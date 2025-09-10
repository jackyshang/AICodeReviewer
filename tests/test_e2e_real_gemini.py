"""E2E tests using real Gemini API for session persistence."""

import os
import tempfile
from pathlib import Path
import git
import pytest
from click.testing import CliRunner

from reviewer.cli import main


class TestE2ERealGemini:
    """E2E tests with real Gemini API."""
    
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
    
    def create_file(self, repo_path: Path, filename: str, content: str):
        """Helper to create a file in the repo."""
        file_path = repo_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    
    def stage_and_commit(self, repo: git.Repo, message: str):
        """Helper to stage all changes and commit."""
        repo.git.add(A=True)
        repo.index.commit(message)
    
    @pytest.mark.integration
    @pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_standard_code_review(self, temp_repo):
        """Test standard code review without sessions."""
        repo_path, repo = temp_repo
        
        # Create initial code
        self.create_file(repo_path, "calculator.py", '''
def divide(a, b):
    """Divide two numbers."""
    return a / b  # Missing zero check
''')
        self.stage_and_commit(repo, "Initial commit")
        
        # Make changes with issues
        self.create_file(repo_path, "calculator.py", '''
def divide(a, b):
    """Divide two numbers."""
    return a / b  # Missing zero check

def multiply(a, b):
    """Multiply two numbers."""
    # Missing type validation
    return a * b

def factorial(n):
    """Calculate factorial."""
    if n == 0:
        return 1
    return n * factorial(n - 1)  # Missing negative number check
''')
        
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # Run review without session
            result = runner.invoke(main, ['--no-spinner'])
            
            if result.exit_code != 0:
                print(f"Review failed with exit code {result.exit_code}")
                print(f"Output: {result.output}")
                if result.exception:
                    import traceback
                    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
            
            assert result.exit_code == 0
            
            # Check that real issues are found
            output = result.output
            assert "divide" in output or "zero" in output.lower()
            assert "factorial" in output or "negative" in output.lower()
            
            # Should have proper formatting
            assert "FILE:" in output or "ISSUE:" in output
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.integration
    @pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_ai_generated_mode_real(self, temp_repo):
        """Test AI-generated mode with real Gemini."""
        repo_path, repo = temp_repo
        
        # Create AI-generated code with issues
        self.create_file(repo_path, "ai_service.py", '''
from typing import List
import requests
from transformers import GPT4Model  # Hallucination - no such model

class AIService:
    def __init__(self):
        self.model = GPT4Model.from_pretrained("gpt-4")  # Hallucination
        
    def generate_text(self, prompt: str) -> str:
        """Generate text using GPT-4."""
        # TODO: Implement actual generation
        return "Generated text"
    
    def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of text."""
        # Stub implementation
        return {"sentiment": "positive", "score": 0.8}
    
    def summarize(self, text: str, max_length: int = 100) -> str:
        """Summarize text."""
        # Claims to work but just returns truncated text
        return text[:max_length] + "..."
''')
        self.stage_and_commit(repo, "Initial AI code")
        
        # Add more problematic code
        self.create_file(repo_path, "ai_service.py", '''
from typing import List
import requests
from transformers import AutoModel  # Fixed import

class AIService:
    def __init__(self):
        self.model = AutoModel.from_pretrained("bert-base-uncased")
        
    def generate_text(self, prompt: str) -> str:
        """Generate text using BERT."""
        # TODO: Implement actual generation
        return "Generated text"
    
    def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of text."""
        # Still a stub
        return {"sentiment": "positive", "score": 0.8}
    
    def summarize(self, text: str, max_length: int = 100) -> str:
        """Summarize text using advanced AI."""
        # Still fake implementation
        return text[:max_length] + "..."
    
    def extract_entities(self, text: str) -> List[str]:
        """Extract named entities from text."""
        # Complete hallucination - returns hard-coded values
        return ["John Doe", "New York", "OpenAI"]
''')
        
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # Run with AI-generated mode
            result = runner.invoke(main, ['--ai-generated', '--no-spinner'])
            
            assert result.exit_code == 0
            
            # Should detect AI-specific issues
            output = result.output.lower()
            assert any(word in output for word in ["stub", "todo", "incomplete", "hallucination", "fake"])
            
            # Should mention specific problematic functions
            assert "summarize" in output or "extract_entities" in output
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.integration
    @pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_prototype_mode_real(self, temp_repo):
        """Test prototype mode with real Gemini."""
        repo_path, repo = temp_repo
        
        # Create prototype code with various issues
        self.create_file(repo_path, "prototype.py", '''
import pickle
import os

# Quick prototype for demo
CONFIG = eval(open("config.txt").read())  # Security issue

def save_data(user_input):
    """Save user data."""
    # Security: Path traversal vulnerability
    filename = user_input.get("file")
    with open(f"./data/{filename}", "w") as f:
        f.write(str(user_input))

def load_cache(path):
    """Load cached data."""
    # Security: Unsafe pickle
    with open(path, "rb") as f:
        return pickle.load(f)

def process_items(items):
    """Process all items."""
    results = []
    for item in items:
        # Performance: O(n²) algorithm
        for other in items:
            if item != other:
                results.append((item, other))
    return results
''')
        self.stage_and_commit(repo, "Initial prototype")
        
        # Make changes
        self.create_file(repo_path, "prototype.py", '''
import pickle
import os
import json

# Quick prototype for demo
CONFIG = eval(open("config.txt").read())  # Security issue

def save_data(user_input):
    """Save user data."""
    # Security: Path traversal vulnerability
    filename = user_input.get("file")
    with open(f"./data/{filename}", "w") as f:
        json.dump(user_input, f)  # Slightly better

def load_cache(path):
    """Load cached data."""
    # Security: Unsafe pickle
    with open(path, "rb") as f:
        return pickle.load(f)

def process_items(items):
    """Process all items."""
    results = []
    # Still O(n²) but with early exit
    for i, item in enumerate(items):
        for j in range(i+1, len(items)):
            results.append((item, items[j]))
            if len(results) > 1000:  # Limit results
                break
    return results

def quick_api_call(endpoint, data):
    """Make API call without proper error handling."""
    import requests
    response = requests.post(endpoint, json=data)
    return response.json()  # No error handling
''')
        
        runner = CliRunner()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # Run with prototype mode
            result = runner.invoke(main, ['--prototype', '--full', '--no-spinner'])
            
            assert result.exit_code == 0
            
            output = result.output
            
            # Should still mention security issues but not as critical
            assert "eval" in output or "pickle" in output
            
            # Should focus more on functionality issues
            assert "error handling" in output.lower() or "api_call" in output
            
            # Check that issues are properly formatted
            assert "FILE:" in output and "ISSUE:" in output
            
        finally:
            os.chdir(old_cwd)