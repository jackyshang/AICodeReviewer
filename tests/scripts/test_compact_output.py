#!/usr/bin/env python3
"""Test script to verify compact output implementation."""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return output."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    return result

def main():
    """Test different command variations."""
    
    print("Testing LLM Review Tool - Compact Output Implementation")
    print("="*60)
    
    # Test 1: Default (compact, critical only)
    print("\n1. DEFAULT MODE (compact output, critical issues only)")
    run_command(["llm-review"])
    
    # Test 2: Human format
    print("\n\n2. HUMAN FORMAT (--human flag)")
    run_command(["llm-review", "--human"])
    
    # Test 3: Full review in compact format
    print("\n\n3. FULL REVIEW, COMPACT FORMAT (--full flag)")
    run_command(["llm-review", "--full"])
    
    # Test 4: Full review in human format
    print("\n\n4. FULL REVIEW, HUMAN FORMAT (--full --human)")
    run_command(["llm-review", "--full", "--human"])
    
    # Test 5: With verbose flag
    print("\n\n5. VERBOSE MODE (--verbose)")
    run_command(["llm-review", "--verbose"])
    
    # Test 6: Help text
    print("\n\n6. HELP TEXT")
    run_command(["llm-review", "--help"])

if __name__ == "__main__":
    main()