#!/usr/bin/env python3
"""Test script to verify severity levels in code review."""

import os
import shutil
import tempfile
from pathlib import Path

from reviewer.cli import main
from reviewer.git_operations import GitOperations


def create_test_scenario():
    """Create a test scenario with both critical issues and suggestions."""
    test_dir = tempfile.mkdtemp(prefix="llm_review_severity_test_")
    print(f"Created test directory: {test_dir}")
    
    # Initialize git repo
    os.chdir(test_dir)
    os.system("git init")
    os.system("git config user.email 'test@example.com'")
    os.system("git config user.name 'Test User'")
    
    # Create initial commit
    Path("README.md").write_text("# Test Project\n")
    os.system("git add README.md")
    os.system("git commit -m 'Initial commit'")
    
    # Create a file with multiple issues
    test_code = '''
import os
import json

class UserManager:
    def __init__(self):
        self.users = {}
        
    def add_user(self, username, password):
        # CRITICAL: Storing password in plain text
        self.users[username] = password
        
    def authenticate(self, username, password):
        # CRITICAL: No input validation
        return self.users[username] == password
        
    def save_to_file(self, filename):
        # CRITICAL: No error handling for file operations
        with open(filename, 'w') as f:
            json.dump(self.users, f)
            
    def load_from_file(self, filename):
        # SUGGESTION: Could use pathlib instead of string
        with open(filename, 'r') as f:
            self.users = json.load(f)
            
    def list_users(self):
        # SUGGESTION: Could return sorted list
        return list(self.users.keys())
        
    def delete_user(self, username):
        # CRITICAL: No check if user exists
        del self.users[username]
        
    # SUGGESTION: Missing docstrings for all methods
    # SUGGESTION: No type hints used
    
def divide_numbers(a, b):
    # CRITICAL: No zero division check
    return a / b
    
def process_data(data):
    # SUGGESTION: Variable name 'x' is not descriptive
    x = data * 2
    return x
'''
    
    Path("user_manager.py").write_text(test_code)
    
    # Create a C# file with issues
    cs_code = '''
using System;
using System.Collections.Generic;

namespace TestApp
{
    public class DataProcessor
    {
        private List<string> data;
        
        public DataProcessor()
        {
            // CRITICAL: Null reference - data not initialized
        }
        
        public void AddData(string item)
        {
            // CRITICAL: Will throw NullReferenceException
            data.Add(item);
        }
        
        public string GetData(int index)
        {
            // CRITICAL: No bounds checking
            return data[index];
        }
        
        public void ProcessAll()
        {
            // SUGGESTION: Could use LINQ instead of foreach
            foreach (var item in data)
            {
                Console.WriteLine(item);
            }
        }
        
        // SUGGESTION: Class lacks proper error handling
        // SUGGESTION: No async support for I/O operations
    }
}
'''
    
    Path("DataProcessor.cs").write_text(cs_code)
    
    return test_dir


def main_test():
    """Run the severity test."""
    # Create test scenario
    test_dir = create_test_scenario()
    
    print("\n" + "="*80)
    print("TESTING SEVERITY LEVELS IN CODE REVIEW")
    print("="*80)
    print("\nThis test verifies that the tool properly categorizes issues as:")
    print("1. 🚨 CRITICAL ISSUES - Must be fixed before merging")
    print("2. 💡 SUGGESTIONS - Good to have improvements")
    print("\n" + "="*80 + "\n")
    
    # Set API key
    if not os.environ.get('GEMINI_API_KEY'):
        print("ERROR: Please set GEMINI_API_KEY environment variable")
        return
    
    # Run the review with verbose output
    print("Running code review with severity categorization...\n")
    os.system("llm-review --verbose")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print("\nThe review above should show:")
    print("- CRITICAL issues for security vulnerabilities, null references, etc.")
    print("- SUGGESTIONS for style improvements, refactoring opportunities, etc.")
    print("\nTest directory:", test_dir)
    print("To clean up: rm -rf", test_dir)


if __name__ == "__main__":
    main_test()