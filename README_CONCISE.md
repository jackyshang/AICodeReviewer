# CodeReviewer

AI-powered code review tool that uses Google Gemini to analyze uncommitted changes with intelligent navigation and session persistence.

## Features

- 🔍 **Smart Navigation** - Only reads relevant files, not entire codebase
- 💾 **Session Memory** - Maintains context across multiple reviews  
- 🎯 **Review Modes** - Critical issues only, full review, AI code detection, prototype mode
- ⚡ **Cost Efficient** - 80-90% fewer tokens than traditional approaches
- 🔌 **Claude Desktop** - MCP integration available

## Quick Start

```bash
# Install
pip install -e .

# Set API key
export GEMINI_API_KEY="your-api-key"

# Review uncommitted changes
reviewer

# With session (remembers context)
reviewer --session-name feature-x

# Review modes
reviewer --mode critical    # Default: only must-fix issues
reviewer --mode full        # All feedback
reviewer --ai-generated     # Detect AI hallucinations
reviewer --prototype        # Skip security for rapid dev
```

## Installation

### Basic Setup
```bash
git clone https://github.com/yourusername/CodeReviewer.git
cd CodeReviewer
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Session Persistence (Optional)
```bash
# macOS only - enables conversation memory
./install-service.sh
reviewer --service status
```

### Claude Desktop Integration (Optional)
Add to Claude Desktop config:
```json
{
  "mcpServers": {
    "reviewer": {
      "command": "reviewer-mcp"
    }
  }
}
```

## Configuration

Create `.reviewer.yaml` in your project:
```yaml
review:
  provider: gemini-2.5-pro
  mode: critical
  
gemini_settings:
  api_key_env: GEMINI_API_KEY
  rate_limiting:
    enabled: true
    tier: tier1
```

## How It Works

Instead of sending your entire codebase (expensive and often hits token limits), CodeReviewer:

1. **Builds an index** of your code structure (classes, functions, imports)
2. **Starts with changed files** from `git diff`
3. **Intelligently explores** related code by following imports and usages
4. **Reviews with context** while using 10x fewer tokens

Example: In a 500-file project, reviewing a single file change might only read 5-10 relevant files instead of all 500.

## CLI Options

```bash
reviewer [OPTIONS]

Options:
  --session-name TEXT       Enable session persistence
  --mode [critical|full|ai-generated|prototype]
  --output-format [compact|human|markdown]
  --verbose                 Show detailed progress
  --no-rate-limit          Disable API rate limiting
  --service [status|logs|restart|stop]
  --help                   Show all options
```

## Requirements

- Python 3.8+
- Git repository with uncommitted changes
- Gemini API key (free tier works)

## License

MIT - See [LICENSE](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Documentation

- [Architecture Overview](docs/architecture.md) - How the AI navigation works
- [API Reference](docs/api.md) - Detailed API documentation
- [Development Guide](docs/development.md) - For contributors