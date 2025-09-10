# MCP Tool Documentation for LLM-Review

This document provides comprehensive documentation for the MCP (Model Context Protocol) tools exposed by the LLM-Review service.

## Overview

The LLM-Review MCP server exposes 5 tools that enable AI assistants to perform code reviews and manage review sessions. All tools follow standard MCP protocol specifications with well-defined JSON schemas.

## Tool Schemas

### 1. review_changes

**Purpose**: Review uncommitted git changes with AI-powered analysis.

**Schema Validation**:
- ✅ All parameters have detailed descriptions
- ✅ Required fields are marked with [REQUIRED]
- ✅ Mutually exclusive parameters (session_name/no_session) are documented
- ✅ Enum values have detailed explanations
- ✅ Examples provided for complex fields

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `directory` | string | No | "." | Path to git repository. Can be absolute or relative. |
| `story` | string | No | - | Story/purpose context. Can be a file path or literal text. |
| `mode` | enum | No | "critical" | Review mode (critical/full/ai-generated/prototype) |
| `session_name` | string | No | - | Named session for continuous review. Pattern: `^[a-zA-Z0-9-_]+$` |
| `no_session` | boolean | No | false | Disable session persistence |
| `output_format` | enum | No | "compact" | Output format (compact/human/markdown) |
| `include_unchanged` | boolean | No | false | Include unchanged files for context |
| `design_doc` | string | No | - | Path to design document |
| `fast` | boolean | No | false | Use Gemini 2.5 Flash for faster analysis |
| `verbose` | boolean | No | false | Show step-by-step progress |
| `debug` | boolean | No | false | Show raw API requests/responses |
| `config_path` | string | No | - | Path to .llm-review.yaml config |
| `save_to_file` | string | No | - | Save output to markdown file |

**Usage Examples**:

```json
// Basic review
{
  "directory": ".",
  "mode": "critical"
}

// Session-based review with context
{
  "directory": "/Users/name/project",
  "session_name": "feature-auth",
  "story": "Implement user authentication",
  "output_format": "human"
}

// Fast AI-generated code check
{
  "mode": "ai-generated",
  "fast": true,
  "save_to_file": "review-results.md"
}
```

### 2. list_review_sessions

**Purpose**: List all active code review sessions with filtering options.

**Schema Validation**:
- ✅ All parameters have descriptions
- ✅ Numeric constraints (minimum/maximum) are defined
- ✅ Default values are specified

**Parameters**:

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `project_filter` | string | No | - | - | Filter by project path (partial match) |
| `limit` | integer | No | 20 | min: 1, max: 100 | Maximum sessions to return |
| `sort_by` | enum | No | "last_reviewed" | - | Sort field (created/last_reviewed/name/iterations) |
| `format` | enum | No | "list" | - | Output format (list/detailed/json) |

**Usage Examples**:

```json
// List recent sessions
{
  "limit": 10,
  "sort_by": "last_reviewed"
}

// Find sessions for specific project
{
  "project_filter": "/Users/name/auth-service",
  "format": "detailed"
}
```

### 3. manage_review_service

**Purpose**: Control the background review service that maintains session state.

**Schema Validation**:
- ✅ Required parameter marked with [REQUIRED]
- ✅ Enum values have detailed explanations
- ✅ Conditional parameters are documented

**Parameters**:

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `action` | enum | **Yes** | - | - | Action to perform (status/start/stop/restart/logs/errors) |
| `tail_lines` | integer | No | 20 | min: 1, max: 1000 | Log lines to display (only for logs/errors actions) |

**Usage Examples**:

```json
// Check service status
{
  "action": "status"
}

// View recent error logs
{
  "action": "errors",
  "tail_lines": 50
}
```

### 4. get_session_details

**Purpose**: Retrieve metadata about a review session.

**Schema Validation**:
- ✅ Required fields marked with [REQUIRED]
- ✅ Pattern validation for session_name
- ✅ Clear scope documentation

**Parameters**:

| Parameter | Type | Required | Pattern | Description |
|-----------|------|----------|---------|-------------|
| `session_name` | string | **Yes** | `^[a-zA-Z0-9-_]+$` | Name of the session |
| `project_root` | string | **Yes** | - | Absolute path to project root |
| `include_history` | boolean | No | - | Include conversation history (coming soon) |

**Usage Examples**:

```json
// Get session metadata
{
  "session_name": "feature-auth",
  "project_root": "/Users/name/project"
}
```

### 5. clear_session

**Purpose**: Delete a review session and all its conversation history.

**Schema Validation**:
- ✅ Required fields marked with [REQUIRED]
- ✅ Safety confirmation parameter
- ✅ Irreversible action warning in description

**Parameters**:

| Parameter | Type | Required | Default | Pattern | Description |
|-----------|------|----------|---------|---------|-------------|
| `session_name` | string | **Yes** | - | `^[a-zA-Z0-9-_]+$` | Session to delete |
| `project_root` | string | **Yes** | - | - | Absolute path to project root |
| `confirm` | boolean | No | true | - | Safety confirmation |

**Usage Examples**:

```json
// Delete a session
{
  "session_name": "old-feature",
  "project_root": "/Users/name/project",
  "confirm": true
}
```

## Key Design Decisions

### 1. Session Scoping
Sessions are scoped per project (using project_root) to prevent cross-contamination between different codebases.

### 2. Parameter Validation
- Session names use strict pattern validation to ensure filesystem compatibility
- Required parameters are clearly marked with [REQUIRED] in descriptions
- Mutually exclusive parameters are documented in both directions

### 3. Output Formats
Multiple output formats support different use cases:
- `compact`: Optimized for AI processing (minimal tokens)
- `human`: User-friendly with emojis and sections
- `markdown`: Full documentation format

### 4. Service Architecture
The background service auto-starts when needed, maintaining session state across reviews.

## Common Usage Patterns

### 1. Continuous Review Workflow
```json
// First review - creates session
{
  "directory": ".",
  "session_name": "feature-x",
  "story": "Implement feature X"
}

// Subsequent reviews - uses context
{
  "directory": ".",
  "session_name": "feature-x"
}
```

### 2. Quick One-Shot Review
```json
{
  "directory": ".",
  "no_session": true,
  "fast": true,
  "mode": "critical"
}
```

### 3. AI-Generated Code Validation
```json
{
  "mode": "ai-generated",
  "include_unchanged": true,
  "verbose": true,
  "save_to_file": "ai-review.md"
}
```

## Error Handling

All tools return structured error responses:
```json
{
  "error": "Error message",
  "details": "Additional context if available"
}
```

Common errors:
- Invalid directory path
- Service not running (for session operations)
- Invalid session name pattern
- Mutually exclusive parameters used together

## Best Practices

1. **Use Sessions for Related Work**: Create named sessions for feature branches or related changes
2. **Choose Appropriate Mode**: Use "critical" for production code, "prototype" for rapid development
3. **Save Important Reviews**: Use `save_to_file` for documentation or compliance
4. **Monitor Service Health**: Periodically check service status and logs
5. **Clean Up Old Sessions**: Delete sessions when features are complete

## Schema Compliance

All schemas comply with:
- JSON Schema Draft-07 specification
- MCP protocol requirements
- Consistent parameter naming conventions
- Comprehensive documentation standards