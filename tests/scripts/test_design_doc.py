#!/usr/bin/env python3
"""Test the design document feature."""

from pathlib import Path
from reviewer.gemini_client import GeminiClient

def test_design_doc_context():
    """Test that design documents are properly included in context."""
    
    # Test data
    changed_files = {
        'modified': ['src/auth.py', 'src/api/users.py']
    }
    
    codebase_summary = "Web application with authentication and user management."
    
    diffs = {
        'src/auth.py': """
@@ -10,7 +10,7 @@ def hash_password(password):
-    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
+    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(8))  # Faster hashing
""",
        'src/api/users.py': """
@@ -45,7 +45,7 @@ def get_user(user_id):
     user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
     if user:
-        return {'status': 'success', 'data': user}
+        return {'user': user}  # Simplified response
"""
    }
    
    design_doc = """# Project Design Document

## Security Requirements
- Passwords MUST be hashed using bcrypt with minimum 12 rounds
- All database queries MUST use parameterized queries

## API Standards  
- All API responses must include 'status' field
- Responses follow format: {'status': 'success/error', 'data': {...}}
"""
    
    # Create client and generate context
    client = GeminiClient(api_key="test", model_name="test")
    
    print("="*60)
    print("TEST: Context WITH Design Document")
    print("="*60)
    
    context = client.format_initial_context(
        changed_files, 
        codebase_summary, 
        diffs,
        show_all=False,
        design_doc=design_doc
    )
    
    # Check that design doc is included
    if "## Project Design Document" in context:
        print("✅ Design document section found")
    else:
        print("❌ Design document section missing")
    
    if "USE THIS DOCUMENT to understand:" in context:
        print("✅ Design doc instructions included")
    else:
        print("❌ Design doc instructions missing")
        
    if "Passwords MUST be hashed using bcrypt with minimum 12 rounds" in context:
        print("✅ Design doc content included")
    else:
        print("❌ Design doc content missing")
    
    # Show relevant sections
    print("\n" + "-"*40)
    print("Context Preview (Design Doc Section):")
    print("-"*40)
    
    if "## Project Design Document" in context:
        start = context.index("## Project Design Document")
        end = context.index("## Changed Files", start)
        print(context[start:end])
    
    print("\n" + "="*60)
    print("TEST: Context WITHOUT Design Document")
    print("="*60)
    
    context_no_doc = client.format_initial_context(
        changed_files,
        codebase_summary,
        diffs,
        show_all=False,
        design_doc=None
    )
    
    if "## Project Design Document" not in context_no_doc:
        print("✅ Design doc correctly omitted when not provided")
    else:
        print("❌ Design doc section present when it shouldn't be")
    
    print("\n" + "="*60)
    print("EXPECTED REVIEW OUTPUT WITH DESIGN DOC:")
    print("="*60)
    print("""
FILE: src/auth.py
LINE: 11
ISSUE: Password hashing reduced to 8 rounds, violating security requirement of minimum 12 rounds
FIX: Use bcrypt.gensalt(12) as specified in design document

FILE: src/api/users.py  
LINE: 46
ISSUE: SQL injection vulnerability - user_id directly interpolated into query
FIX: Use parameterized query: db.query("SELECT * FROM users WHERE id = ?", (user_id,))

FILE: src/api/users.py
LINE: 48
ISSUE: API response missing required 'status' field per API standards
FIX: Return {'status': 'success', 'data': {'user': user}} to match documented format
""")

if __name__ == "__main__":
    test_design_doc_context()