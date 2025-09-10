#!/usr/bin/env python3
"""Test the improved prompts to verify better code review quality."""

from reviewer.gemini_client import GeminiClient

def test_context_generation():
    """Test that the context now includes diffs and better prompts."""
    
    # Create test data
    changed_files = {
        'modified': ['src/auth.py', 'src/database.py'],
        'added': ['src/security.py']
    }
    
    codebase_summary = "A web application with authentication and database features."
    
    diffs = {
        'src/auth.py': """
@@ -10,7 +10,8 @@ def authenticate(username, password):
     user = db.query(f"SELECT * FROM users WHERE username = '{username}'")
-    if user and user.password == password:
+    # Fixed: This still stores passwords in plain text!
+    if user and user.password == hash_password(password):
         return generate_token(user)
     return None
""",
        'src/database.py': """
@@ -25,6 +25,10 @@ class Database:
     def query(self, sql):
+        # TODO: Add input validation
         cursor = self.conn.cursor()
         cursor.execute(sql)
         return cursor.fetchone()
+        
+    def close(self):
+        self.conn.close()
"""
    }
    
    # Test critical-only mode (default)
    client = GeminiClient(api_key="test", model_name="test-model")
    context = client.format_initial_context(changed_files, codebase_summary, diffs, show_all=False)
    
    print("="*60)
    print("CRITICAL-ONLY MODE (Default)")
    print("="*60)
    
    # Check key improvements
    checks = {
        "✓ Comprehensive prompt": "thorough security and quality review" in context,
        "✓ Expanded critical issues": "logic errors, or edge cases" in context,
        "✓ Encourages exploration": "explore related files and understand the full context" in context,
        "✓ Includes git diffs": "## Git Diffs" in context,
        "✓ Shows actual changes": "SELECT * FROM users WHERE username" in context,
        "✓ Compact format specified": "FILE:" in context and "LINE:" in context
    }
    
    for check, passed in checks.items():
        print(f"{check}: {'✅ PASS' if passed else '❌ FAIL'}")
    
    # Show a snippet of the context
    print("\nContext snippet:")
    print("-"*40)
    lines = context.split('\n')
    
    # Show the improved prompt section
    for i, line in enumerate(lines[:30]):
        print(line)
    
    print("...")
    
    # Show the diffs section
    if "## Git Diffs" in context:
        diff_start = context.index("## Git Diffs")
        print(context[diff_start:diff_start+500])
    
    # Test full mode
    print("\n" + "="*60)
    print("FULL MODE (--full flag)")
    print("="*60)
    
    context_full = client.format_initial_context(changed_files, codebase_summary, diffs, show_all=True)
    
    full_checks = {
        "✓ Includes suggestions": "SUGGESTIONS (💡)" in context_full,
        "✓ Critical issues": "CRITICAL (🚨)" in context_full,
        "✓ Includes git diffs": "## Git Diffs" in context_full
    }
    
    for check, passed in full_checks.items():
        print(f"{check}: {'✅ PASS' if passed else '❌ FAIL'}")

if __name__ == "__main__":
    test_context_generation()