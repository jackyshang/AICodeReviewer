"""HTTP client for the LLM Review Service API."""

import aiohttp
import os
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import quote

class ReviewServiceClient:
    """Async HTTP client for the LLM Review Service API."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get(
            'LLM_REVIEW_SERVICE_URL', 
            'http://localhost:8765'
        )
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def check_health(self) -> Dict[str, Any]:
        """Check service health via GET /health."""
        async with self.session.get(f"{self.base_url}/health") as resp:
            if resp.status == 200:
                return await resp.json()
            raise Exception(f"Service unhealthy: {resp.status}")
            
    async def create_review(self, project_root: str, session_name: Optional[str],
                          mode: str = "critical", story: Optional[str] = None,
                          design_doc: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a code review via POST /review."""
        # Import here to avoid circular dependencies
        try:
            from reviewer.git_operations import GitOperations
            from reviewer.codebase_indexer import CodebaseIndexer
        except ImportError as e:
            raise Exception(f"Failed to import required modules: {e}")
        
        try:
            git_ops = GitOperations(project_root)
        except Exception as e:
            raise Exception(f"Failed to initialize GitOperations with {project_root}: {e}")
        
        # Check for changes
        if not git_ops.has_uncommitted_changes():
            return {
                "error": "No uncommitted changes found",
                "has_changes": False
            }
        
        # Get change data (service expects this)
        changed_files = git_ops.get_uncommitted_files()
        diffs = git_ops.get_all_diffs()
        
        # Build codebase summary
        indexer = CodebaseIndexer(Path(project_root))
        index = indexer.build_index()
        codebase_summary = indexer.get_index_summary(index)
        
        # Prepare review request matching ReviewRequest model
        review_request = {
            "session_name": session_name or f"mcp-review-{os.getpid()}",
            "project_root": project_root,
            "initial_context": f"MCP Review Request - Mode: {mode}",
            "codebase_summary": codebase_summary,
            "changed_files": changed_files,
            "diffs": diffs,
            "show_all": mode == "full",
            "ai_generated": mode == "ai-generated",
            "prototype": mode == "prototype",
            "story": story,
            "design_doc": design_doc,
            **kwargs  # Pass through additional options
        }
        
        # Call service
        async with self.session.post(
            f"{self.base_url}/review", 
            json=review_request
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                error_text = await resp.text()
                raise Exception(f"Review failed ({resp.status}): {error_text}")
                
    async def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions via GET /sessions."""
        async with self.session.get(f"{self.base_url}/sessions") as resp:
            if resp.status == 200:
                return await resp.json()
            raise Exception(f"Failed to list sessions: {resp.status}")
            
    async def get_session(self, session_name: str) -> Dict[str, Any]:
        """Get session details via GET /sessions/{name}."""
        # URL-encode the session name to handle project paths with slashes
        encoded_name = quote(session_name, safe='')
        async with self.session.get(
            f"{self.base_url}/sessions/{encoded_name}"
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 404:
                raise ValueError(f"Session '{session_name}' not found")
            raise Exception(f"Failed to get session: {resp.status}")
            
    async def clear_session(self, session_name: str) -> Dict[str, Any]:
        """Clear a session via DELETE /sessions/{name}."""
        # URL-encode the session name to handle project paths with slashes
        encoded_name = quote(session_name, safe='')
        async with self.session.delete(
            f"{self.base_url}/sessions/{encoded_name}"
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 404:
                raise ValueError(f"Session '{session_name}' not found")
            raise Exception(f"Failed to clear session: {resp.status}")