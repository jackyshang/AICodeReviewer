#!/usr/bin/env python3
"""Test spinner functionality."""

import time
from reviewer.review_formatter import ReviewFormatter

def test_spinner():
    """Test the spinner display."""
    formatter = ReviewFormatter()
    
    print("Testing spinner...")
    
    # Test the spinner
    with formatter.show_progress("🤖 Reviewing code...") as progress:
        task = progress.add_task("Processing", total=100)
        
        for i in range(100):
            time.sleep(0.01)  # Simulate work
            progress.update(task, advance=1)
    
    print("Spinner test complete!")
    
    # Test different messages
    messages = [
        "🔍 Analyzing changes...",
        "🧪 Running security checks...",
        "📝 Generating review...",
        "✨ Finalizing results..."
    ]
    
    for msg in messages:
        with formatter.show_progress(msg) as progress:
            task = progress.add_task("", total=None)
            time.sleep(1)
            progress.update(task, completed=100)

if __name__ == "__main__":
    test_spinner()