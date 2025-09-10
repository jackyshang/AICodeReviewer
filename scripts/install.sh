#!/bin/bash
# LLM Review Tool - Installation Script

set -e

echo "================================================"
echo "LLM Review Tool - Installation Script"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python $required_version or higher is required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version found"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Error: git is not installed"
    exit 1
fi
echo "✅ Git is installed"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists, skipping creation"
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install the package
echo ""
echo "Installing LLM Review Tool..."
pip install -e . --quiet
echo "✅ Installation complete"

# Check if GEMINI_API_KEY is set
echo ""
echo "Checking API key..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY environment variable is not set"
    echo ""
    echo "To set your API key:"
    echo "  export GEMINI_API_KEY='your-api-key-here'"
    echo ""
    echo "Get your API key from: https://makersuite.google.com/app/apikey"
else
    echo "✅ GEMINI_API_KEY is set"
fi

# Verify installation
echo ""
echo "Verifying installation..."
if command -v llm-review &> /dev/null; then
    echo "✅ llm-review command is available"
else
    echo "⚠️  llm-review command not found in PATH"
    echo "   You may need to run: source venv/bin/activate"
fi

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Set your API key (if not already done):"
echo "   export GEMINI_API_KEY='your-api-key-here'"
echo ""
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. Run the tool:"
echo "   llm-review --help"
echo ""
echo "For more information, see:"
echo "  - Quick Start: QUICKSTART.md"
echo "  - Full Guide: README.md"
echo "  - Test Guide: TEST_GUIDE.md"
echo ""