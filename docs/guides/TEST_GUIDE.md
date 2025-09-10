# LLM Review Tool - Testing Guide

## Overview

This guide explains how to test and validate that the LLM Review tool is working correctly. We provide comprehensive end-to-end testing that creates real code scenarios and verifies the tool identifies expected issues.

## Quick Test

Run the complete test suite:

```bash
# Make sure you have your API key set
export GEMINI_API_KEY="your-api-key-here"

# Run the full test
./run_full_test.sh
```

This will:
1. Create 5 test scenarios with different code issues
2. Run the LLM Review tool on each scenario
3. Analyze results to verify correct issue detection
4. Generate a validation report

## Test Scenarios

### Scenario 1: Security Vulnerabilities
- **Files Modified**: `src/app.py`
- **Issues Introduced**:
  - SQL injection vulnerability
  - Missing authentication on DELETE endpoint
  - Direct string interpolation in queries
- **Expected Detection**: Critical security issues

### Scenario 2: Missing Error Handling
- **Files Added**: `src/calculator.py`
- **Issues Introduced**:
  - Division by zero not handled
  - No input validation
  - Missing error handling for invalid inputs
  - No checks for empty lists
- **Expected Detection**: Critical errors and warnings

### Scenario 3: Performance Issues
- **Files Added**: `src/data_processor.py`
- **Issues Introduced**:
  - O(n²) algorithm instead of O(n)
  - Memory leaks (cache without cleanup)
  - Inefficient string concatenation
  - Recursive Fibonacci without memoization
- **Expected Detection**: Performance warnings

### Scenario 4: Code Style Issues
- **Files Added**: `src/messy_code.py`
- **Issues Introduced**:
  - Global variables
  - Poor naming conventions
  - Missing type hints
  - Functions doing too many things
  - Magic numbers
- **Expected Detection**: Style and maintainability issues

### Scenario 5: Missing Test Coverage
- **Files Added**: `src/auth.py`
- **Issues Introduced**:
  - Complex authentication logic without tests
  - Permission management without tests
  - Security-critical code untested
- **Expected Detection**: Test coverage warnings

## Manual Testing

### 1. Run Demo Only

```bash
python demo.py
```

This creates test scenarios and runs the tool, saving results to `demo_results/`.

### 2. Analyze Results Only

```bash
python analyze_demo_results.py
```

This analyzes the latest demo results and validates issue detection.

### 3. Test on Your Own Code

```bash
# Make changes to any git repository
cd /path/to/your/repo

# Run the tool
llm-review

# Or save to file
llm-review --output-file review.md
```

## Understanding Results

### Demo Results Structure

```
demo_results/
└── 20240115_143022/          # Timestamp directory
    ├── README.md              # Overview of test run
    ├── summary.json           # Test execution summary
    ├── validation_report.md   # Detailed validation results
    ├── scenario_1_*.md        # Review output for each scenario
    ├── scenario_1_stdout.txt  # Raw stdout
    └── scenario_1_stderr.txt  # Raw stderr
```

### Validation Metrics

The tool is considered working if:
- ✅ All 5 scenarios run successfully
- ✅ At least 70% of expected issues are detected
- ✅ Navigation is efficient (reads relevant files)
- ✅ Provides actionable feedback

### Reading the Validation Report

The `validation_report.md` shows:
- **Issue Detection Rate**: Percentage of expected issues found
- **Navigation Efficiency**: How many files were explored
- **Per-Scenario Results**: What was found vs. missed
- **Overall Pass/Fail Status**

## Debugging Failed Tests

### If API Key Issues

```bash
# Check if key is set
echo $GEMINI_API_KEY

# Set the key
export GEMINI_API_KEY="your-key-here"
```

### If Import Errors

```bash
# Ensure you're in virtual environment
source venv/bin/activate

# Reinstall
pip install -e .
```

### If Tool Crashes

Check the stderr files:
```bash
cat demo_results/latest/scenario_*_stderr.txt
```

### If Detection Rate is Low

1. Check the markdown output files to see what was actually detected
2. The AI might use different terminology - check `analyze_demo_results.py` patterns
3. Ensure your API key has sufficient quota

## Expected Success Metrics

When working correctly:
- **Security Issues**: 90%+ detection rate
- **Error Handling**: 80%+ detection rate  
- **Performance Issues**: 70%+ detection rate
- **Style Issues**: 70%+ detection rate
- **Test Coverage**: 80%+ detection rate
- **Overall**: 75%+ average

## Advanced Testing

### Custom Scenarios

Edit `demo.py` to add your own test scenarios:

```python
def scenario_6_custom(temp_dir: Path) -> DemoScenario:
    """Your custom scenario."""
    scenario = DemoScenario(
        "Custom Issue",
        "Description of what you're testing"
    )
    
    # Add your test code
    (temp_dir / "src" / "custom.py").write_text('''
    # Your problematic code here
    ''')
    
    scenario.repo_path = temp_dir
    return scenario
```

### Performance Testing

Time the tool on larger codebases:

```bash
time llm-review --no-spinner
```

### Token Usage Analysis

Check efficiency in the output:
- Files explored vs. total files
- Estimated tokens used
- Cost estimate

## Continuous Validation

Run tests after any code changes:

```bash
# Run unit tests
pytest

# Run end-to-end test
./run_full_test.sh
```

## Success Indicators

You know the tool is working when:
1. ✅ Demo completes without errors
2. ✅ Validation report shows "PASSED"
3. ✅ Detection rate > 70%
4. ✅ Navigation is efficient (< 10% of files read)
5. ✅ Reviews are actionable and accurate