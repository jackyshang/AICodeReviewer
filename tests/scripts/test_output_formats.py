#!/usr/bin/env python3
"""Test script to demonstrate output formats without API calls."""

from reviewer.review_formatter import ReviewFormatter
from rich.console import Console

def test_compact_output():
    """Test compact output format (default)."""
    print("="*60)
    print("1. COMPACT OUTPUT (Default - for AI agents)")
    print("="*60)
    
    # Simulate what the AI would return in compact format
    review_text = """FILE: test_security.py
LINE: 14
ISSUE: SQL injection vulnerability in user query
FIX: Use parameterized query: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

FILE: test_security.py
LINE: 21
ISSUE: Command injection vulnerability in os.system call
FIX: Use subprocess.run with proper argument list: subprocess.run(['cat', filename])

FILE: test_security.py
LINE: 26
ISSUE: Password stored in plain text
FIX: Hash password using bcrypt before storage"""
    
    # In compact mode, we just print the text directly
    print(review_text)

def test_human_format():
    """Test human-readable format."""
    print("\n" + "="*60)
    print("2. HUMAN-READABLE FORMAT (--human flag)")
    print("="*60)
    
    formatter = ReviewFormatter()
    
    # Simulate review data
    review_data = {
        'review': """### 🚨 CRITICAL ISSUES

#### 1. **test_security.py** - SQL Injection Vulnerability
- **Line 14**: Direct string interpolation in SQL query
- **Risk**: Attackers can inject malicious SQL commands
- **Recommendation**: Use parameterized queries

```python
# Instead of:
query = f"SELECT * FROM users WHERE id = {user_id}"

# Use:
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

#### 2. **test_security.py** - Command Injection
- **Line 21**: Using os.system with user input
- **Risk**: Arbitrary command execution
- **Recommendation**: Use subprocess with proper escaping

### 💡 SUGGESTIONS

#### 1. **test_security.py** - Code Style
- **Line 30**: Missing spaces around operators
- **Line 31**: Unnecessary parentheses in if statement
""",
        'repo_info': {
            'repo_path': '/Users/test/project',
            'current_branch': 'main'
        },
        'changed_files': {
            'modified': ['llm_review/cli.py', 'llm_review/gemini_client.py'],
            'added': ['test_security.py']
        },
        'navigation_history': [],
        'navigation_summary': {}
    }
    
    # Display in human format
    formatter.display_review_terminal(review_data, verbose=False, human_format=True, show_all=True)

def test_full_vs_critical():
    """Test difference between full and critical-only."""
    print("\n" + "="*60)
    print("3. CRITICAL ONLY vs FULL REVIEW")
    print("="*60)
    
    print("\nCritical Only (default):")
    print("-" * 30)
    critical_only = """FILE: test_security.py
LINE: 14
ISSUE: SQL injection vulnerability
FIX: Use parameterized queries

FILE: test_security.py
LINE: 26
ISSUE: Password stored in plain text
FIX: Hash with bcrypt"""
    print(critical_only)
    
    print("\n\nFull Review (--full flag):")
    print("-" * 30)
    full_review = """### 🚨 CRITICAL ISSUES

1. SQL injection vulnerability at line 14
2. Password stored in plain text at line 26

### 💡 SUGGESTIONS

1. Missing spaces around operators at line 30
2. Unused import 'json' at line 36
3. Consider adding type hints for better code clarity"""
    print(full_review)

if __name__ == "__main__":
    # Test all formats
    test_compact_output()
    test_human_format()
    test_full_vs_critical()
    
    print("\n" + "="*60)
    print("SUMMARY OF COMMAND OPTIONS")
    print("="*60)
    print("""
Default:           llm-review                    # Compact, critical only
Human format:      llm-review --human           # Pretty, critical only  
Full review:       llm-review --full            # Compact, all issues
Full + Human:      llm-review --full --human    # Pretty, all issues
Fast mode:         llm-review --fast            # Use Flash model
With details:      llm-review --verbose         # Show progress & tokens
""")