# End-to-End Testing Guide

## Overview

This project has comprehensive E2E tests that validate the complete code review functionality, including the new session persistence feature.

## Test Structure

### 1. Unit Tests (`test_session_persistence.py`)
- Tests individual components with mocks
- Fast, reliable, no API costs
- 17 tests covering all session persistence functionality

### 2. E2E Tests with Mocks (`test_e2e_review_scenarios.py`)
- Tests the full CLI pipeline with mocked Gemini responses
- Validates integration without API costs
- Uses `mock_gemini_for_e2e` fixture

### 3. E2E Tests with Real API (`test_e2e_real_gemini.py`, `test_e2e_session_persistence.py`)
- Tests with actual Gemini API
- Validates real code review quality
- Requires GEMINI_API_KEY environment variable

## Running Tests

### Unit Tests Only
```bash
pytest tests/test_session_persistence.py -v
```

### E2E Tests with Mocks (Default)
```bash
python run_e2e_tests.py
```

### E2E Tests with Real Gemini API
```bash
# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Run all E2E tests with real API
python run_e2e_tests.py --real

# Run specific E2E test
pytest tests/test_e2e_real_gemini.py -v -m integration
```

## Session Persistence E2E Tests

The `test_e2e_session_persistence.py` file includes:

1. **test_session_creation_and_continuation**: Verifies that sessions persist across multiple reviews
2. **test_cross_project_session_isolation**: Ensures sessions don't leak between projects
3. **test_service_unavailable_fallback**: Tests graceful fallback when service is down
4. **test_ai_generated_code_review_with_session**: Tests AI-generated mode with sessions
5. **test_prototype_mode_with_session**: Tests prototype mode with sessions
6. **test_session_list_and_clear**: Tests session management operations

## Important Notes

1. **Real API Tests**: These cost money! Use sparingly and only when needed.
2. **Service Requirement**: Session persistence tests require the service to be running:
   ```bash
   python -m llm_review.service
   ```
3. **Environment**: Tests create temporary git repositories to simulate real usage.

## Test Coverage

- **Code Review Quality**: Tests verify that the tool catches real issues like:
  - Missing error handling
  - Security vulnerabilities
  - Performance problems
  - Type safety issues
  - AI hallucinations and incomplete implementations

- **Session Features**: Tests verify:
  - Sessions persist conversation history
  - Sessions are project-scoped
  - Fallback works when service is unavailable
  - Different review modes work with sessions

## Debugging Failed Tests

If E2E tests fail:

1. Check API key is set: `echo $GEMINI_API_KEY`
2. Check service is running: `curl http://localhost:8765/health`
3. Run with verbose output: `pytest -v -s tests/test_e2e_real_gemini.py`
4. Check logs: `tail -f /tmp/llm-review.error.log`

## Writing New E2E Tests

When adding new features:

1. Add unit tests first (fast feedback)
2. Add E2E tests with mocks (integration validation)
3. Add E2E tests with real API (quality validation)

Example structure:
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_new_feature(self, temp_repo):
    # Create test code
    # Run llm-review
    # Assert on real output
```