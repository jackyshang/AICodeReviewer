# CodeReviewer - AI-Powered Code Review Tool

**Version**: 0.1.0  
**Platform**: macOS/Linux/Windows Terminal Application  
**Language**: Python 3.8+  
**Current Scope**: Local uncommitted changes & GitHub PRs  
**Supported Providers**: Google Gemini (2.5 Pro/Flash, 2.0 Flash), Claude (via MCP)

## Quick Installation

```bash
# Clone and install
git clone https://github.com/yourusername/CodeReviewer.git
cd CodeReviewer
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .

# Set API key
export GEMINI_API_KEY="your-api-key-here"
# Or create a .env file with: GEMINI_API_KEY=your-api-key-here

# Run review
reviewer

# For MCP integration with Claude Desktop
reviewer-mcp
```

## 1. Executive Summary

CodeReviewer is an AI-powered command-line tool that performs intelligent code reviews on local uncommitted changes and GitHub PRs. It uses advanced AI models (primarily Google Gemini) to provide categorized feedback with severity levels, session persistence for iterative development, and integrates with Claude Desktop via MCP (Model Context Protocol).

### Key Features
- 🔍 **Intelligent Navigation**: AI-driven code exploration that follows imports and dependencies
- 💾 **Session Persistence**: Maintains conversation history across multiple reviews
- 🎯 **Multiple Review Modes**: Critical-only, full review, AI-generated code detection, prototype mode
- 🚀 **Rate Limiting**: Built-in rate limiting for API tier compliance
- 🔌 **MCP Integration**: Works seamlessly with Claude Desktop
- ⚡ **Fast & Efficient**: Token-optimized navigation reduces costs by 80-90%

### 1.1 Design Principles
- **MVP Simplicity**: Gemini handles everything in one conversation
- **Context Preservation**: Single conversation maintains full context
- **Always Actionable**: Every review categorizes issues by severity
- **Clear Priorities**: Critical issues vs. suggestions
- **Future Ready**: Architecture allows expansion to multi-AI
- **Test Driven**: TDD/BDD methodology

### 1.2 Current Status (v0.1.0)
- ✅ **Implemented**: Local changes review with Gemini
- ✅ **Implemented**: Session persistence with conversation history
- ✅ **Implemented**: MCP server for Claude Desktop integration
- ✅ **Implemented**: Rate limiting for API tier compliance
- ✅ **Implemented**: Multiple review modes (critical, full, ai-generated, prototype)
- ✅ **Implemented**: Service management for background operation
- 🚧 **In Progress**: GitHub PR support
- 📋 **Planned**: Multi-AI provider support

## 2. MVP Architecture

### 2.1 MVP Approach: AI-Driven Navigation
- **Single AI**: Gemini navigates and reviews intelligently
- **On-Demand File Access**: AI requests files as needed
- **Smart Navigation**: Provides codebase map and indices
- **Tool-Based Interaction**: Gemini uses tools to explore code
- **Efficient Token Usage**: Only loads relevant files

### 2.2 AI Navigation Strategy

```
┌─────────────────────────────────────────────────────┐
│          Gemini with Navigation Tools                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Initial Context Provided:                          │
│  • Project file tree structure                      │
│  • Class/Interface → File mapping                   │
│  • Method → File mapping                            │
│  • Changed files list                               │
│                                                     │
│  Available Tools for Gemini:                        │
│  • read_file(path) → Returns file content          │
│  • search_symbol(name) → Finds declarations        │
│  • find_usages(symbol) → Finds where used          │
│  • get_imports(file) → Lists file dependencies     │
│                                                     │
│  Gemini's Review Process:                           │
│  1. Examines changed files                          │
│  2. Requests related files as needed               │
│  3. Follows import chains                          │
│  4. Checks test coverage                           │
│  5. Provides comprehensive review                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2.3 Why AI Navigation is Superior

**Traditional Approach** (send all files):
- Wastes tokens on irrelevant files
- Can hit token limits quickly
- No intelligent exploration
- Slower processing

**AI Navigation Approach** (MVP):
- Only reads what's necessary
- Follows logical code paths
- Mimics human code review
- Scales to any project size
- More cost effective

### 2.4 Example Navigation Flow

```
Gemini: "I see auth.py was modified. Let me check its imports."
→ read_file("src/auth/auth.py")

Gemini: "This imports UserService. Let me examine that."
→ read_file("src/services/user_service.py")

Gemini: "The auth change affects login(). Let me find its usages."
→ find_usages("login")

Gemini: "Found 3 callers. Let me check if they handle the new exception."
→ read_file("src/api/login_endpoint.py")
→ read_file("src/cli/auth_commands.py")
→ read_file("tests/test_auth.py")

Gemini: "I should verify the test coverage for this change."
→ read_file("tests/test_auth.py")

Result: Targeted review with only 6 files read instead of 200+
```

## 3. MVP Implementation

### 3.1 Core Workflow

```
$ llm-review

1. Detect Changes
   └─> git diff --name-only
   
2. Build Codebase Index
   └─> Generate file tree structure
   └─> Create symbol → file mappings
   └─> Index class/interface/method locations
   
3. Start Gemini Conversation with Tools
   └─> Provide codebase map
   └─> Enable navigation functions
   
4. AI-Driven Review Process
   └─> Gemini examines changed files
   └─> Navigates to related code as needed
   └─> Builds understanding incrementally
   └─> Requests only relevant files
   
5. Generate Comprehensive Review
   └─> Based on targeted exploration
   └─> Includes cross-file impacts
   └─> Suggests improvements
   
6. Format Output
   └─> Display results with navigation path
```

### 3.2 Navigation Tools for Gemini

**Tool Suite**:
```python
# Tools available to Gemini during review

def read_file(filepath: str) -> str:
    """Read and return file content"""
    
def search_symbol(symbol_name: str) -> List[Location]:
    """Find where a class/function/variable is defined"""
    
def find_usages(symbol_name: str) -> List[Location]:
    """Find all places where symbol is used"""
    
def get_imports(filepath: str) -> List[str]:
    """Get all imports from a file"""
    
def get_file_tree() -> str:
    """Get project structure as tree"""
    
def search_text(pattern: str) -> List[Match]:
    """Search for text pattern across codebase"""
```

### 3.3 Example: AI Navigation in Action

**Initial Context Provided**:
```
Project Structure:
├── src/
│   ├── auth/
│   │   ├── auth.py (CHANGED)
│   │   └── tokens.py
│   ├── services/
│   │   ├── user_service.py
│   │   └── email_service.py
│   └── api/
│       └── endpoints.py
└── tests/
    └── test_auth.py

Symbol Index:
- class AuthManager → src/auth/auth.py:15
- class UserService → src/services/user_service.py:8  
- def login() → src/auth/auth.py:45
- def verify_token() → src/auth/tokens.py:12
```

**Gemini's Navigation**:
```
[Turn 1] "I'll start by examining the changed file"
> read_file("src/auth/auth.py")

[Turn 2] "The login method now throws a new exception. Let me check who calls it"
> find_usages("login")
Returns: ["src/api/endpoints.py:78", "tests/test_auth.py:23"]

[Turn 3] "Let me verify the API endpoint handles this new exception"
> read_file("src/api/endpoints.py")

[Turn 4] "The endpoint doesn't handle the new SecurityException. Let me check if there's a global handler"
> search_symbol("SecurityException")
> read_file("src/exceptions.py")

[Turn 5] "Now let me ensure tests cover this new behavior"
> read_file("tests/test_auth.py")
```

### 3.4 Benefits of AI Navigation

1. **Efficient Token Usage**: Only reads ~5-10 files instead of 100+
2. **Intelligent Exploration**: Follows logical code relationships
3. **Scalable**: Works on any size codebase
4. **Better Insights**: Focuses on actually related code
5. **Cost Effective**: 10x fewer tokens than full dump
6. **Human-Like Review**: Mimics how developers navigate code

### 3.5 Codebase Indexing Process

**What Gets Indexed** (Fast, <2 seconds):
```
1. File Tree Structure
   project/
   ├── src/
   │   ├── auth/ (3 files)
   │   ├── services/ (8 files)
   │   └── api/ (5 files)
   └── tests/ (12 files)

2. Symbol → Location Mapping
   {
     "classes": {
       "AuthManager": "src/auth/auth.py:15",
       "UserService": "src/services/user.py:8",
       "APIRouter": "src/api/router.py:22"
     },
     "functions": {
       "login": ["src/auth/auth.py:45", "src/api/endpoints.py:78"],
       "validate_token": "src/auth/tokens.py:23"
     }
   }

3. Import Dependencies
   src/api/endpoints.py → imports from:
     - src/auth/auth.py
     - src/services/user.py
     - src/utils/validators.py

4. Test → Source Mapping
   tests/test_auth.py → tests → src/auth/auth.py
   tests/test_user.py → tests → src/services/user.py
```

**How Gemini Uses the Index**:
1. Starts with changed files from index
2. Uses symbol map to find definitions
3. Follows import graph for dependencies
4. Locates tests via test mapping
5. Explores only what's needed

**Indexing Technologies**:
- AST parsing for accurate symbol extraction
- Incremental updates (only reindex changed files)
- Language-specific parsers (Python, JS, Java, etc.)
- Cached between runs for speed

### 3.6 Why This Beats Simple Rules

**Rule-Based Approach**: "Always include files in same directory"
- Includes irrelevant files
- Misses important dependencies
- Wastes tokens

**AI Navigation**: "Let me follow the actual code flow"
- Traces real dependencies
- Understands architecture
- Optimal token usage

## 4. Configuration

### 4.1 MVP Configuration

```yaml
# .llm-review.yaml
review:
  # MVP uses Gemini for everything
  provider: gemini-1.5-pro
  mode: ai_navigation  # Let AI explore codebase
  
  navigation:
    # What indices to build
    build_indices:
      - file_tree: true
      - symbol_map: true  # class/function → file
      - import_graph: true
      - test_mapping: true  # test → source file
    
    # Navigation boundaries
    exploration_limits:
      max_files_per_review: 50  # Prevent runaway
      max_depth: 10  # Import chain depth
      timeout_seconds: 300
    
    # File filters
    include_patterns:
      - "**/*.py"
      - "**/*.js" 
      - "**/*.java"
      - "**/*.go"
      - "**/*.ts"
      
    exclude_patterns:
      - "**/node_modules/**"
      - "**/__pycache__/**"
      - "**/venv/**"
      - "**/.git/**"
      - "**/dist/**"
      
  gemini_settings:
    api_key_env: GEMINI_API_KEY
    temperature: 0.7
    tools_enabled: true  # Enable function calling
    rate_limiting:
      enabled: true  # Enable rate limiting (default: true)
      tier: tier1    # API tier (tier1 = free tier)
    
  output:
    format: markdown
    show_navigation_path: true  # Show which files AI explored
    show_token_usage: true
    show_cost: true
```

### 4.2 Future Configuration (Post-MVP)

```yaml
# Future: After MVP
review:
  providers:
    context: gemini      # Could stay Gemini
    reviewers:          # Could add others
      - gpt-4
      - claude
    next_steps: gemini  # Could be collaborative
```

## 5. Technical Specifications

### 5.1 Codebase Indexing

**Pre-Review Index Generation**:
```python
CodebaseIndex:
├── FileTree
│   └── Hierarchical structure for navigation
├── SymbolIndex  
│   ├── Classes → File:Line mapping
│   ├── Functions → File:Line mapping
│   └── Methods → File:Line mapping
├── ImportGraph
│   └── File → Dependencies mapping
└── TestMapping
    └── Test file → Source file relationships

Example Index:
{
  "symbols": {
    "AuthManager": "src/auth/auth.py:15",
    "UserService": "src/services/user.py:8",
    "login": "src/auth/auth.py:45",
    "validate_token": "src/auth/tokens.py:23"
  },
  "imports": {
    "src/auth/auth.py": ["src/services/user.py", "src/utils/crypto.py"],
    "src/api/endpoints.py": ["src/auth/auth.py", "src/services/user.py"]
  }
}
```

### 5.2 Token Economics with Navigation

**Efficiency Comparison**:

| Approach | Files Read | Tokens Used | Cost | Quality |
|----------|------------|-------------|------|---------|
| Full Dump (small) | 50 | 200K | $0.05 | Good |
| Full Dump (medium) | 200 | 800K | $0.20 | Good |
| Full Dump (large) | 500+ | >1M | N/A | Can't do |
| **AI Navigation** | 5-15 | 50K | $0.01 | Excellent |

**Cost Benefits**:
- 80-90% token reduction
- Works on any size codebase
- Better focused insights
- Faster response times

### 5.3 Domain Model

```
Review Session (MVP)
├── Codebase Index
│   ├── File Tree
│   ├── Symbol Map
│   ├── Import Graph
│   └── Test Mapping
├── Navigation Tools
│   ├── read_file()
│   ├── search_symbol()
│   ├── find_usages()
│   └── get_imports()
├── Gemini Conversation
│   ├── Initial Context (index + changes)
│   ├── Navigation Decisions
│   ├── File Explorations
│   └── Review Generation
└── Output
    ├── Issues Found
    ├── Navigation Path
    ├── Recommendations
    └── Token Usage Report
```

### 5.4 Implementation Approach

**Index Generation** (Fast, <2 seconds):
```python
# Use AST parsing for accuracy
# Cache results between runs
# Incremental updates for speed

def build_symbol_index(project_root):
    """Build symbol → file:line mapping"""
    index = {}
    for file in get_source_files(project_root):
        ast_tree = parse_file(file)
        for node in walk_ast(ast_tree):
            if is_definition(node):
                index[node.name] = f"{file}:{node.line}"
    return index
```

**Tool Implementation**:
```python
# Gemini calls these during review
def read_file(filepath: str) -> str:
    """Read file content with safety checks"""
    if not is_safe_path(filepath):
        return "Error: Invalid path"
    return read_text_file(filepath)

def find_usages(symbol: str) -> List[str]:
    """Find where symbol is used"""
    # Use grep/ripgrep for speed
    results = search_codebase(symbol)
    return format_results(results)
```

## 6. Testing Strategy

### 6.1 TDD Approach

1. **Unit Tests**
   - Git operations
   - Prompt construction
   - Response parsing
   - Output formatting

2. **Integration Tests**
   - Full conversation flow
   - Error scenarios
   - Large diff handling

3. **BDD Scenarios**
   ```gherkin
   Feature: AI-Driven Code Navigation Review
     
     Scenario: Review with intelligent navigation
       Given I have uncommitted changes in auth.py
       And the project has 250 files
       When I run llm-review
       Then Gemini should build a codebase index
       And Gemini should start by reading auth.py
       And Gemini should navigate to related files
       And Gemini should read fewer than 20 files total
       And the review should find cross-file impacts
       
     Scenario: Large project navigation
       Given I have a project with 5000 files
       When I run llm-review
       Then indexing should complete in under 5 seconds
       And Gemini should navigate efficiently
       And token usage should be under 50K
       
     Scenario: Navigation with missing dependencies
       Given I have changes that import a missing module
       When Gemini tries to navigate to the import
       Then it should report the missing dependency
       And continue reviewing other aspects
   ```

## 7. CLI Interface

### 7.1 Available Commands

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
