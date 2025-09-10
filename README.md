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
$ reviewer

# With options
$ reviewer --verbose
$ reviewer --output-file review.md
$ reviewer --include-unchanged  # Include context files
$ reviewer --no-rate-limit      # Disable rate limiting (use with caution)

# Review modes
$ reviewer --ai-generated  # Detect hallucinations, stubs
$ reviewer --prototype     # Deprioritize security issues
$ reviewer --full          # Show all issues, not just critical
$ reviewer --mode critical  # Default: only critical issues

# Session persistence (maintains conversation history)
$ reviewer --session-name feature-auth  # Named session
$ reviewer -s feature-auth              # Continue previous session
$ reviewer --list-sessions              # Show active sessions
$ reviewer --no-session                 # Disable persistence

# Service management
$ reviewer --service status   # Check service health
$ reviewer --service restart  # Restart the service
$ reviewer --service logs     # Tail service logs
$ reviewer --service stop     # Stop the service

# Output formats
$ reviewer --output-format compact    # Minimal output (default)
$ reviewer --output-format human      # Formatted with emojis
$ reviewer --output-format markdown   # Full markdown report

# Configuration
$ reviewer --config .reviewer.yaml    # Use specific config file
$ reviewer --directory /path/to/repo  # Review different directory
$ reviewer --design-doc README.md     # Provide design context

# MCP Server (for Claude Desktop)
$ reviewer-mcp  # Start MCP server
```

### 7.1.1 Session Persistence

The tool supports persistent review sessions to maintain context across multiple reviews:

```bash
# Install and start the service (one-time setup)
$ ./install-service.sh
$ reviewer --service status

# First review creates a new session
$ reviewer --session-name auth-feature
🆕 Starting NEW review session: auth-feature
🤖 Creating fresh Gemini chat instance

# Subsequent reviews continue the conversation
$ reviewer --session-name auth-feature
🔄 CONTINUING review session: auth-feature (iteration 2)
🧠 Using existing Gemini chat with full conversation history
📅 Last reviewed: 5 minutes ago
💬 Conversation history: 42 messages

# List all active sessions
$ reviewer --list-sessions
Active review sessions (3):
  • auth-feature        (iteration 4, last: 5 minutes ago)
  • bug-fix-123         (iteration 2, last: 2 hours ago)
  • refactor-api        (iteration 7, last: 1 day ago)
```

Benefits:
- Maintains full conversation history between reviews
- AI remembers previous issues and context
- Project-scoped sessions prevent cross-contamination
- Runs as macOS service for reliability

### 7.1.2 Rate Limiting

The tool includes built-in rate limiting for Gemini API calls to comply with tier limits:

```bash
# Rate limiting is enabled by default (Tier 1: 150 RPM for Pro, 1000 RPM for Flash)
$ reviewer

# Disable rate limiting (use with caution)
$ reviewer --no-rate-limit

# Configure in .reviewer.yaml
gemini_settings:
  rate_limiting:
    enabled: true    # Enable/disable rate limiting
    tier: tier1      # API tier (currently only tier1 supported)
```

Tier 1 Rate Limits:
- Gemini 2.5 Pro: 150 requests per minute
- Gemini 2.5 Flash: 1,000 requests per minute
- Gemini 2.0 Flash: 2,000 requests per minute

The rate limiter uses a token bucket algorithm to ensure compliance while maximizing throughput.

### 7.2 Output Example

```
🔍 Code Review for Local Changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: Gemini 1.5 Pro
Mode: AI Navigation (Intelligent Exploration)
Changed Files: 3

📊 Building codebase index...
✓ Indexed 245 files
✓ Found 1,847 symbols
✓ Mapped 523 imports

🤖 Gemini exploring codebase...

Navigation Path:
1. src/auth/auth.py (changed) - 2.3K tokens
2. src/services/user_service.py (import) - 1.8K tokens  
3. src/api/endpoints.py (usage) - 3.1K tokens
4. tests/test_auth.py (tests) - 2.5K tokens
5. src/middleware/error_handler.py (exception handling) - 1.2K tokens
6. src/utils/validators.py (related) - 0.9K tokens

📊 Review Results:
─────────────────────────
🔴 Critical Issues: 1
⚠️  Warnings: 2
💡 Suggestions: 4
✨ Commendations: 2

🎯 Key Findings:

1. **Unhandled Exception** (Critical)
   - Your new SecurityException in auth.py
   - Not caught in api/endpoints.py:78
   - Will cause 500 errors in production
   - Fix: Add to error_handler.py middleware

2. **Missing Test Coverage** (Warning)
   - New login() behavior not tested
   - Found by exploring test_auth.py
   - Add test for SecurityException case

3. **Pattern Opportunity** (Suggestion)
   - Similar auth logic in user_service.py:45
   - Could refactor to share validation
   - Would prevent future inconsistencies

📋 Actionable Next Steps:
1. Add SecurityException handler to middleware
2. Update login endpoint error handling
3. Add test case for new exception
4. Consider extracting auth validation
5. Update API documentation

💰 Efficiency Report:
- Files explored: 6 of 245 (2.4%)
- Tokens used: 11,800 (vs ~980K full dump)
- Cost: $0.003 (vs $0.25 full context)
- Time: 8 seconds

🔍 Navigation Insights:
"I found the issue by following the import chain from auth.py 
to the API endpoint, then checking the error handling middleware. 
This targeted approach found issues that might be missed in a 
simple diff review."

Full report: review_2024_01_15.md
```

### 7.3 Comparison: Navigation vs Full Dump

**Scenario**: 300-file project with auth changes

**Full Context Approach**:
- Send all 300 files (1.2M tokens - won't fit!)
- Falls back to heuristics
- Might miss exception handling issue
- Cost: $0.30+

**AI Navigation Approach**:
- Explores only 6 relevant files
- Follows logical code paths
- Finds actual usage problems
- Cost: $0.003

**Benefits Demonstrated**:
1. **Precision**: Only reads what matters
2. **Intelligence**: Follows relationships
3. **Scalability**: Works on any size project
4. **Cost**: 100x cheaper
5. **Speed**: 8s vs 45s+

## 8. Future Enhancements

### 8.1 Phase 1: PR Support (v1.0)
- Add GitHub integration
- Gemini navigates PR files
- Same intelligent exploration
- Remote file fetching via GitHub API

### 8.2 Phase 2: Multi-AI Navigation (v2.0)

**Shared Navigation Architecture**:
```
┌─────────────────────────────────────────────────────┐
│          Shared Codebase Index                       │
│  • File tree, symbols, imports, tests               │
│  • Available to all AI participants                 │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│         Navigation Tool Service                      │
│  • read_file() - shared file cache                 │
│  • find_usages() - consistent results              │
│  • Prevents duplicate reads                        │
└────────────────────┬────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│ Gemini  │    │  GPT-4  │    │ Claude  │
│Navigator│    │Security │    │ Arch    │
└─────────┘    └─────────┘    └─────────┘
```

**Multi-AI Navigation Benefits**:
- Each AI explores based on expertise
- Shared file cache prevents duplication
- Different perspectives, same codebase view
- Collaborative navigation paths

### 8.3 Advanced Navigation Features

**Future Capabilities**:
```python
# Semantic search across codebase
def search_semantic(query: str) -> List[CodeBlock]:
    """Find code by meaning, not just text"""
    
# Architecture analysis
def get_architecture_diagram() -> Diagram:
    """Generate architecture from code"""
    
# Change impact analysis  
def trace_impact(change: Change) -> ImpactGraph:
    """Show full impact of a change"""
    
# Smart test recommendations
def suggest_tests(code: str) -> List[TestCase]:
    """Generate test cases for code"""
```

### 8.4 Navigation Intelligence Evolution

**MVP**: Basic navigation with file/symbol lookup
**v1.0**: Add semantic understanding
**v2.0**: Multi-AI collaborative exploration
**v3.0**: Predictive navigation (anticipate needs)

## 9. Security Considerations

### 9.1 MVP Security
- API key via environment variable
- No code storage or logging
- Local execution only
- Respect .gitignore
- Safe file path validation in navigation

### 9.2 Navigation Security
- Prevent directory traversal attacks
- Sandbox file access to project root
- Validate all file paths before reading
- Rate limit navigation requests
- Timeout long-running explorations

### 9.3 Future Security
- Multiple API key management
- PR access permissions
- Code sanitization
- Audit trails of navigation paths

## 10. Why AI Navigation is the Right Approach

### 10.1 Mimics Human Code Review

**Human Developer Process**:
1. Look at what changed
2. Check where it's used
3. Verify tests exist
4. Follow imports
5. Check error handling

**AI Navigation Process**:
1. ✓ Examines changed files
2. ✓ Finds usages across codebase
3. ✓ Locates and reads tests
4. ✓ Follows import chains
5. ✓ Checks exception handlers

### 10.2 Solves Real Problems

| Problem | Traditional Solution | AI Navigation Solution |
|---------|---------------------|----------------------|
| Token limits | Complex heuristics | Read only what's needed |
| Missing context | Include everything | Follow relationships |
| Large codebases | Can't review | Works at any scale |
| Cost | Expensive | 100x cheaper |
| Speed | Slow | Fast, targeted |

### 10.3 Technical Advantages

1. **Incremental Understanding**: Builds context as needed
2. **Lazy Loading**: Only reads files when necessary
3. **Intelligent Caching**: Reuses file reads across review
4. **Language Agnostic**: Works with any codebase structure
5. **Future Proof**: Same approach scales infinitely

### 10.4 Business Value

- **For Developers**: Better, faster reviews
- **For Teams**: Consistent quality at scale
- **For Organizations**: Massive cost savings
- **For Open Source**: Affordable for any project

## 11. Summary

The MVP revolutionizes code review through AI-driven intelligent navigation:

### Core Innovation
Instead of dumping all code or using rigid rules, we give Gemini:
- **A map** (file tree and symbol index)
- **Navigation tools** (read files on demand)
- **Freedom to explore** intelligently

### Immediate Benefits
- **Works on ANY size codebase** (10 to 10,000+ files)
- **100x cost reduction** ($0.003 vs $0.30+ per review)
- **Better insights** than full-context approaches
- **Faster reviews** (5-10 seconds vs 30-60 seconds)
- **Simple implementation** (no complex selection logic)

### Real Example
```
Traditional: "Here's 500 files, find issues" → Can't fit, fails
Our Approach: "Here's a map, explore as needed" → Reads 6 files, finds critical bug
```

### Why This Works
1. **Mimics Human Behavior**: Developers don't read entire codebases
2. **Follows Real Relationships**: Code connections, not folder proximity  
3. **Scales Infinitely**: Same approach for 10 or 10,000 files
4. **Cost Effective**: Pay only for what's actually reviewed
5. **Intelligent**: AI makes smart navigation decisions

### MVP Deliverables
- Single Gemini conversation with navigation
- Works on local uncommitted changes
- Provides actionable insights
- Costs pennies per review
- Ready for expansion to PRs and multi-AI

This isn't just another code review tool - it's a fundamentally better approach that makes AI code review practical and affordable for everyone.

## 12. Project Structure

```
CodeReviewer/
├── reviewer/                # Core package
│   ├── __init__.py         
│   ├── cli.py              # Command-line interface
│   ├── gemini_client.py    # Gemini API integration with rate limiting
│   ├── claude_client.py    # Claude API integration (future)
│   ├── git_operations.py   # Git diff and change detection
│   ├── codebase_indexer.py # AST-based code analysis
│   ├── navigation_tools.py # AI navigation functions
│   ├── review_formatter.py # Output formatting
│   ├── rate_limiter.py     # Token bucket rate limiting
│   ├── service.py          # FastAPI service for sessions
│   ├── mcp_server.py       # MCP server entry point
│   └── mcp/                # MCP protocol implementation
│       ├── __init__.py
│       ├── server.py       # MCP server implementation
│       ├── protocol.py     # MCP protocol types
│       ├── client.py       # MCP client for service
│       └── tools.py        # MCP tool definitions
│
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures and mocks
│   ├── test_gemini_client_rate_limiting.py # Rate limiter tests
│   ├── test_e2e_session_persistence.py     # Session tests
│   ├── test_e2e_real_gemini.py            # Real API tests
│   ├── test_e2e_mcp_server.py             # MCP tests
│   └── scripts/            # Test scripts and utilities
│
├── docs/                    # Documentation
│   ├── guides/             # User guides
│   ├── design/             # Design documents
│   └── api/                # API documentation
│
├── examples/               # Example configurations
│   ├── demo.py            # Demo script
│   └── sample-config/     # Sample configuration files
│
├── scripts/                # Utility scripts
│   └── install-service.sh # macOS service installer
│
├── setup.py               # Package setup
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── pytest.ini            # Test configuration
├── run_e2e_tests.py      # E2E test runner
├── implementation_status.md # Current implementation status
├── .gitignore           # Git ignore rules
├── .env                 # Environment variables (not in git)
└── README.md            # This file
```

### Key Directories

- **`reviewer/`**: Core package with all review functionality
- **`reviewer/mcp/`**: MCP server implementation for Claude Desktop integration
- **`tests/`**: Comprehensive test suite including E2E tests with real API
- **`docs/`**: Documentation (guides, design docs, API reference)
- **`examples/`**: Demo scripts and configuration examples
- **`scripts/`**: Utility scripts including service installer

### Getting Started

1. Install the package: `pip install -e .`
2. Set your API key: `export GEMINI_API_KEY="your-api-key"`
3. Run a review: `reviewer`
4. For persistent sessions: `./install-service.sh` then `reviewer --session-name my-feature`

### MCP Integration with Claude Desktop

To use with Claude Desktop:

1. Install the reviewer package
2. Add to Claude Desktop config:
```json
{
  "mcpServers": {
    "reviewer": {
      "command": "reviewer-mcp"
    }
  }
}
```
3. Use review tools directly in Claude Desktop

### Configuration

Create a `.reviewer.yaml` file in your project root:

```yaml
review:
  provider: gemini-2.5-pro
  mode: critical  # critical, full, ai-generated, prototype
  
gemini_settings:
  api_key_env: GEMINI_API_KEY
  temperature: 0.7
  rate_limiting:
    enabled: true
    tier: tier1
    
output:
  format: markdown
  show_navigation_path: true
  show_token_usage: true
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

### License

MIT License - see [LICENSE](LICENSE) file for details.
