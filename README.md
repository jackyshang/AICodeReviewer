# CodeReviewer

AI-powered code review tool using Google Gemini for intelligent, context-aware analysis of uncommitted changes.

## Quick Start

```bash
# Install
git clone https://github.com/jackyshang/AICodeReviewer.git
cd AICodeReviewer
pip install -e .

# Set API key
export GEMINI_API_KEY="your-api-key-here"

# Run review
reviewer
```

## Features

- **Intelligent Navigation** - Only reads relevant files by following imports and dependencies
- **Session Persistence** - Maintains conversation history across multiple reviews
- **Multiple Review Modes** - Critical-only, full review, AI-generated detection, prototype mode
- **Rate Limiting** - Built-in compliance with API tier limits
- **MCP Integration** - Works with Claude Desktop
- **Cost Efficient** - Uses 80-90% fewer tokens than traditional approaches

## How It Works

Instead of sending your entire codebase to the AI (expensive and often exceeds token limits), CodeReviewer uses intelligent navigation:

1. **Builds an index** of your code structure (classes, functions, imports)
2. **Starts with changed files** from `git diff`
3. **Follows dependencies** by exploring imports and usages
4. **Reviews with context** using only relevant files

Example: In a 500-file project, reviewing one file change typically reads only 5-10 relevant files.


## Configuration

Create `.reviewer.yaml` in your project root:

```yaml
review:
  provider: gemini-2.5-pro
  mode: critical  # critical, full, ai-generated, prototype
  
gemini_settings:
  api_key_env: GEMINI_API_KEY
  rate_limiting:
    enabled: true
    tier: tier1  # Free tier limits
    
output:
  format: markdown
  show_navigation_path: true
```


## CLI Usage

```bash
# Basic review
reviewer

# Review modes
reviewer --mode critical       # Only must-fix issues (default)
reviewer --mode full           # All feedback
reviewer --ai-generated        # Detect AI hallucinations
reviewer --prototype           # Skip security for rapid prototyping

# Session persistence  
reviewer --session-name feature-x    # Named session with memory
reviewer --list-sessions              # Show active sessions
reviewer --no-session                 # One-time review

# Output options
reviewer --verbose                    # Show detailed progress
reviewer --output-format markdown     # Full markdown report
reviewer --output-file review.md      # Save to file

# Service management (for persistent sessions)
./install-service.sh                  # One-time setup
reviewer --service status             # Check service
reviewer --service logs               # View logs
```

### Session Persistence

Sessions maintain conversation history across reviews:

```bash
# First review
reviewer --session-name auth-feature
# AI analyzes and remembers issues

# Later review (same session)
reviewer --session-name auth-feature  
# AI recalls previous context and feedback
```

### Rate Limiting

Built-in rate limiting for API compliance (Tier 1):
- Gemini 2.5 Pro: 150 requests/minute
- Gemini 2.5 Flash: 1,000 requests/minute

Disable with `--no-rate-limit` if needed.


## MCP Integration (Claude Desktop)

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "reviewer": {
      "command": "reviewer-mcp"
    }
  }
}
```

Then use review tools directly in Claude Desktop conversations.

## Requirements

- Python 3.8+
- Git repository with uncommitted changes  
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.
