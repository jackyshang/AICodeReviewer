# Code Review Severity Levels

The LLM Review Tool now categorizes all feedback into two distinct severity levels to help you prioritize fixes:

## 🚨 CRITICAL ISSUES - Must Fix Before Merging

These are issues that **must be resolved** before code can be merged. They include:

- **Security vulnerabilities** (e.g., SQL injection, XSS, plain text passwords)
- **Logic errors** that will cause runtime failures (e.g., division by zero, null references)
- **Data loss or corruption risks**
- **Breaking changes** to APIs or contracts
- **Missing critical error handling** that could crash the application
- **Memory leaks** or resource management issues
- **Race conditions** and thread safety issues

## 💡 SUGGESTIONS - Nice to Have Improvements  

These are recommended improvements that enhance code quality but aren't blocking:

- **Code style** inconsistencies
- **Performance optimizations** (unless critical)
- **Missing documentation** or docstrings
- **Type hints** and annotations
- **Refactoring opportunities** for better maintainability
- **Test coverage** improvements
- **Best practice** recommendations
- **Code duplication** that could be refactored
- **Naming conventions** and readability improvements

## How It Works

1. **Gemini 2.5 Pro Preview** analyzes your code changes
2. Uses AI-driven navigation to explore only relevant files
3. Categorizes each issue found based on severity
4. Presents results in clearly separated sections

## Example Output

```
### 🚨 CRITICAL ISSUES

1. **auth.py: SQL Injection vulnerability in login()**
   The query is constructed with string concatenation, allowing SQL injection.
   
2. **payment.py: Credit card number logged in plain text**
   Sensitive payment information is being written to logs.

### 💡 SUGGESTIONS  

1. **utils.py: Add type hints to function parameters**
   Type hints would improve code clarity and enable better IDE support.
   
2. **models.py: Consider using dataclasses**
   The User class could be simplified using Python dataclasses.
```

## Benefits

- **Clear Priorities**: Know exactly what needs fixing vs. what's optional
- **Faster Reviews**: Focus on critical issues first
- **Better Communication**: Team members understand issue severity
- **Compliance Ready**: Ensures security and safety issues are addressed

## Usage

The severity levels are automatically applied when you run:

```bash
llm-review                    # Basic review with severity levels
llm-review --verbose         # See detailed progress
llm-review --debug           # View API interactions
llm-review --output-file review.md  # Save to file
```

## Configuration

You can customize the review behavior in `.llm-review.yaml`:

```yaml
review:
  provider: gemini-2.5-pro-preview-06-05
  severity_levels:
    enabled: true
    critical_threshold: high
    suggestion_threshold: medium
```