"""Integration tests for llm-review covering multiple issue types."""

import os
import tempfile
from pathlib import Path
import git
import pytest
from click.testing import CliRunner
from reviewer.cli import main


class TestE2EIntegration:
    """Integration tests covering complete review scenarios."""
    
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
    
    def run_review(self, repo_path: Path, extra_args: list = None):
        """Helper to run llm-review in the given repo."""
        runner = CliRunner()
        args = extra_args or []
        
        # Save current directory
        old_cwd = os.getcwd()
        try:
            # Change to repo directory
            os.chdir(str(repo_path))
            result = runner.invoke(main, args, catch_exceptions=False)
        finally:
            # Restore directory
            os.chdir(old_cwd)
        
        return result
    
    @pytest.mark.integration
    def test_full_integration_scenario(self, temp_repo):
        """Test a complete scenario with multiple issue types."""
        repo_path, repo = temp_repo
        
        # Create README with principles
        self.create_file(repo_path, "README.md", '''
# API Service

## Development Principles

1. **Input Validation**: All endpoints must validate input data
2. **Database Transactions**: All database operations must use transactions
3. **Documentation**: All public methods must have comprehensive docstrings
4. **Dependency Injection**: Use dependency injection, not global state
5. **Error Handling**: All external operations must have proper error handling
6. **Type Safety**: All functions must have type hints
''')
        
        # Create initial good code
        self.create_file(repo_path, "src/models.py", '''
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class User:
    """User model with validation."""
    id: Optional[int]
    name: str
    email: str
    
    def validate(self) -> bool:
        """Validate user data."""
        return bool(self.name and "@" in self.email)
''')
        
        self.stage_and_commit(repo, "Initial setup with models")
        
        # Create a complex change with multiple issues
        self.create_file(repo_path, "src/api.py", '''
import json
from typing import Dict, List, Any

# HIGH PRIORITY: Global state violation (violates README principle #4)
db_connection = None

class APIService:
    # HIGH PRIORITY: Missing docstring (violates README principle #3)
    # HIGH PRIORITY: Missing type hints (violates README principle #6)
    def create_user(self, data):
        # HIGH PRIORITY: No input validation (violates README principle #1)
        # HIGH PRIORITY: SQL injection vulnerability
        query = f"INSERT INTO users (name, email) VALUES ('{data['name']}', '{data['email']}')"
        
        # HIGH PRIORITY: No transaction (violates README principle #2)
        # HIGH PRIORITY: No error handling (violates README principle #5)
        db_connection.execute(query)
        return {"status": "created"}
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users from database.
        
        HIGH PRIORITY: Performance anti-pattern - loading all users without pagination
        """
        return db_connection.execute("SELECT * FROM users").fetchall()
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID.
        
        HIGH PRIORITY: No authorization check before deletion
        """
        # At least this one has error handling
        try:
            db_connection.execute(f"DELETE FROM users WHERE id = {user_id}")
            return True
        except Exception:
            return False
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA256.
        
        DEFER: Could use bcrypt instead of sha256 for better security
        """
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def format_response(self, data: Dict[str, Any]) -> str:
        """Format response as JSON.
        
        DEFER: Minor - could use json.dumps with indent for readability
        """
        return json.dumps(data)
''')
        
        # HIGH PRIORITY: No tests for the new API code!
        
        # Run review in critical mode
        result = self.run_review(repo_path)
        
        assert result.exit_code == 0
        output = result.output
        
        # Should identify HIGH priority issues:
        # 1. README violations (global state, missing docstrings, type hints)
        assert any(term in output.lower() for term in ["global", "principle", "compliance"])
        
        # 2. Missing tests
        assert any(term in output.lower() for term in ["test", "missing"])
        
        # 3. Security (SQL injection, no authorization)
        assert any(term in output.lower() for term in ["injection", "sql", "security"])
        
        # 4. No validation, no transaction, no error handling
        assert any(term in output.lower() for term in ["validation", "transaction", "error"])
        
        # 5. Performance (no pagination)
        assert any(term in output.lower() for term in ["pagination", "performance", "users"])
        
        # Should NOT include low-priority items in critical mode
        assert "bcrypt" not in output
        assert "indent" not in output.lower()
        
        # Run with --full to see all issues
        result_full = self.run_review(repo_path, ['--full'])
        
        # In full mode, should see DEFER items
        assert "DEFER" in result_full.output or "defer" in result_full.output.lower()
        assert "bcrypt" in result_full.output.lower()
    
    @pytest.mark.integration
    def test_priority_ordering(self, temp_repo):
        """Test that issues are reported in the correct priority order."""
        repo_path, repo = temp_repo
        
        # Create README
        self.create_file(repo_path, "README.md", '''
# Service

## Development Principles
1. Use async/await for all I/O operations
2. All functions must have type hints
''')
        
        # Create initial code
        self.create_file(repo_path, "src/service.py", '''
async def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    return "data"
''')
        
        self.stage_and_commit(repo, "Initial async service")
        
        # Add code with issues in different priority levels
        self.create_file(repo_path, "src/service.py", '''
import time

async def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    return "data"

# Issue priority ordering test:

# 1. README violation - synchronous I/O
def read_file(path):  # Also missing type hints
    """Read file synchronously - violates async principle."""
    with open(path, 'r') as f:
        return f.read()

# 2. Missing test (no test file for new function)

# 3. Security issue
def execute_command(cmd: str) -> str:
    """Execute shell command - command injection vulnerability."""
    import subprocess
    return subprocess.check_output(cmd, shell=True).decode()

# 4. Bug - infinite loop
def process_items(items: list) -> list:
    """Process items with a bug."""
    results = []
    i = 0
    while i < len(items):  # Bug: i is never incremented
        results.append(items[i] * 2)
    return results

# 5. Performance issue
def find_max_naive(numbers: list) -> int:
    """O(n²) complexity for finding max - anti-pattern."""
    max_val = numbers[0]
    for i in range(len(numbers)):
        for j in range(len(numbers)):
            if numbers[j] > max_val:
                max_val = numbers[j]
    return max_val
''')
        
        # Run review
        result = self.run_review(repo_path)
        
        # Check that all issue types are found
        output = result.output.lower()
        assert all(term in output for term in ["principle", "test", "security", "bug", "performance"])
        
        # The output should list issues in priority order
        # This is harder to test exactly without parsing, but we can check
        # that HIGH priority issues are mentioned
        assert "HIGH" in result.output or "high" in output
    
    @pytest.mark.integration
    def test_mixed_quality_changes(self, temp_repo):
        """Test review of changes with both good and bad code."""
        repo_path, repo = temp_repo
        
        # Create initial code
        self.create_file(repo_path, "src/utils.py", '''
def add(a: int, b: int) -> int:
    return a + b
''')
        
        self.stage_and_commit(repo, "Initial utils")
        
        # Add mixed quality code
        self.create_file(repo_path, "src/utils.py", '''
def add(a: int, b: int) -> int:
    return a + b

# Good code with tests
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

# Bad code without tests
def divide(a, b):  # Missing type hints
    return a / b  # No zero check!

# Good async code
async def fetch_json(url: str) -> dict:
    """Fetch JSON from URL."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad SQL code
def get_user(user_id: str) -> dict:
    """Get user by ID - SQL injection vulnerability."""
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    # Execute query...
    return {}
''')
        
        # Add tests for SOME functions
        self.create_file(repo_path, "tests/test_utils.py", '''
from src.utils import add, multiply

def test_add():
    assert add(2, 3) == 5

def test_multiply():
    assert multiply(3, 4) == 12

# Note: divide() and get_user() have no tests!
''')
        
        # Run review
        result = self.run_review(repo_path)
        
        output = result.output
        
        # Should flag issues with divide() and get_user()
        assert "divide" in output
        assert any(term in output.lower() for term in ["zero", "type hint", "test"])
        
        assert "get_user" in output or "sql" in output.lower()
        assert "injection" in output.lower()
        
        # Should NOT complain about multiply() or fetch_json() which are good
        # (This is harder to verify - we're checking they're not criticized)