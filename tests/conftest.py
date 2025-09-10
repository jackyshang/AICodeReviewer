"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from git import Repo


@pytest.fixture
def temp_git_repo() -> Generator[Path, None, None]:
    """Create a temporary git repository for testing.
    
    Yields:
        Path to temporary repository
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        repo = Repo.init(repo_path)
        
        # Create initial commit
        readme = repo_path / "README.md"
        readme.write_text("# Test Repository\n")
        repo.index.add([str(readme)])
        repo.index.commit("Initial commit")
        
        yield repo_path


@pytest.fixture
def sample_python_project(temp_git_repo: Path) -> Path:
    """Create a sample Python project structure.
    
    Args:
        temp_git_repo: Temporary git repository path
        
    Returns:
        Path to repository
    """
    # Create project structure
    src_dir = temp_git_repo / "src"
    src_dir.mkdir()
    
    # Create main module
    main_py = src_dir / "main.py"
    main_py.write_text('''"""Main module for sample project."""

def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator class."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        """Subtract b from a."""
        return a - b
''')
    
    # Create utils module
    utils_py = src_dir / "utils.py"
    utils_py.write_text('''"""Utility functions."""

import re
from typing import List

def validate_email(email: str) -> bool:
    """Validate an email address."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def parse_csv_line(line: str) -> List[str]:
    """Parse a CSV line."""
    return line.strip().split(',')
''')
    
    # Create test file
    tests_dir = temp_git_repo / "tests"
    tests_dir.mkdir()
    
    test_main = tests_dir / "test_main.py"
    test_main.write_text('''"""Tests for main module."""

from src.main import greet, Calculator

def test_greet():
    """Test greet function."""
    assert greet("World") == "Hello, World!"
    assert greet("Python") == "Hello, Python!"

def test_calculator_add():
    """Test calculator addition."""
    calc = Calculator()
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 1) == 0
''')
    
    # Commit all files
    repo = Repo(temp_git_repo)
    repo.index.add(['src/main.py', 'src/utils.py', 'tests/test_main.py'])
    repo.index.commit("Add sample Python project")
    
    return temp_git_repo


@pytest.fixture
def mock_gemini_response():
    """Mock response from Gemini API."""
    return {
        'review': '''## Code Review Results

### 🔴 Critical Issues

1. **Missing Error Handling in Calculator**
   - The `divide` method doesn't handle division by zero
   - File: `src/main.py`, Line: 15
   - Recommendation: Add a check for zero denominator

### ⚠️ Warnings

1. **Email Validation Too Permissive**
   - The regex pattern in `validate_email` allows some invalid emails
   - File: `src/utils.py`, Line: 7
   - Consider using a more robust email validation library

### 💡 Suggestions

1. **Add Type Hints**
   - Some functions are missing return type hints
   - This would improve code clarity and IDE support

### ✅ Good Practices

1. **Clear Documentation**
   - All functions have docstrings
   - Good separation of concerns between modules
''',
        'navigation_history': [
            {
                'function': 'read_file',
                'args': {'filepath': 'src/main.py'},
                'result_preview': '"""Main module...'
            },
            {
                'function': 'read_file', 
                'args': {'filepath': 'src/utils.py'},
                'result_preview': '"""Utility functions...'
            },
            {
                'function': 'find_usages',
                'args': {'symbol_name': 'Calculator'},
                'result_preview': 'Found in tests/test_main.py...'
            }
        ],
        'navigation_summary': {
            'files_cached': 3,
            'total_tokens_estimate': 1500,
            'files_read': ['src/main.py', 'src/utils.py', 'tests/test_main.py'],
            'index_stats': {
                'total_files': 5,
                'source_files': 3,
                'unique_symbols': 6
            }
        },
        'iterations': 3
    }


# E2E test markers and configuration
def pytest_configure(config):
    """Add custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test requiring Gemini API"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture
def mock_gemini_for_e2e(monkeypatch):
    """Mock Gemini responses for E2E tests based on code patterns.
    
    NOTE: This mock validates the CLI integration pipeline but does not test
    the effectiveness of the prompts themselves. The mock contains hardcoded
    logic to simulate finding issues rather than using the actual prompts.
    
    For true prompt validation:
    - Use the --real flag with run_e2e_tests.py
    - Run manual tests with the real Gemini API
    - Consider implementing record-and-replay testing in the future
    """
    
    def create_mock_review(initial_context, *args, **kwargs):
        """Create a mock review based on the code context."""
        review_parts = []
        
        # Check for various patterns in the context
        context_lower = initial_context.lower()
        
        # Check for missing tests
        if "multiply" in context_lower and "def test_multiply" not in context_lower:
            review_parts.append("""FILE: src/calculator.py
LINE: 10
ISSUE: Missing test coverage for multiply() method
FIX: Add test cases for the multiply method in tests/test_calculator.py""")
        
        if "divide" in context_lower and "def test_divide" not in context_lower:
            review_parts.append("""FILE: src/calculator.py
LINE: 14
ISSUE: Missing test coverage for divide() method
FIX: Add test cases for the divide method, including edge case for division by zero""")
        
        # Check for README violations
        if "global" in context_lower and "cache = {}" in initial_context:
            review_parts.append("""FILE: src/service.py
LINE: 4
ISSUE: Global state violation - violates development principle #4
FIX: Use dependency injection instead of global variables""")
        
        if "def save_data(self, data):" in initial_context:
            review_parts.append("""FILE: src/service.py
LINE: 23
ISSUE: Missing type hints - violates development principle #2
FIX: Add type hints: def save_data(self, data: dict) -> str:""")
        
        # Check for security issues
        if "sql" in context_lower and ("f\"" in initial_context or "f'" in initial_context):
            review_parts.append("""FILE: src/auth.py
LINE: 8
ISSUE: SQL injection vulnerability in query construction
FIX: Use parameterized queries instead of string formatting""")
        
        # Check for performance anti-patterns
        if "o(n²)" in context_lower or "quadratic" in context_lower:
            review_parts.append("""FILE: src/data_processor.py
LINE: 8
ISSUE: O(n²) algorithm for duplicate detection when O(n) solution exists
FIX: Use a set-based approach for linear time complexity""")
        
        # Check for bugs
        if "calculate_discount" in initial_context and "price * discount_percent / 100" in initial_context:
            review_parts.append("""FILE: src/validator.py
LINE: 8
ISSUE: Incorrect calculation - returns discount amount instead of final price
FIX: Change to: return price * (1 - discount_percent / 100)""")
        
        return {
            'review': "HIGH PRIORITY ISSUES:\n\n" + "\n\n".join(review_parts) if review_parts else "No critical issues found.",
            'navigation_history': [],
            'navigation_summary': {},
            'iterations': 1,
            'token_details': {'input_tokens': 1000, 'output_tokens': 500, 'total_tokens': 1500}
        }
    
    def mock_review_method(*args, **kwargs):
        initial_context = args[0] if args else kwargs.get('initial_context', '')
        return create_mock_review(initial_context)
    
    # Mock the review_code method
    monkeypatch.setattr(
        "llm_review.gemini_client.GeminiClient.review_code",
        mock_review_method
    )