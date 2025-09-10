# Installation Guide for LLM Review Tool

## Prerequisites

- Python 3.8 or higher
- Git
- A Gemini API key from Google

## Quick Install (Recommended)

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/pr-reviewer.git
cd pr-reviewer
```

### 2. Create a virtual environment

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install the tool

```bash
pip install -e .
```

This installs the tool in "editable" mode, so you can update the code without reinstalling.

### 4. Set up your Gemini API key

```bash
# On macOS/Linux
export GEMINI_API_KEY="your-api-key-here"

# On Windows
set GEMINI_API_KEY=your-api-key-here

# Or add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
```

Get your API key from: https://makersuite.google.com/app/apikey

## Alternative Installation Methods

### Install from PyPI (when available)

```bash
pip install llm-review
```

### Install from GitHub directly

```bash
pip install git+https://github.com/yourusername/pr-reviewer.git
```

### Development Installation

```bash
# Clone and install with all development dependencies
git clone https://github.com/yourusername/pr-reviewer.git
cd pr-reviewer
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Verify Installation

### 1. Check the tool is installed

```bash
llm-review --help
```

You should see:
```
Usage: llm-review [OPTIONS]

  LLM Review - AI-powered code review with intelligent navigation.

Options:
  -v, --verbose           Enable verbose output
  -d, --debug            Enable debug mode (show API requests/responses)
  -o, --output-file PATH  Save review to markdown file
  --include-unchanged     Include unchanged files for context
  -c, --config PATH       Path to config file
  --no-spinner           Disable progress spinner
  --help                 Show this message and exit.
```

### 2. Check your API key

```bash
echo $GEMINI_API_KEY
```

### 3. Run a test review

Create a test file and run the tool:

```bash
# Create a test file
echo "def divide(a, b): return a/b" > test.py
git add test.py
git commit -m "Add test file"

# Make a change
echo "def divide(a, b): return a/b  # Bug: no zero check" > test.py

# Run review
llm-review
```

## Platform-Specific Instructions

### macOS

```bash
# Install using Homebrew (if we add formula)
brew tap yourusername/llm-review
brew install llm-review

# Or use pipx for isolated installation
pipx install llm-review
```

### Ubuntu/Debian

```bash
# Ensure Python 3.8+ is installed
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# Follow general installation steps
```

### Windows

```powershell
# Using PowerShell
# Ensure Python is installed from python.org

# Clone repository
git clone https://github.com/yourusername/pr-reviewer.git
cd pr-reviewer

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install
pip install -e .

# Set API key (PowerShell)
$env:GEMINI_API_KEY = "your-api-key-here"
```

## Docker Installation (Optional)

Create a Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install the package
COPY . .
RUN pip install -e .

# Set entrypoint
ENTRYPOINT ["llm-review"]
```

Build and run:

```bash
# Build image
docker build -t llm-review .

# Run with current directory mounted
docker run -v $(pwd):/workspace -w /workspace \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  llm-review
```

## Configuration (Optional)

Create `.llm-review.yaml` in your project:

```yaml
review:
  provider: gemini-1.5-pro
  navigation:
    max_files_per_review: 50
  output:
    format: markdown
    show_navigation_path: true
    show_token_usage: true
    show_cost: true
```

## Troubleshooting

### "Command not found: llm-review"

The installation directory might not be in your PATH. Try:

```bash
# Run directly with Python
python -m llm_review.cli

# Or reinstall
pip uninstall llm-review
pip install -e .
```

### "No module named 'llm_review'"

Make sure you're in the virtual environment:

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### "GEMINI_API_KEY not found"

Set your API key:

```bash
export GEMINI_API_KEY="your-key-here"
```

### SSL Certificate errors

If you get SSL errors:

```bash
pip install --upgrade certifi
```

### Permission errors

On macOS/Linux, you might need to use `pip3` instead of `pip`:

```bash
pip3 install -e .
```

## Updating the Tool

To update to the latest version:

```bash
cd pr-reviewer
git pull
pip install -e . --upgrade
```

## Uninstalling

```bash
pip uninstall llm-review
```

## Next Steps

1. Read the [Quick Start Guide](QUICKSTART.md)
2. Check out [usage examples](TEST_GUIDE.md)
3. Configure for your project with `.llm-review.yaml`
4. Run `llm-review --help` for all options

## Support

- GitHub Issues: https://github.com/yourusername/pr-reviewer/issues
- Documentation: [README.md](README.md)