#!/usr/bin/env python3
"""Runner script for end-to-end tests."""

import sys
import subprocess
import os

def run_e2e_tests(use_mock=True):
    """Run the end-to-end tests.
    
    Args:
        use_mock: If True, use mocked Gemini responses. If False, use real API.
    """
    # Use the current environment which may include sourced .env variables
    env = os.environ.copy()
    
    if use_mock:
        print("Running E2E tests with mocked Gemini responses...")
        cmd = ["pytest", "-v", "-m", "integration", "--tb=short", "tests/test_e2e_review_scenarios.py", "tests/test_e2e_integration.py"]
    else:
        print("Running E2E tests with real Gemini API...")
        print("Make sure GEMINI_API_KEY is set in your environment!")
        # Include our new session persistence E2E tests
        cmd = ["pytest", "-v", "-m", "integration", "--tb=short", "-s", 
               "tests/test_e2e_review_scenarios.py", 
               "tests/test_e2e_integration.py",
               "tests/test_e2e_session_persistence.py",
               "tests/test_e2e_real_gemini.py"]
    
    # Run the tests
    result = subprocess.run(cmd, env=env)
    return result.returncode

if __name__ == "__main__":
    # Check for --real flag to use real API
    use_mock = "--real" not in sys.argv
    
    if not use_mock and not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY environment variable not set!")
        print("Either set the API key or run with mocked responses (default)")
        sys.exit(1)
    
    exit_code = run_e2e_tests(use_mock)
    sys.exit(exit_code)