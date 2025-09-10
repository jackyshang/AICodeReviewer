# Session Persistence for LLM Review

## Overview

The session persistence feature allows `llm-review` to maintain conversation history across multiple review sessions. This means the AI remembers previous reviews, what issues were found, and what has been fixed.

## How It Works

1. **Service Architecture**: A lightweight FastAPI service runs in the background, maintaining Gemini chat objects in memory
2. **Named Sessions**: Each review session has a name (e.g., "auth-feature") that identifies it
3. **Automatic Continuation**: When you use the same session name, the AI continues the conversation with full context

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install the Service (macOS)

```bash
./install-service.sh
```

This will:
- Create a macOS LaunchAgent that starts automatically
- Configure the service to run on port 8765
- Start the service immediately

### 3. Verify Installation

```bash
./llm-review-service-ctl status
```

## Usage

### Basic Session Usage

```bash
# First review - creates new session
llm-review --session-name "auth-feature"
> 🆕 Starting NEW review session: auth-feature
> Found 3 critical issues...

# Later review - continues same session
llm-review --session-name "auth-feature"
> 🔄 CONTINUING review session: auth-feature (iteration 2)
> I see you've fixed 2 of the 3 issues from our last review...
```

### List Active Sessions

```bash
llm-review --list-sessions
> Active review sessions (3):
>   • auth-feature      (iteration 2, last: 10 minutes ago)
>   • payment-api       (iteration 1, last: 2 hours ago)
>   • main              (iteration 5, last: yesterday)
```

### Standard Mode (No Session)

```bash
# Works exactly as before - no persistence
llm-review
```

## Service Management

### Control Commands

```bash
# Check status
./llm-review-service-ctl status

# View logs
./llm-review-service-ctl logs

# Restart service (e.g., after code changes)
./llm-review-service-ctl restart

# Stop service
./llm-review-service-ctl stop

# Start service
./llm-review-service-ctl start

# List sessions
./llm-review-service-ctl sessions
```

### Manual Service Operation

If you prefer not to install as a system service:

```bash
# Run service manually
python -m llm_review.service

# In another terminal
llm-review --session-name "my-feature"
```

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Your Gemini API key (required)
- `LLM_REVIEW_SERVICE_URL`: Service URL (default: http://localhost:8765)
- `LLM_REVIEW_PORT`: Service port (default: 8765)

### Service Behavior

- Sessions are kept in memory while service runs
- Service auto-starts on login (if installed)
- Restarts automatically if it crashes
- Logs to `/tmp/llm-review.log` and `/tmp/llm-review.error.log`

## How Sessions Improve Reviews

### Example Workflow

**Day 1 - Initial Review:**
```bash
$ llm-review -s "user-auth"
> 🆕 Starting NEW review session: user-auth
> 
> Found 3 critical issues:
> 1. Missing test coverage for login()
> 2. Hardcoded API key in config.py
> 3. SQL injection vulnerability
```

**Day 2 - After Fixes:**
```bash
$ llm-review -s "user-auth"
> 🔄 CONTINUING review session: user-auth (iteration 2)
> 📅 Last reviewed: yesterday
> 
> Checking your changes since our last review...
> ✅ Excellent! You've fixed the test coverage for login()
> ✅ Good job moving the API key to environment variables
> ⚠️  The SQL injection issue in user.py line 87 is still present
> 🆕 New issue: Missing error handling in logout()
```

### Benefits

1. **Context Preservation**: AI remembers entire conversation history
2. **Progress Tracking**: See what's been fixed vs. what's new
3. **Efficient Reviews**: AI focuses on changes since last review
4. **Natural Dialogue**: Ask follow-up questions naturally

## Technical Details

### What's Stored in Memory

Each session maintains:
- Complete Gemini chat object with full message history
- Review iteration count
- Timestamps of creation and last use
- Navigation history and token usage

### Memory Management

- Sessions remain in memory while service runs
- Restarting service clears all sessions
- Typical session: 50-200KB initially, grows with usage
- 10 active sessions ≈ 50-200MB total memory

### API Endpoints

The service exposes:
- `GET /health` - Health check and basic stats
- `POST /review` - Perform review with session
- `GET /sessions` - List all active sessions
- `GET /sessions/{name}` - Get session details
- `DELETE /sessions/{name}` - Clear specific session

## Troubleshooting

### Service Won't Start

```bash
# Check logs
tail -f /tmp/llm-review.error.log

# Verify port is available
lsof -i :8765

# Check service status
launchctl list | grep llm-review
```

### Session Not Persisting

1. Ensure service is running: `./llm-review-service-ctl status`
2. Check session name is consistent
3. Verify no typos in session name

### High Memory Usage

```bash
# Check active sessions
./llm-review-service-ctl sessions

# Restart to clear all sessions
./llm-review-service-ctl restart
```

## Uninstall

To remove the service:

```bash
./llm-review-service-ctl uninstall
```

This removes the LaunchAgent but preserves your code.

## Future Enhancements

- Persistent storage to disk (survive restarts)
- Session export/import for team sharing
- Web UI for session management
- Automatic session cleanup policies
- Multi-user session sharing