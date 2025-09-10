"""API service for persistent Gemini chat sessions."""

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Load from project root .env file
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}", file=sys.stderr)
except ImportError:
    pass  # python-dotenv not installed

# Import existing modules
from reviewer.gemini_client import GeminiClient
from reviewer.navigation_tools import NavigationTools
from reviewer.codebase_indexer import CodebaseIndexer


class ReviewRequest(BaseModel):
    """Request model for review endpoint."""
    session_name: str
    project_root: str
    initial_context: str
    codebase_summary: str
    changed_files: Dict[str, list]
    diffs: Dict[str, str]
    # Options
    show_all: bool = False
    max_iterations: int = 20
    show_progress: bool = False
    debug: bool = False
    # Model config
    model_name: str = "gemini-2.5-pro"
    # Review modes
    ai_generated: bool = False
    prototype: bool = False
    design_doc: Optional[str] = None
    story: Optional[str] = None


class SessionInfo(BaseModel):
    """Information about a review session."""
    name: str
    status: str  # 'new' or 'continued'
    iteration: int
    created_at: str
    last_reviewed: Optional[str]
    chat_messages_count: int
    previous_issues_count: Optional[int] = None


class ReviewResponse(BaseModel):
    """Response model for review endpoint."""
    session_info: SessionInfo
    review_result: Dict[str, Any]


class ReviewerService:
    """Service for managing persistent review sessions."""
    
    def __init__(self):
        self.app = FastAPI(title="Reviewer Service")
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.time()
        self.setup_routes()
        
    def setup_routes(self):
        """Set up API routes."""
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            uptime_seconds = time.time() - self.start_time
            return {
                "status": "running",
                "active_sessions": len(self.active_sessions),
                "sessions": list(self.active_sessions.keys()),
                "uptime": uptime_seconds,
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/review", response_model=ReviewResponse)
        async def review(request: ReviewRequest):
            """Main review endpoint with session support."""
            return await self.handle_review(request)
        
        @self.app.get("/sessions")
        async def list_sessions():
            """List all active sessions."""
            sessions = []
            for name, session in self.active_sessions.items():
                sessions.append({
                    "name": name,
                    "created_at": session['created_at'].isoformat(),
                    "last_reviewed": session.get('last_reviewed', session['created_at']).isoformat(),
                    "iteration": session['iteration'],
                    "messages": len(session['chat_history']) if 'chat_history' in session else 0
                })
            return {"sessions": sessions}
        
        @self.app.get("/sessions/{session_name}")
        async def get_session(session_name: str):
            """Get details about a specific session."""
            # Decode the URL-encoded session name
            decoded_name = unquote(session_name)
            if decoded_name not in self.active_sessions:
                raise HTTPException(status_code=404, detail=f"Session '{decoded_name}' not found")
            
            session = self.active_sessions[decoded_name]
            return {
                "name": decoded_name,
                "created_at": session['created_at'].isoformat(),
                "last_reviewed": session.get('last_reviewed', session['created_at']).isoformat(),
                "iteration": session['iteration'],
                "messages": len(session['chat_history']) if 'chat_history' in session else 0,
                "model": session.get('model_name', 'gemini-2.5-pro')
            }
        
        @self.app.delete("/sessions/{session_name}")
        async def clear_session(session_name: str):
            """Clear a specific session."""
            # Decode the URL-encoded session name
            decoded_name = unquote(session_name)
            if decoded_name in self.active_sessions:
                del self.active_sessions[decoded_name]
                return {"message": f"Session '{decoded_name}' cleared"}
            else:
                raise HTTPException(status_code=404, detail=f"Session '{decoded_name}' not found")
    
    async def handle_review(self, request: ReviewRequest) -> ReviewResponse:
        """Handle review request with session management."""
        # SECURITY: Validate and resolve the project_root path
        try:
            project_root = Path(request.project_root).resolve(strict=True)
            # Ensure the path is a directory
            if not project_root.is_dir():
                raise ValueError("Path is not a directory")
            
            # Security check: Ensure path is within safe boundaries
            # Allow paths within user's home directory or temp directory (for tests)
            import tempfile
            temp_root = Path(tempfile.gettempdir()).resolve()
            safe_prefixes = [
                str(Path.home()),
                str(temp_root),
                "/tmp",
                "/var/folders",
                "/private/var/folders"  # macOS temp directory
            ]
            if not any(str(project_root).startswith(prefix) for prefix in safe_prefixes):
                raise ValueError("Project path is outside safe boundaries")
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid project_root: {str(e)}")
        
        # Create project-scoped session key to prevent cross-project pollution
        session_key = f"{str(project_root)}:{request.session_name}"
        display_name = request.session_name
        
        is_new_session = session_key not in self.active_sessions
        
        if is_new_session:
            # Create new session
            session = await self.create_new_session(session_key, display_name, request, project_root)
            session_status = "new"
            previous_issues = None
        else:
            # Continue existing session
            session = self.active_sessions[session_key]
            session['iteration'] += 1
            session['last_reviewed'] = datetime.now()
            session_status = "continued"
            
            # Get previous issues count if available
            previous_issues = session.get('last_issues_count', None)
        
        # Get or update the Gemini client
        gemini_client = session['client']
        
        # Update navigation tools with current project state
        # project_root is already validated as a Path object above
        codebase_indexer = CodebaseIndexer(project_root)
        codebase_index = codebase_indexer.build_index()
        nav_tools = NavigationTools(project_root, codebase_index)
        gemini_client.setup_navigation_tools(nav_tools)
        
        # Build initial context using the GeminiClient's format_initial_context
        base_context = gemini_client.format_initial_context(
            changed_files=request.changed_files,
            codebase_summary=request.codebase_summary,
            diffs=request.diffs,
            show_all=request.show_all,
            design_doc=request.design_doc,
            story=request.story,
            ai_generated=request.ai_generated,
            prototype=request.prototype
        )
        
        # Build context - if continuing, add session context
        if session_status == "continued":
            # Add continuation context
            initial_context = self.build_continuation_context(
                session, base_context, session['iteration']
            )
        else:
            initial_context = base_context
        
        # Perform the review using existing GeminiClient
        try:
            review_result = gemini_client.review_code(
                initial_context=initial_context,
                max_iterations=request.max_iterations,
                show_progress=request.show_progress,
                show_all=request.show_all
            )
            
            # Update session with results
            if 'chat' in session and hasattr(session['chat'], 'get_history'):
                try:
                    session['chat_history'] = session['chat'].get_history()
                except Exception as e:
                    print(f"Warning: Failed to retrieve chat history: {e}", file=sys.stderr)
            
            # Track issues count for next iteration
            review_content = review_result.get('review_content', '')
            issues_count = self.count_issues_in_review(review_content)
            session['last_issues_count'] = issues_count
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")
        
        # Build response
        session_info = SessionInfo(
            name=display_name,
            status=session_status,
            iteration=session['iteration'],
            created_at=session['created_at'].isoformat(),
            last_reviewed=session.get('last_reviewed', session['created_at']).isoformat(),
            chat_messages_count=len(session.get('chat_history', [])),
            previous_issues_count=previous_issues
        )
        
        return ReviewResponse(
            session_info=session_info,
            review_result=review_result
        )
    
    async def create_new_session(self, session_key: str, display_name: str, request: ReviewRequest, project_root: Path) -> Dict[str, Any]:
        """Create a new review session."""
        # Create GeminiClient with same parameters as CLI
        # API key comes from environment, not request
        gemini_client = GeminiClient(
            model_name=request.model_name,
            debug=request.debug
        )
        
        # Create session
        session = {
            'client': gemini_client,
            'display_name': display_name,
            'project_root': str(project_root),
            'created_at': datetime.now(),
            'last_reviewed': datetime.now(),
            'iteration': 1,
            'model_name': request.model_name,
            'chat_history': []
        }
        
        # Store the chat object reference if available
        if hasattr(gemini_client, 'chat'):
            session['chat'] = gemini_client.chat
        
        self.active_sessions[session_key] = session
        return session
    
    def build_continuation_context(self, session: Dict[str, Any], 
                                   original_context: str, iteration: int) -> str:
        """Build context for continuing a session."""
        parts = [
            f"🔄 Continuing review session (iteration {iteration})",
            f"📅 Last reviewed: {self.format_time_ago(session.get('last_reviewed', session['created_at']))}",
            ""
        ]
        
        # Add previous issues summary if available
        if session.get('last_issues_count'):
            parts.append(f"In our last review, we found {session['last_issues_count']} issues.")
            parts.append("Let me check what has changed since then.")
            parts.append("")
        
        # Add the original context
        parts.append(original_context)
        
        return "\n".join(parts)
    
    def format_time_ago(self, dt: datetime) -> str:
        """Format datetime as human-readable time ago."""
        if not dt:
            return "unknown"
        
        delta = datetime.now() - dt
        
        if delta.total_seconds() < 60:
            return "just now"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(delta.total_seconds() / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    def count_issues_in_review(self, review_content: str) -> int:
        """Count the number of issues found in a review."""
        # Simple heuristic - count issue markers
        count = 0
        markers = ['ISSUE:', 'ERROR:', 'WARNING:', 'FILE:', 'Line:']
        for marker in markers:
            count += review_content.count(marker)
        return count
    
    def run(self, host: str = "127.0.0.1", port: int = 8765):
        """Run the service."""
        print(f"Starting LLM Review Service on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)


def main():
    """Main entry point for the service."""
    service = ReviewerService()
    
    # Get configuration from environment
    host = os.environ.get('REVIEWER_HOST', '127.0.0.1')
    port = int(os.environ.get('REVIEWER_PORT', '8765'))
    
    service.run(host=host, port=port)


if __name__ == "__main__":
    main()