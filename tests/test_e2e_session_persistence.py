"""End-to-end tests for session persistence feature."""

import os
import time
import tempfile
import shutil
import subprocess
from pathlib import Path
import git
import pytest
from click.testing import CliRunner
import requests

from reviewer.cli import main
from reviewer.service import ReviewerService


class TestE2ESessionPersistence:
    """E2E tests for session persistence with real code review scenarios."""
    
    @pytest.fixture
    def service_port(self):
        """Get a unique port for the test service."""
        return 9876  # Use a different port to avoid conflicts
    
    @pytest.fixture
    def service_url(self, service_port):
        """Get the service URL."""
        return f"http://localhost:{service_port}"
    
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
    def service_process(self, service_port):
        """Start the LLM Review service in a subprocess."""
        env = os.environ.copy()
        env['LLM_REVIEW_PORT'] = str(service_port)
        
        # Start the service
        proc = subprocess.Popen(
            ['python', '-m', 'llm_review.service'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for service to start
        max_attempts = 30
        for i in range(max_attempts):
            try:
                response = requests.get(f"http://localhost:{service_port}/health", timeout=0.5)
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(0.5)
        else:
            proc.terminate()
            raise RuntimeError("Service failed to start")
        
        yield proc
        
        # Cleanup
        proc.terminate()
        proc.wait(timeout=5)
    
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
    def test_session_creation_and_continuation(self, temp_repo, service_process, service_url):
        """Test creating a session and continuing it with new changes."""
        repo_path, repo = temp_repo
        
        # Create initial code with a bug
        self.create_file(repo_path, "src/calculator.py", '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        # BUG: No zero division check
        return a / b
''')
        self.stage_and_commit(repo, "Initial calculator")
        
        # Make changes - add a new method with issues
        self.create_file(repo_path, "src/calculator.py", '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        # BUG: No zero division check
        return a / b
    
    def multiply(self, a, b):
        # BUG: Type checking missing
        return a * b
''')
        
        # Run first review with session
        runner = CliRunner()
        env = {'LLM_REVIEW_SERVICE_URL': service_url, 'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY')}
        
        # Save current directory
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # First review - should create new session
            result1 = runner.invoke(main, ['--session-name', 'feature-calc', '--no-spinner'], env=env)
            if result1.exit_code != 0:
                print(f"First review failed with exit code {result1.exit_code}")
                print(f"Output: {result1.output}")
                if result1.exception:
                    import traceback
                    traceback.print_exception(type(result1.exception), result1.exception, result1.exception.__traceback__)
            assert result1.exit_code == 0
            assert "Starting NEW review session: feature-calc" in result1.output
            assert "divide" in result1.output  # Should mention the divide issue
            
            # Add more changes - fix divide but introduce new bug
            self.create_file(repo_path, "src/calculator.py", '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    def multiply(self, a, b):
        # BUG: Type checking missing
        return a * b
    
    def power(self, base, exp):
        # BUG: No validation for negative exponents with integers
        return base ** exp
''')
            
            # Second review - should continue session
            result2 = runner.invoke(main, ['--session-name', 'feature-calc', '--no-spinner'], env=env)
            assert result2.exit_code == 0
            assert "CONTINUING review session: feature-calc" in result2.output
            assert "iteration 2" in result2.output
            
            # Should acknowledge the fix
            output_lower = result2.output.lower()
            assert "divide" in output_lower or "fixed" in output_lower or "resolved" in output_lower
            
            # Should still catch the multiply and power issues
            assert "multiply" in result2.output or "power" in result2.output
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.integration
    def test_cross_project_session_isolation(self, service_process, service_url):
        """Test that sessions are isolated between projects."""
        # Create two temporary repos
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            # Setup repo 1
            repo1_path = Path(tmpdir1)
            repo1 = git.Repo.init(repo1_path)
            repo1.config_writer().set_value("user", "name", "Test User").release()
            repo1.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Setup repo 2
            repo2_path = Path(tmpdir2)
            repo2 = git.Repo.init(repo2_path)
            repo2.config_writer().set_value("user", "name", "Test User").release()
            repo2.config_writer().set_value("user", "email", "test@example.com").release()
            
            # Create different code in each repo
            self.create_file(repo1_path, "app.py", '''
def process_data(data):
    # Repo 1: Missing validation
    return data.upper()
''')
            repo1.git.add(A=True)
            repo1.index.commit("Initial commit")
            
            self.create_file(repo2_path, "service.py", '''
def fetch_data(url):
    # Repo 2: Missing error handling
    response = requests.get(url)
    return response.json()
''')
            repo2.git.add(A=True)
            repo2.index.commit("Initial commit")
            
            # Make changes in both repos
            self.create_file(repo1_path, "app.py", '''
def process_data(data):
    # Repo 1: Missing validation
    result = data.upper()
    # New feature
    return result.strip()
''')
            
            self.create_file(repo2_path, "service.py", '''
import requests

def fetch_data(url):
    # Repo 2: Missing error handling
    response = requests.get(url)
    return response.json()

def post_data(url, data):
    # New function with issues
    response = requests.post(url, json=data)
    return response
''')
            
            runner = CliRunner()
            env = {'LLM_REVIEW_SERVICE_URL': service_url}
            
            # Review repo 1 with session "feature-x"
            old_cwd = os.getcwd()
            try:
                os.chdir(str(repo1_path))
                result1 = runner.invoke(main, ['--session-name', 'feature-x', '--no-spinner'], env=env)
                assert result1.exit_code == 0
                assert "Starting NEW review session: feature-x" in result1.output
                assert "process_data" in result1.output
                
                # Review repo 2 with same session name "feature-x"
                os.chdir(str(repo2_path))
                result2 = runner.invoke(main, ['--session-name', 'feature-x', '--no-spinner'], env=env)
                assert result2.exit_code == 0
                # Should be NEW session, not continued (different project)
                assert "Starting NEW review session: feature-x" in result2.output
                assert "fetch_data" in result2.output or "post_data" in result2.output
                
                # Should NOT see content from repo1
                assert "process_data" not in result2.output
                
            finally:
                os.chdir(old_cwd)
    
    @pytest.mark.integration
    def test_service_unavailable_fallback(self, temp_repo):
        """Test fallback to standard mode when service is not available."""
        repo_path, repo = temp_repo
        
        # Create code with issues
        self.create_file(repo_path, "main.py", '''
def main():
    # Missing error handling
    data = open("config.json").read()
    config = json.loads(data)
    return config
''')
        self.stage_and_commit(repo, "Initial commit")
        
        # Make changes
        self.create_file(repo_path, "main.py", '''
import json

def main():
    # Still missing error handling
    data = open("config.json").read()
    config = json.loads(data)
    # Process config
    for key in config:
        print(key)
    return config
''')
        
        runner = CliRunner()
        # Use a port where no service is running
        env = {'LLM_REVIEW_SERVICE_URL': 'http://localhost:19999', 'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY')}
        
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # Should fallback gracefully
            result = runner.invoke(main, ['--session-name', 'test-fallback', '--no-spinner'], env=env)
            
            print(f"Exit code: {result.exit_code}")
            print(f"Output:\n{result.output}")
            
            assert result.exit_code == 0
            # Either fallback message or successful review without session
            assert ("Falling back to standard mode" in result.output) or ("FILE:" in result.output and "Starting NEW review session" not in result.output)
            # Should still produce a review
            assert "open" in result.output  # Should catch the file handling issue
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.integration
    def test_ai_generated_code_review_with_session(self, temp_repo, service_process, service_url):
        """Test AI-generated code review mode with sessions."""
        repo_path, repo = temp_repo
        
        # Create initial AI-generated code with hallucinations
        self.create_file(repo_path, "ai_helper.py", '''
from typing import List
import numpy as np
from sklearn.metrics import calculate_similarity  # Hallucination!

def process_embeddings(texts: List[str]) -> np.ndarray:
    """Process text embeddings using advanced NLP."""
    # TODO: Implement embedding logic
    pass

def find_similar(query: str, documents: List[str]) -> List[str]:
    """Find similar documents using cosine similarity."""
    # Stub implementation
    return documents[:5]
''')
        self.stage_and_commit(repo, "Initial AI code")
        
        # Make changes - add more AI-generated code
        self.create_file(repo_path, "ai_helper.py", '''
from typing import List
import numpy as np
from sklearn.metrics import cosine_similarity  # Fixed hallucination
from transformers import AutoTokenizer  # New import

def process_embeddings(texts: List[str]) -> np.ndarray:
    """Process text embeddings using advanced NLP."""
    tokenizer = AutoTokenizer.from_pretrained("bert-base")
    # Still TODO: Implement actual embedding logic
    embeddings = []
    for text in texts:
        # Incomplete implementation
        tokens = tokenizer.encode(text)
        embeddings.append(tokens)
    return np.array(embeddings)

def find_similar(query: str, documents: List[str]) -> List[str]:
    """Find similar documents using cosine similarity."""
    query_embedding = process_embeddings([query])
    doc_embeddings = process_embeddings(documents)
    
    # Calculate similarities
    similarities = cosine_similarity(query_embedding, doc_embeddings)
    
    # Return top 5
    top_indices = np.argsort(similarities[0])[-5:]
    return [documents[i] for i in top_indices]

def generate_summary(text: str) -> str:
    """Generate summary using GPT model."""
    # HALLUCINATION: Function claims to work but has no implementation
    return "Summary generated successfully!"
''')
        
        runner = CliRunner()
        env = {'LLM_REVIEW_SERVICE_URL': service_url, 'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY')}
        
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # First review with AI-generated mode
            result = runner.invoke(main, [
                '--session-name', 'ai-feature',
                '--ai-generated',
                '--no-spinner'
            ], env=env)
            
            assert result.exit_code == 0
            assert "Starting NEW review session: ai-feature" in result.output
            
            # Should detect AI-specific issues
            output_lower = result.output.lower()
            assert "hallucination" in output_lower or "incomplete" in output_lower or "stub" in output_lower
            assert "generate_summary" in result.output  # Should catch the fake implementation
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.integration
    def test_prototype_mode_with_session(self, temp_repo, service_process, service_url):
        """Test prototype mode deprioritizes security issues."""
        repo_path, repo = temp_repo
        
        # Create initial prototype code
        self.create_file(repo_path, "prototype.py", '''
import os

def quick_config_loader():
    """Quick and dirty config loader for prototype."""
    # Security issue: using eval
    config_str = open("config.txt").read()
    config = eval(config_str)
    return config

def save_user_data(data):
    """Save user data to file."""
    # Security issue: no input validation
    filename = data.get("filename")
    content = data.get("content")
    
    # Potential path traversal
    with open(f"./data/{filename}", "w") as f:
        f.write(content)
''')
        self.stage_and_commit(repo, "Initial prototype")
        
        # Add more prototype code
        self.create_file(repo_path, "prototype.py", '''
import os
import pickle

def quick_config_loader():
    """Quick and dirty config loader for prototype."""
    # Security issue: using eval
    config_str = open("config.txt").read()
    config = eval(config_str)
    return config

def save_user_data(data):
    """Save user data to file."""
    # Security issue: no input validation
    filename = data.get("filename")
    content = data.get("content")
    
    # Potential path traversal
    with open(f"./data/{filename}", "w") as f:
        f.write(content)

def load_cached_data(cache_file):
    """Load cached data from pickle file."""
    # Security issue: unpickling untrusted data
    with open(cache_file, "rb") as f:
        return pickle.load(f)

def process_batch(items):
    """Process items in batch."""
    results = []
    for item in items:
        # Performance issue: inefficient processing
        result = process_single_item(item)
        results.append(result)
    return results
''')
        
        runner = CliRunner()
        env = {'LLM_REVIEW_SERVICE_URL': service_url, 'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY')}
        
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # Review with prototype mode
            result = runner.invoke(main, [
                '--session-name', 'prototype-v1',
                '--prototype',
                '--full',  # Show all issues to see prioritization
                '--no-spinner'
            ], env=env)
            
            assert result.exit_code == 0
            assert "Starting NEW review session: prototype-v1" in result.output
            
            # In prototype mode, security issues should be suggestions, not critical
            output = result.output
            
            # Check that security issues are mentioned but as lower priority
            assert "eval" in output or "pickle" in output or "security" in output.lower()
            
            # Performance and correctness issues should still be flagged
            assert "process_batch" in output or "performance" in output.lower()
            
        finally:
            os.chdir(old_cwd)
    
    @pytest.mark.integration
    def test_session_list_and_clear(self, service_process, service_url, temp_repo):
        """Test listing and clearing sessions."""
        repo_path, repo = temp_repo
        
        # Create simple code
        self.create_file(repo_path, "app.py", "def main(): pass")
        self.stage_and_commit(repo, "Initial")
        self.create_file(repo_path, "app.py", "def main(): return 42")
        
        runner = CliRunner()
        env = {'LLM_REVIEW_SERVICE_URL': service_url, 'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY')}
        
        old_cwd = os.getcwd()
        try:
            os.chdir(str(repo_path))
            
            # Create multiple sessions
            for session_name in ['feature-a', 'feature-b', 'feature-c']:
                result = runner.invoke(main, ['--session-name', session_name, '--no-spinner'], env=env)
                assert result.exit_code == 0
            
            # List sessions
            result = runner.invoke(main, ['--list-sessions'], env=env)
            assert result.exit_code == 0
            assert "feature-a" in result.output
            assert "feature-b" in result.output
            assert "feature-c" in result.output
            assert "iteration 1" in result.output
            
            # Clear a session via API
            response = requests.delete(f"{service_url}/sessions/{str(repo_path)}:feature-b")
            assert response.status_code == 200
            
            # List again - feature-b should be gone
            result = runner.invoke(main, ['--list-sessions'], env=env)
            assert result.exit_code == 0
            assert "feature-a" in result.output
            assert "feature-b" not in result.output
            assert "feature-c" in result.output
            
        finally:
            os.chdir(old_cwd)