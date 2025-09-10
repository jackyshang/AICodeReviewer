#!/bin/bash
# Install LLM Review Tool system-wide

set -e

echo "================================================"
echo "LLM Review Tool - System Installation"
echo "================================================"
echo ""

# Get the current directory
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create a symlink in a directory that's in PATH
SYMLINK_DIR="$HOME/.local/bin"
SYMLINK_PATH="$SYMLINK_DIR/llm-review"

# Create ~/.local/bin if it doesn't exist
if [ ! -d "$SYMLINK_DIR" ]; then
    echo "Creating $SYMLINK_DIR directory..."
    mkdir -p "$SYMLINK_DIR"
fi

# Create the symlink
echo "Creating symlink..."
ln -sf "$INSTALL_DIR/llm-review-wrapper.sh" "$SYMLINK_PATH"
echo "✅ Symlink created at $SYMLINK_PATH"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$SYMLINK_DIR:"* ]]; then
    echo ""
    echo "⚠️  Warning: $SYMLINK_DIR is not in your PATH"
    echo ""
    echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then reload your shell or run:"
    echo "  source ~/.bashrc  # or ~/.zshrc"
else
    echo "✅ $SYMLINK_DIR is already in PATH"
fi

# Set up API key in shell profile if not already set
if [ -z "$GEMINI_API_KEY" ]; then
    echo ""
    echo "📝 Setting up API key..."
    echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export GEMINI_API_KEY='your-api-key-here'"
fi

echo ""
echo "================================================"
echo "System Installation Complete!"
echo "================================================"
echo ""
echo "You can now use 'llm-review' from anywhere!"
echo ""
echo "Try it:"
echo "  llm-review --help"
echo ""
echo "If the command is not found:"
echo "1. Add ~/.local/bin to your PATH (see instructions above)"
echo "2. Reload your shell: source ~/.bashrc"
echo ""