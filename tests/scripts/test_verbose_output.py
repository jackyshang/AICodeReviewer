#!/usr/bin/env python3
"""Test verbose output to verify tool usage is displayed."""

import sys
from io import StringIO
from reviewer.review_formatter import ReviewFormatter

def test_verbose_scenarios():
    """Test different verbose output scenarios."""
    
    formatter = ReviewFormatter()
    
    # Test data with navigation history
    review_data = {
        'review': 'Test review content',
        'navigation_history': [
            {
                'function': 'read_file',
                'args': {'filepath': 'src/main.py'},
                'result_preview': 'File content...'
            },
            {
                'function': 'search_symbol',
                'args': {'symbol_name': 'authenticate'},
                'result_preview': 'Found in auth.py...'
            },
            {
                'function': 'find_usages',
                'args': {'symbol_name': 'Database'},
                'result_preview': 'Used in 5 files...'
            }
        ],
        'navigation_summary': {
            'files_cached': 3,
            'index_stats': {'total_files': 100}
        },
        'repo_info': {
            'repo_path': '/test/repo',
            'current_branch': 'main'
        },
        'changed_files': {
            'modified': ['file1.py', 'file2.py']
        }
    }
    
    print("="*60)
    print("TEST 1: Default (Compact, No Verbose)")
    print("="*60)
    formatter.display_review_terminal(review_data, verbose=False, human_format=False, show_all=False)
    
    print("\n" + "="*60)
    print("TEST 2: Verbose + Human Format")
    print("="*60)
    formatter.display_review_terminal(review_data, verbose=True, human_format=True, show_all=False)
    
    print("\n" + "="*60)
    print("TEST 3: Verbose + Compact Format")
    print("="*60)
    formatter.display_review_terminal(review_data, verbose=True, human_format=False, show_all=False)
    
    print("\n" + "="*60)
    print("EXPLANATION OF VERBOSE BEHAVIOR")
    print("="*60)
    print("""
When --verbose is used, you should see:

1. During execution (real-time):
   → Calling read_file({'filepath': 'src/main.py'})
   → Calling search_symbol({'symbol_name': 'authenticate'})
   ← Received response (iteration 1)

2. In final output with --human:
   - Repository info
   - Changed files list
   - Navigation Summary table
   - Efficiency report

3. In final output without --human:
   - Just the compact review (no navigation shown)

The real-time tool usage is controlled by show_progress parameter
passed to gemini.review_code() in cli.py.
""")

if __name__ == "__main__":
    test_verbose_scenarios()