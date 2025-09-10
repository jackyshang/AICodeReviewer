#!/usr/bin/env python3
"""Test a single scenario to debug issues."""

import os
import tempfile
from pathlib import Path
import traceback

from git import Repo
from rich.console import Console

# Add the current directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from reviewer.git_operations import GitOperations
from reviewer.codebase_indexer import CodebaseIndexer
from reviewer.navigation_tools import NavigationTools
from reviewer.gemini_client import GeminiClient
from reviewer.review_formatter import ReviewFormatter

console = Console()

def test_scenario():
    """Test a single scenario with detailed output."""
    
    # Check API key
    if not os.environ.get('GEMINI_API_KEY'):
        console.print("[red]Error: GEMINI_API_KEY not set[/red]")
        return
    
    console.print("[bold]Creating test repository...[/bold]")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        repo = Repo.init(repo_path)
        
        # Create initial file
        (repo_path / "main.py").write_text('''def greet(name):
    return f"Hello, {name}!"

def calculate(a, b):
    return a + b
''')
        
        # Commit initial state
        repo.index.add(['main.py'])
        repo.index.commit("Initial commit")
        
        console.print("✅ Repository created")
        
        # Make changes with issues
        (repo_path / "main.py").write_text('''def greet(name):
    return f"Hello, {name}!"

def calculate(a, b):
    return a + b

def divide(a, b):
    # Missing zero check - will crash!
    return a / b

def process_user_input(user_id):
    # SQL injection vulnerability!
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    print(f"Would execute: {query}")
    return query
''')
        
        console.print("✅ Added problematic code")
        
        try:
            # Step 1: Git operations
            console.print("\n[bold]Step 1: Checking git status...[/bold]")
            git_ops = GitOperations(repo_path)
            has_changes = git_ops.has_uncommitted_changes()
            console.print(f"Has changes: {has_changes}")
            
            changed_files = git_ops.get_uncommitted_files()
            console.print(f"Changed files: {changed_files}")
            
            # Step 2: Build index
            console.print("\n[bold]Step 2: Building codebase index...[/bold]")
            indexer = CodebaseIndexer(repo_path)
            index = indexer.build_index()
            console.print(f"Index built: {index.stats}")
            
            # Step 3: Initialize navigation tools
            console.print("\n[bold]Step 3: Setting up navigation tools...[/bold]")
            nav_tools = NavigationTools(repo_path, index)
            
            # Test navigation tools
            console.print("Testing read_file...")
            content = nav_tools.read_file("main.py")
            console.print(f"Read {len(content)} characters")
            
            # Step 4: Initialize Gemini
            console.print("\n[bold]Step 4: Initializing Gemini client...[/bold]")
            gemini = GeminiClient()
            gemini.setup_navigation_tools(nav_tools)
            console.print("✅ Gemini initialized")
            
            # Step 5: Create context
            console.print("\n[bold]Step 5: Creating initial context...[/bold]")
            codebase_summary = indexer.get_index_summary(index)
            diffs = git_ops.get_all_diffs()
            initial_context = gemini.format_initial_context(changed_files, codebase_summary, diffs)
            console.print(f"Context size: {len(initial_context)} characters")
            
            # Step 6: Run review
            console.print("\n[bold]Step 6: Running AI review...[/bold]")
            review_result = gemini.review_code(initial_context, max_iterations=5)
            
            console.print("\n[bold green]✅ Review completed![/bold green]")
            console.print(f"Iterations: {review_result['iterations']}")
            console.print(f"Navigation steps: {len(review_result['navigation_history'])}")
            
            # Show navigation history
            if review_result['navigation_history']:
                console.print("\n[bold]Navigation History:[/bold]")
                for i, step in enumerate(review_result['navigation_history'], 1):
                    console.print(f"{i}. {step['function']}({step['args']})")
            
            # Show review
            console.print("\n[bold]Review Result:[/bold]")
            console.print(review_result['review'][:500] + "..." if len(review_result['review']) > 500 else review_result['review'])
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Error occurred:[/bold red]")
            console.print(f"Error type: {type(e).__name__}")
            console.print(f"Error message: {str(e)}")
            console.print("\n[bold]Full traceback:[/bold]")
            traceback.print_exc()

if __name__ == "__main__":
    test_scenario()