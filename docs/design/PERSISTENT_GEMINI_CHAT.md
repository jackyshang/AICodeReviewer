# Persistent Gemini Chat Sessions Design

## Overview
Enable `llm-review` to maintain a single Gemini chat session across multiple review iterations, preserving the full conversation context and the AI's understanding of the codebase.

## Current Architecture
Currently, each `llm-review` run:
1. Creates a new chat session: `self.client.chats.create()`
2. Sends initial context
3. Processes navigation/review
4. Discards the chat session

## Proposed Architecture

### Approach 1: Serialize Chat History (Recommended)
Since the Gemini SDK doesn't directly support session persistence, we can:
1. Save the chat history (messages exchanged)
2. Recreate the chat with the full history on next run
3. Continue the conversation from where we left off

```python
# Simplified example
class PersistentGeminiClient(GeminiClient):
    def save_chat_session(self, session_name: str):
        """Save current chat messages to disk."""
        chat_data = {
            'model': self.model_name,
            'messages': self.chat.history,  # All messages exchanged
            'navigation_tools': self.navigation_tools.get_state(),
            'timestamp': datetime.now().isoformat()
        }
        # Save to .llm-review/chats/{session_name}.json
        
    def load_chat_session(self, session_name: str):
        """Load and restore a previous chat session."""
        # Load chat data
        # Create new chat with history
        self.chat = self.client.chats.create(
            model=self.model_name,
            history=chat_data['messages']
        )
```

### Approach 2: Conversation Summary (Fallback)
If full history is too large:
1. Summarize the conversation after each iteration
2. Include summary in the next iteration's context
3. Less ideal but more token-efficient

## Implementation Plan

### 1. Chat Session Storage

```python
@dataclass
class ChatSession:
    """Represents a persistent Gemini chat session."""
    session_id: str
    session_name: str
    model_name: str
    created_at: str
    last_updated: str
    messages: List[Dict[str, Any]]  # Chat history
    navigation_state: Dict[str, Any]  # Indexed files, symbols, etc.
    review_iterations: List[str]  # Review summaries
    total_tokens_used: int
```

### 2. CLI Interface

```bash
# First review - creates new chat session
llm-review --chat-session "auth-feature"

# Continue the conversation
llm-review --chat-session "auth-feature"
# AI: "I see we're continuing our review from iteration 2. 
#      Last time, you had 3 critical issues. Let me check what's changed..."

# List chat sessions
llm-review --list-chats

# Show chat history
llm-review --show-chat "auth-feature"

# Export chat for sharing
llm-review --export-chat "auth-feature" > auth-review.json
```

### 3. Enhanced Context Flow

**First iteration:**
```
User: Review my changes
AI: I found 3 issues: [stores in memory]
1. Missing tests for auth.py
2. Hardcoded secret in config.py
3. SQL injection in user.py
```

**Second iteration (same chat):**
```
User: Review my changes
AI: I see you've made changes since our last review. Let me check:
- ✅ You added tests for auth.py - good!
- ⚠️  The hardcoded secret in config.py is still there
- ✅ SQL injection fixed with parameterized queries
- 🆕 I notice a new file api.py - let me review it...
```

### 4. Benefits of Persistent Chat

1. **Natural Continuity**: AI remembers the entire conversation
2. **Contextual Understanding**: AI knows what it already reviewed
3. **Learning Effect**: AI understands your fix patterns
4. **Efficient Navigation**: AI remembers which files it explored
5. **Conversation Flow**: More natural back-and-forth dialogue

### 5. Technical Considerations

#### Message Storage Format
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "role": "user",
      "parts": [{"text": "Review my changes"}],
      "timestamp": "2024-01-06T10:00:00Z"
    },
    {
      "role": "model", 
      "parts": [{"text": "I found..."}],
      "timestamp": "2024-01-06T10:00:30Z"
    },
    {
      "role": "function",
      "parts": [{"function_call": {...}}]
    }
  ]
}
```

#### Storage Optimization
- Compress message history with gzip
- Implement size limits (e.g., last 50 messages)
- Option to summarize old messages
- Prune navigation function calls (keep results only)

#### Session Management
```python
class ChatSessionManager:
    def __init__(self, project_root: Path):
        self.sessions_dir = project_root / ".llm-review" / "chats"
        
    def create_session(self, name: str, gemini_client: GeminiClient):
        """Create new chat session."""
        
    def continue_session(self, name: str, gemini_client: GeminiClient):
        """Continue existing chat session."""
        # Load history
        # Create chat with history
        # Add continuation message
        
    def auto_session_name(self) -> str:
        """Generate session name from git branch."""
        branch = GitOperations().get_current_branch()
        return f"branch-{branch}"
```

### 6. Example Implementation

```python
# In gemini_client.py
def continue_chat_session(self, session_data: Dict[str, Any]):
    """Continue a previous chat session."""
    # Recreate chat with history
    self.chat = self.client.chats.create(
        model=self.model_name,
        config=types.GenerateContentConfig(
            tools=[self.tool],
            temperature=0.7,
            top_p=0.95,
        ),
        history=session_data['messages']
    )
    
    # Send continuation message
    continuation_prompt = f"""
    We're continuing our code review session from {session_data['last_updated']}.
    In our last conversation, we reviewed {len(session_data['review_iterations'])} iterations.
    
    Please check what has changed since then and provide an updated review.
    """
    
    response = self.chat.send_message(continuation_prompt)
    return response
```

### 7. Integration with Existing Code

Modify `cli.py`:
```python
@click.option("--chat-session", "-s", help="Named chat session to continue")
@click.option("--auto-session", is_flag=True, help="Use git branch as session name")
def main(..., chat_session: Optional[str], auto_session: bool):
    if auto_session:
        chat_session = GitOperations().get_current_branch()
    
    if chat_session:
        # Load or create persistent chat
        session_mgr = ChatSessionManager(project_root)
        if session_mgr.has_session(chat_session):
            gemini_client.load_chat_session(session_mgr.get_session(chat_session))
```

## Advantages Over Simple Review Storage

1. **Full Context**: AI remembers entire conversation, not just results
2. **Natural Flow**: Can ask follow-up questions naturally
3. **Incremental Learning**: AI builds understanding over time
4. **Debugging Help**: "Why did you flag this last time?"
5. **Team Collaboration**: Share full conversation for context

## Challenges & Solutions

1. **Token Limits**: Implement sliding window or summarization
2. **Storage Size**: Compress and prune old messages
3. **API Changes**: Version the storage format
4. **Privacy**: Local storage only, optional encryption