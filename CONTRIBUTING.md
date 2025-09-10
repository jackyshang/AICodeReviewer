# Contributing to PR Reviewer

Thank you for your interest in contributing to PR Reviewer! We welcome contributions from the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/pr-reviewer.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest`
6. Commit your changes: `git commit -m "Add your feature"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .

# Set up your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=reviewer

# Run specific test file
pytest tests/test_git_operations.py
```

## Code Style

We use Black for code formatting and Flake8 for linting:

```bash
# Format code
black .

# Check code style
flake8

# Type checking
mypy reviewer/
```

## Submitting Pull Requests

1. Ensure all tests pass
2. Add tests for new functionality
3. Update documentation as needed
4. Follow the existing code style
5. Write clear commit messages
6. Include a description of your changes in the PR

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
- Clear description of the issue
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

## Code of Conduct

Please be respectful and constructive in all interactions. We want this to be a welcoming community for all contributors.

## Questions?

Feel free to open an issue for any questions about contributing!