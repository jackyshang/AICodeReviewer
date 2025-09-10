"""End-to-end tests for llm-review with real scenarios."""

import os
import tempfile
import shutil
from pathlib import Path
import git
import pytest
from click.testing import CliRunner
from reviewer.cli import main


class TestE2EReviewScenarios:
    """End-to-end tests for llm-review with real scenarios."""
    
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
    def test_missing_tests_detection(self, temp_repo):
        """Test that missing tests are flagged as HIGH priority."""
        repo_path, repo = temp_repo
        
        # Create initial code with tests
        self.create_file(repo_path, "src/calculator.py", '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
''')
        
        self.create_file(repo_path, "tests/test_calculator.py", '''
import pytest
from src.calculator import Calculator

def test_add():
    calc = Calculator()
    assert calc.add(2, 3) == 5

def test_subtract():
    calc = Calculator()
    assert calc.subtract(5, 3) == 2
''')
        
        self.stage_and_commit(repo, "Initial calculator with tests")
        
        # Add new method WITHOUT tests
        self.create_file(repo_path, "src/calculator.py", '''
class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        """New method without tests"""
        return a * b
    
    def divide(self, a, b):
        """Another new method without tests"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
''')
        
        # Run llm-review
        result = self.run_review(repo_path)
        
        # Debug output
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
        
        # Verify the output flags missing tests as HIGH priority
        assert result.exit_code == 0
        output = result.output.lower()
        assert any(term in output for term in ["high", "test", "missing", "multiply", "divide"])
    
    @pytest.mark.integration
    def test_readme_compliance_violation(self, temp_repo):
        """Test that violations of README principles are flagged."""
        repo_path, repo = temp_repo
        
        # Create README with development principles
        self.create_file(repo_path, "README.md", '''
# Project Guidelines

## Development Principles

1. **Error Handling**: All public methods MUST have proper error handling
2. **Type Hints**: All function parameters and return values MUST have type hints
3. **Docstrings**: All public methods MUST have docstrings
4. **No Global State**: Never use global variables for state management
5. **Async First**: All I/O operations MUST be async
''')
        
        # Create initial compliant code
        self.create_file(repo_path, "src/service.py", '''
from typing import Optional

class DataService:
    async def fetch_data(self, id: int) -> Optional[dict]:
        """Fetch data by ID.
        
        Args:
            id: The data ID to fetch
            
        Returns:
            Data dictionary or None if not found
        """
        try:
            # Simulated async operation
            return {"id": id, "data": "example"}
        except Exception as e:
            # Proper error handling
            return None
''')
        
        self.stage_and_commit(repo, "Initial compliant code")
        
        # Add code that violates multiple principles
        self.create_file(repo_path, "src/service.py", '''
from typing import Optional

# VIOLATION: Global state
cache = {}

class DataService:
    async def fetch_data(self, id: int) -> Optional[dict]:
        """Fetch data by ID.
        
        Args:
            id: The data ID to fetch
            
        Returns:
            Data dictionary or None if not found
        """
        try:
            # Simulated async operation
            return {"id": id, "data": "example"}
        except Exception as e:
            # Proper error handling
            return None
    
    # VIOLATIONS: No type hints, no docstring, no error handling, not async
    def save_data(self, data):
        cache[data['id']] = data
        return data['id']
    
    # VIOLATION: Synchronous I/O operation
    def read_file(self, path: str) -> str:
        """Read file synchronously - violates async-first principle."""
        with open(path, 'r') as f:
            return f.read()
''')
        
        # Run llm-review
        result = self.run_review(repo_path)
        
        # Verify README violations are flagged as HIGH priority
        assert result.exit_code == 0
        output = result.output.lower()
        assert "high" in output
        assert any(term in output for term in ["principle", "compliance", "global", "type hint", "async"])
    
    @pytest.mark.integration
    def test_performance_antipattern_detection(self, temp_repo):
        """Test that real performance anti-patterns are flagged, but micro-optimizations are not."""
        repo_path, repo = temp_repo
        
        # Create initial code
        self.create_file(repo_path, "src/data_processor.py", '''
class DataProcessor:
    def process_items(self, items):
        results = []
        for item in items:
            results.append(item * 2)
        return results
''')
        
        self.stage_and_commit(repo, "Initial code")
        
        # Add code with REAL anti-patterns and micro-optimizations
        self.create_file(repo_path, "src/data_processor.py", '''
class DataProcessor:
    def process_items(self, items):
        results = []
        for item in items:
            results.append(item * 2)
        return results
    
    def find_duplicates_quadratic(self, items):
        """O(n²) algorithm when O(n) is easily available - ANTI-PATTERN"""
        duplicates = []
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i] == items[j] and items[i] not in duplicates:
                    duplicates.append(items[i])
        return duplicates
    
    def find_duplicates_linear(self, items):
        """Better O(n) implementation using a set"""
        seen = set()
        duplicates = []
        for item in items:
            if item in seen and item not in duplicates:
                duplicates.append(item)
            seen.add(item)
        return duplicates
    
    def load_all_users(self):
        """Loading entire dataset into memory - ANTI-PATTERN"""
        # Simulating loading millions of users
        users = self.db.query("SELECT * FROM users")  # No pagination!
        return [self.process_user(u) for u in users]
    
    def micro_optimization_example(self, data):
        """This is NOT an anti-pattern, just a style preference"""
        # Using list comprehension instead of map - both are fine
        result = [x * 2 for x in data]
        # Could also be: result = list(map(lambda x: x * 2, data))
        return result
''')
        
        # Add the corresponding test file
        self.create_file(repo_path, "tests/test_data_processor.py", '''
import pytest
from src.data_processor import DataProcessor

def test_find_duplicates():
    processor = DataProcessor()
    assert processor.find_duplicates_quadratic([1, 2, 2, 3, 3, 3]) == [2, 3]
    assert processor.find_duplicates_linear([1, 2, 2, 3, 3, 3]) == [2, 3]

def test_micro_optimization():
    processor = DataProcessor()
    assert processor.micro_optimization_example([1, 2, 3]) == [2, 4, 6]
''')
        
        # Run llm-review
        result = self.run_review(repo_path)
        
        # Verify REAL anti-patterns are flagged
        assert result.exit_code == 0
        output = result.output
        assert "HIGH" in output or "high" in output.lower()
        assert any(term in output.lower() for term in ["o(n²)", "quadratic", "pagination", "memory"])
        
        # Verify micro-optimization is NOT flagged as HIGH priority
        # It should either not be mentioned or be marked as DEFER
        if "list comprehension" in output.lower():
            assert "defer" in output.lower()
    
    @pytest.mark.integration
    def test_security_issue_prioritization(self, temp_repo):
        """Test that critical security issues are HIGH priority, but hardening is DEFERRED."""
        repo_path, repo = temp_repo
        
        # Create initial code
        self.create_file(repo_path, "src/auth.py", '''
import hashlib

class AuthService:
    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
''')
        
        self.stage_and_commit(repo, "Initial auth code")
        
        # Add code with both critical vulnerabilities and hardening opportunities
        self.create_file(repo_path, "src/auth.py", '''
import hashlib
import os

class AuthService:
    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, username: str, password: str) -> bool:
        """CRITICAL: SQL injection vulnerability"""
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        # Execute query (simulated)
        return True
    
    def generate_token(self) -> str:
        """CRITICAL: Weak random token generation"""
        return str(hash(os.getpid()))  # Predictable!
    
    def log_attempt(self, username: str):
        """LOW RISK: Could add rate limiting (hardening)"""
        with open('auth.log', 'a') as f:
            f.write(f"Login attempt: {username}\\n")
    
    def check_password_strength(self, password: str) -> bool:
        """LOW RISK: Basic check, could be enhanced (hardening)"""
        return len(password) >= 8
''')
        
        # Add test file
        self.create_file(repo_path, "tests/test_auth.py", '''
from src.auth import AuthService

def test_password_hash():
    auth = AuthService()
    assert auth.hash_password("test") == auth.hash_password("test")

def test_verify_user():
    auth = AuthService()
    assert auth.verify_user("admin", "password")

def test_generate_token():
    auth = AuthService()
    token = auth.generate_token()
    assert isinstance(token, str)
''')
        
        # Run llm-review in critical mode
        result = self.run_review(repo_path)
        
        # Verify critical security issues are HIGH priority
        assert result.exit_code == 0
        output = result.output.lower()
        assert "high" in output
        assert any(term in output for term in ["injection", "sql", "predictable", "weak"])
        
        # Run with --full to see deferred items
        result_full = self.run_review(repo_path, ['--full'])
        
        # In full mode, hardening suggestions should be in DEFER section
        if "rate limiting" in result_full.output.lower():
            assert "defer" in result_full.output.lower()
    
    @pytest.mark.integration
    def test_bug_detection_with_existing_tests(self, temp_repo):
        """Test that bugs are detected even when tests exist (but might be wrong)."""
        repo_path, repo = temp_repo
        
        # Create initial correct code
        self.create_file(repo_path, "src/validator.py", '''
class Validator:
    def is_valid_email(self, email: str) -> bool:
        return "@" in email and "." in email.split("@")[1]
''')
        
        self.stage_and_commit(repo, "Initial validator")
        
        # Add buggy code WITH tests
        self.create_file(repo_path, "src/validator.py", '''
class Validator:
    def is_valid_email(self, email: str) -> bool:
        return "@" in email and "." in email.split("@")[1]
    
    def calculate_discount(self, price: float, discount_percent: float) -> float:
        """Calculate final price after discount.
        
        BUG: This returns the discount amount, not the final price!
        """
        # Should be: price * (1 - discount_percent / 100)
        return price * discount_percent / 100
    
    def days_between(self, date1: str, date2: str) -> int:
        """Calculate days between two dates.
        
        BUG: Doesn't handle date1 > date2 correctly - returns negative
        """
        from datetime import datetime
        d1 = datetime.strptime(date1, "%Y-%m-%d")
        d2 = datetime.strptime(date2, "%Y-%m-%d")
        return (d2 - d1).days
''')
        
        # Add tests that don't catch the bugs properly
        self.create_file(repo_path, "tests/test_validator.py", '''
from src.validator import Validator

def test_calculate_discount():
    validator = Validator()
    # This test is wrong - it expects the discount amount, not the final price
    assert validator.calculate_discount(100, 20) == 20  # Bug not caught!

def test_days_between():
    validator = Validator()
    # Only tests one direction
    assert validator.days_between("2024-01-01", "2024-01-10") == 9
''')
        
        # Run llm-review
        result = self.run_review(repo_path)
        
        # Verify bugs are detected despite tests existing
        assert result.exit_code == 0
        output = result.output.lower()
        assert "high" in output
        assert "calculate_discount" in output
        assert any(term in output for term in ["incorrect", "bug", "wrong", "final price", "discount"])
    
    @pytest.mark.integration
    def test_ai_generated_mode_detects_hallucinations(self, temp_repo):
        """Test that --ai-generated mode detects AI-specific issues."""
        repo_path, repo = temp_repo
        
        # Create initial file
        self.create_file(repo_path, "src/__init__.py", "")
        self.stage_and_commit(repo, "Initial commit")
        
        # Add AI-generated code with typical AI issues
        self.create_file(repo_path, "src/user_auth.py", '''
"""User authentication module."""
from utils.validator import EmailValidator  # This module doesn't exist!
from typing import Optional

class UserAuth:
    def __init__(self):
        self.validator = EmailValidator()
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user credentials."""
        # TODO: Implement actual authentication
        print(f"Authenticating {username}")
        return True  # Stub implementation
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        return self.validator.is_valid(email)  # Uses non-existent validator
    
    def reset_password(self, email: str) -> bool:
        """Reset user password."""
        raise NotImplementedError("Password reset not implemented yet")
''')
        
        # Add a test that doesn't actually test
        self.create_file(repo_path, "tests/test_auth.py", '''
"""Tests for authentication."""
from src.user_auth import UserAuth

def test_authentication():
    """Test user authentication."""
    auth = UserAuth()
    # This test doesn't actually verify authentication works
    assert True  # Placeholder test
    
def test_email_validation():
    """Test email validation."""
    # Test exists but can't work due to missing import
    pass
''')
        
        # Run llm-review with --ai-generated flag
        result = self.run_review(repo_path, ["--ai-generated"])
        
        # Verify AI-specific issues are detected
        assert result.exit_code == 0
        output = result.output.lower()
        
        # Should detect hallucinated import
        assert "emailvalidator" in output or "utils.validator" in output
        assert any(term in output for term in ["doesn't exist", "not found", "hallucination", "import"])
        
        # Should detect stub implementation
        assert "authenticate" in output
        assert any(term in output for term in ["stub", "todo", "not implemented", "placeholder"])
        
        # Should detect test that doesn't test
        assert "assert true" in output or "placeholder" in output
    
    @pytest.mark.integration
    def test_prototype_mode_deprioritizes_security(self, temp_repo):
        """Test that --prototype mode focuses on functionality over security."""
        repo_path, repo = temp_repo
        
        # Create initial file
        self.create_file(repo_path, "app.py", "# Initial app")
        self.stage_and_commit(repo, "Initial commit")
        
        # Add code with security issues but working functionality
        self.create_file(repo_path, "app.py", '''
"""Simple prototype API."""
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route('/user/<user_id>')
def get_user(user_id):
    """Get user by ID - SQL injection vulnerable but works for prototype."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Direct string interpolation - security issue
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = cursor.execute(query).fetchone()
    conn.close()
    return {"user": result} if result else {"error": "Not found"}, 404

@app.route('/api/data')
def get_data():
    """Get data - no auth but works for 2-5 users."""
    # Hardcoded for prototype
    API_KEY = "prototype-key-123"
    return {"data": "sensitive info", "users": 3}

if __name__ == '__main__':
    # Debug mode for development
    app.run(debug=True, host='0.0.0.0')
''')
        
        # Run llm-review with --prototype flag
        result = self.run_review(repo_path, ["--prototype"])
        
        # Verify security issues are not high priority
        assert result.exit_code == 0
        output = result.output
        
        # Should not flag SQL injection as critical in prototype mode
        if "sql injection" in output.lower():
            # If mentioned, should be deferred/low priority
            assert "deferred" in output.lower() or "low" in output.lower()
        
        # Hardcoded values should be medium priority at most
        if "hardcoded" in output.lower():
            assert "medium" in output.lower() or "deferred" in output.lower()
    
    @pytest.mark.integration  
    def test_combined_mode_ai_prototype(self, temp_repo):
        """Test --ai-generated --prototype combined mode."""
        repo_path, repo = temp_repo
        
        # Create initial file
        self.create_file(repo_path, "src/__init__.py", "")
        self.stage_and_commit(repo, "Initial commit")
        
        # Add over-engineered AI-generated code
        self.create_file(repo_path, "src/config.py", '''
"""Configuration management with unnecessary complexity."""
from abc import ABC, abstractmethod
from typing import Any, Dict

class ConfigInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Any:
        pass

class ConfigFactory:
    @staticmethod
    def create_config(config_type: str) -> ConfigInterface:
        if config_type == "simple":
            return SimpleConfigAdapter(SimpleConfigImplementation())
        raise ValueError(f"Unknown config type: {config_type}")

class SimpleConfigImplementation:
    def __init__(self):
        self.data = {"api_key": "test123"}
    
    def retrieve(self, key: str) -> Any:
        return self.data.get(key)

class SimpleConfigAdapter(ConfigInterface):
    def __init__(self, impl: SimpleConfigImplementation):
        self.impl = impl
    
    def get(self, key: str) -> Any:
        return self.impl.retrieve(key)

# Over-engineered way to get a simple config value
def get_api_key() -> str:
    """Get API key using factory pattern."""
    factory = ConfigFactory()
    config = factory.create_config("simple")
    return config.get("api_key")
''')
        
        # Run with combined flags
        result = self.run_review(repo_path, ["--ai-generated", "--prototype"])
        
        # Should detect over-engineering
        assert result.exit_code == 0
        output = result.output.lower()
        assert any(term in output for term in ["over-engineer", "complex", "simple", "unnecessary"])