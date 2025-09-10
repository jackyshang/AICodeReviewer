# Quick Start Guide

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/pr-reviewer.git
   cd pr-reviewer
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install the package:**
   ```bash
   pip install -e .
   ```

4. **Set up your Gemini API key:**
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

   Get your API key from: https://makersuite.google.com/app/apikey

## Usage

### Basic Review

Review uncommitted changes in your current repository:

```bash
llm-review
```

### Save Review to File

```bash
llm-review --output-file review.md
```

### Verbose Output

```bash
llm-review --verbose
```

### Custom Configuration

Create a `.llm-review.yaml` file in your project root:

```yaml
review:
  provider: gemini-1.5-pro
  navigation:
    exploration_limits:
      max_files_per_review: 30
      timeout_seconds: 180
```

## Example Output

```
🔍 Code Review Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Repository: /Users/you/myproject
Branch: feature/new-auth
Provider: Gemini 1.5 Pro (AI Navigation)

📝 Changed Files:

  Modified:
    • src/auth/login.py
    • src/auth/tokens.py
    • tests/test_auth.py

🧭 Navigation Summary:
┏━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Step ┃ Action          ┃ Target               ┃
┡━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 1   │ Read File       │ src/auth/login.py    │
│ 2   │ Search Symbol   │ SecurityException    │
│ 3   │ Find Usages     │ login               │
│ 4   │ Read File       │ src/api/endpoints.py │
└─────┴─────────────────┴──────────────────────┘

📋 Review Results:

🔴 Critical Issues: 1
⚠️  Warnings: 2
💡 Suggestions: 3

1. **Unhandled Exception** (Critical)
   Your new SecurityException in login.py
   Not caught in api/endpoints.py:78
   Will cause 500 errors in production

💰 Efficiency Report:
Files in repository: 245
Files explored: 6 (2.4%)
Tokens used (est.): 12,450
Estimated cost: $0.0062
```

## Tips

1. **First Run**: The tool will build an index of your codebase. This takes 1-2 seconds but enables efficient navigation.

2. **Token Efficiency**: The AI only reads files it needs to understand your changes, typically 5-15 files instead of hundreds.

3. **Cost**: Most reviews cost less than $0.01 due to intelligent navigation.

4. **Large Codebases**: Works on any size codebase - the AI navigates intelligently rather than reading everything.

## Troubleshooting

**"No GEMINI_API_KEY found"**
- Make sure you've set the environment variable
- Get your key from https://makersuite.google.com/app/apikey

**"Not a git repository"**
- Run the command from within a git repository
- The tool needs git to detect changes

**"No uncommitted changes"**
- Make some changes to your code first
- The tool reviews uncommitted changes only (in MVP)

## Next Steps

- Read the [Design Document](README.md) to understand how it works
- Check `.llm-review.yaml.example` for configuration options
- Run tests with `pytest` to ensure everything works