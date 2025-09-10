#!/bin/bash
# Wrapper script to run llm-review from anywhere

# Get the actual installation directory (follow symlinks)
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || readlink "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
INSTALL_DIR="$(dirname "$SCRIPT_PATH")"

# Activate the virtual environment and run llm-review
source "$INSTALL_DIR/venv/bin/activate" && llm-review "$@"