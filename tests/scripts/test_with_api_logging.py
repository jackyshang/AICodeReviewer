#!/usr/bin/env python3
"""Test with detailed API logging."""

import os
import tempfile
from pathlib import Path
import json
from datetime import datetime

from git import Repo
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Add the current directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from reviewer.git_operations import GitOperations
from reviewer.codebase_indexer import CodebaseIndexer
from reviewer.navigation_tools import NavigationTools
from reviewer.gemini_client import GeminiClient
from reviewer.review_formatter import ReviewFormatter

console = Console()

# Monkey patch the GeminiClient to log API calls
original_review_code = GeminiClient.review_code

def logged_review_code(self, initial_context, max_iterations=20):
    """Wrapped version that logs all API interactions."""
    console.print(Panel("[bold cyan]Starting Gemini API Interaction[/bold cyan]"))
    
    # Log initial context
    console.print("\n[bold yellow]Initial Context Sent to Gemini:[/bold yellow]")
    console.print(Syntax(initial_context[:1000] + "..." if len(initial_context) > 1000 else initial_context, "text"))
    
    # Keep track of all interactions
    api_log = []
    
    # Patch the send_message method to log requests/responses
    if hasattr(self, 'model') and self.model:
        original_start_chat = self.model.start_chat
        
        def logged_start_chat(*args, **kwargs):
            chat = original_start_chat(*args, **kwargs)
            original_send_message = chat.send_message
            
            def logged_send_message(message):
                # Log request
                console.print(f"\n[bold magenta]API Request #{len(api_log) + 1}:[/bold magenta]")
                
                if isinstance(message, str):
                    console.print(f"Type: Text Message")
                    console.print(f"Content: {message[:500]}..." if len(message) > 500 else message)
                elif isinstance(message, list):
                    console.print(f"Type: Function Results")
                    for item in message[:3]:  # Show first 3 items
                        if hasattr(item, 'name'):
                            console.print(f"  - Function: {item.name}")
                            if hasattr(item, 'response'):
                                console.print(f"    Response preview: {str(item.response)[:100]}...")
                else:
                    console.print(f"Type: {type(message).__name__}")
                
                # Make actual API call
                response = original_send_message(message)
                
                # Log response
                console.print(f"\n[bold green]API Response:[/bold green]")
                
                if response and response.candidates:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for i, part in enumerate(candidate.content.parts[:3]):  # First 3 parts
                            if hasattr(part, 'text') and part.text:
                                console.print(f"Part {i+1} (Text): {part.text[:200]}...")
                            elif hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                console.print(f"Part {i+1} (Function Call):")
                                console.print(f"  Function: {fc.name}")
                                console.print(f"  Args: {dict(fc.args) if fc.args else {}}")
                
                # Log to list
                api_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "request_type": type(message).__name__,
                    "response_parts": len(response.candidates[0].content.parts) if response and response.candidates else 0
                })
                
                return response
            
            chat.send_message = logged_send_message
            return chat
        
        self.model.start_chat = logged_start_chat
    
    # Call original method
    result = original_review_code(self, initial_context, max_iterations)
    
    # Log summary
    console.print(Panel.fit(
        f"[bold]API Interaction Summary[/bold]\n"
        f"Total Requests: {len(api_log)}\n"
        f"Navigation Steps: {len(result.get('navigation_history', []))}\n"
        f"Final Review Length: {len(result.get('review', ''))} chars",
        border_style="green"
    ))
    
    return result

# Apply the patch
GeminiClient.review_code = logged_review_code

def test_scenario():
    """Test a single scenario with API logging."""
    
    # Check API key
    if not os.environ.get('GEMINI_API_KEY'):
        console.print("[red]Error: GEMINI_API_KEY not set[/red]")
        return
    
    console.print(Panel.fit("[bold]LLM Review Tool - API Logging Test[/bold]"))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        repo = Repo.init(repo_path)
        
        # Create initial file
        (repo_path / "calculator.py").write_text('''def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
''')
        
        # Commit initial state
        repo.index.add(['calculator.py'])
        repo.index.commit("Initial commit")
        
        # Make changes with issues
        (repo_path / "calculator.py").write_text('''def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def divide(a, b):
    # TODO: Add zero check
    return a / b

def calculate_average(numbers):
    # Will fail on empty list!
    return sum(numbers) / len(numbers)

def unsafe_eval(user_input):
    # Security issue: eval on user input!
    return eval(user_input)
''')
        
        console.print("✅ Test repository created with issues")
        
        # Run the review process
        git_ops = GitOperations(repo_path)
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        nav_tools = NavigationTools(repo_path, index)
        
        gemini = GeminiClient()
        gemini.setup_navigation_tools(nav_tools)
        
        changed_files = git_ops.get_uncommitted_files()
        codebase_summary = indexer.get_index_summary(index)
        diffs = git_ops.get_all_diffs()
        initial_context = gemini.format_initial_context(changed_files, codebase_summary, diffs)
        
        # This will now show all API interactions
        review_result = gemini.review_code(initial_context, max_iterations=5)
        
        # Show final review
        console.print("\n[bold cyan]Final Review:[/bold cyan]")
        console.print(review_result['review'])

if __name__ == "__main__":
    test_scenario()