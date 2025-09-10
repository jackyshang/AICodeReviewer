"""MCP tool implementations that consume the Review Service API."""

import json
import uuid
import subprocess
import sys
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .client import ReviewServiceClient
from ..cli import load_config

class MCPTools:
    """MCP tool implementations that use the Review Service."""
    
    def __init__(self):
        self.client = ReviewServiceClient()
        
    async def __aenter__(self):
        await self.client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        
    async def review_changes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Review uncommitted changes with full CLI parity."""
        # Extract all parameters
        try:
            dir_arg = args.get('directory', '.')
            # Handle case where directory might already be a Path or contain invalid chars
            if isinstance(dir_arg, str):
                directory = str(Path(dir_arg).resolve())
            else:
                directory = str(Path('.').resolve())
        except Exception as e:
            return self._error_response(f"Invalid directory parameter: {e}")
        story = args.get('story')
        mode = args.get('mode', 'critical')
        session_name = args.get('session_name')
        no_session = args.get('no_session', False)
        output_format = args.get('output_format', 'compact')
        include_unchanged = args.get('include_unchanged', False)
        design_doc = args.get('design_doc')
        fast = args.get('fast', False)
        verbose = args.get('verbose', False)
        debug = args.get('debug', False)
        config_path = args.get('config_path')
        save_to_file = args.get('save_to_file')
        
        # Handle story from file
        if story and Path(story).exists():
            try:
                with open(story, 'r') as f:
                    story = f.read()
                if verbose:
                    story = f"[From file: {args.get('story')}]\n\n{story}"
            except:
                pass  # Treat as literal text if can't read
                
        # Handle design doc
        if not design_doc:
            # Check for README.md in project root
            try:
                readme_path = Path(directory) / "README.md"
                if readme_path.exists():
                    design_doc = str(readme_path)
            except Exception as e:
                # Log error but continue without design doc
                print(f"Warning: Could not check for README.md: {e}")
                
        if design_doc and Path(design_doc).exists():
            try:
                with open(design_doc, 'r') as f:
                    design_doc_content = f.read()
            except:
                design_doc_content = None
        else:
            design_doc_content = None
        
        # Load config
        if config_path:
            config = load_config(Path(config_path))
        else:
            config = load_config()
        
        # Determine model
        if fast:
            model_name = "gemini-2.5-flash"
        else:
            model_name = config["review"]["provider"]
        
        # Auto-generate session name if not provided and sessions enabled
        if not no_session and not session_name:
            session_name = f"mcp-{uuid.uuid4().hex[:8]}"
            
        # Set session to None if no_session is True
        if no_session:
            session_name = None
        
        try:
            # Call service
            result = await self.client.create_review(
                project_root=directory,
                session_name=session_name,
                mode=mode,
                story=story,
                design_doc=design_doc_content,
                include_unchanged=include_unchanged,
                model_name=model_name,
                debug=debug,
                max_iterations=config["review"]["navigation"].get("max_iterations", 20),
                show_progress=verbose
            )
            
            # Check for no changes
            if result.get('has_changes') is False:
                return {
                    "content": [{
                        "type": "text",
                        "text": "📭 No uncommitted changes found in the repository."
                    }]
                }
            
            # Format output based on requested format
            if output_format == "human":
                output = self._format_human_output(result, mode, verbose)
            elif output_format == "markdown":
                output = self._format_markdown_output(result, mode)
            else:
                output = self._format_compact_output(result, mode)
            
            # Save to file if requested
            if save_to_file:
                Path(save_to_file).write_text(output)
                output += f"\n\n📝 Review saved to: {save_to_file}"
            
            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
            
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Review failed: {str(e)}\n\n"
                           f"Make sure the review service is running:\n"
                           f"  llm-review --service status"
                }]
            }
            
    async def list_review_sessions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all active review sessions with filtering."""
        project_filter = args.get('project_filter')
        limit = args.get('limit', 20)
        sort_by = args.get('sort_by', 'last_reviewed')
        format_type = args.get('format', 'list')
        
        try:
            result = await self.client.list_sessions()
            sessions = result.get('sessions', [])
            
            # Filter by project if requested
            if project_filter:
                sessions = [s for s in sessions if project_filter in s.get('name', '')]
                
            # Sort sessions
            if sort_by == 'created':
                sessions.sort(key=lambda s: s.get('created_at', ''))
            elif sort_by == 'last_reviewed':
                sessions.sort(key=lambda s: s.get('last_reviewed', ''), reverse=True)
            elif sort_by == 'name':
                sessions.sort(key=lambda s: s.get('name', ''))
            elif sort_by == 'iterations':
                sessions.sort(key=lambda s: s.get('iteration', 0), reverse=True)
                
            # Apply limit
            sessions = sessions[:limit]
            
            # Format output
            if format_type == 'json':
                output = json.dumps(sessions, indent=2)
            elif format_type == 'detailed':
                output = self._format_sessions_detailed(sessions)
            else:
                output = self._format_sessions_list(sessions)
                
            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
        except Exception as e:
            return self._error_response(f"Failed to list sessions: {e}")
            
    async def manage_review_service(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Manage the review service."""
        action = args.get('action')
        tail_lines = args.get('tail_lines', 20)
        
        if action == 'status':
            return await self._service_status()
        elif action == 'start':
            return await self._service_start()
        elif action == 'stop':
            return await self._service_stop()
        elif action == 'restart':
            return await self._service_restart()
        elif action == 'logs':
            return await self._service_logs(tail_lines)
        elif action == 'errors':
            return await self._service_errors(tail_lines)
        else:
            return self._error_response(f"Unknown action: {action}")
            
    async def get_session_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific session."""
        session_name = args.get('session_name')
        project_root = args.get('project_root')
        include_history = args.get('include_history', False)
        
        if not session_name or not project_root:
            return self._error_response("session_name and project_root are required")
            
        # Build project-scoped key
        session_key = f"{project_root}:{session_name}"
        
        try:
            session = await self.client.get_session(session_key)
            
            output = f"📊 Session Details: {session_name}\n"
            output += "=" * 40 + "\n\n"
            output += f"Project: {project_root}\n"
            output += f"Created: {session['created_at']}\n"
            output += f"Last reviewed: {session['last_reviewed']}\n"
            output += f"Iterations: {session['iteration']}\n"
            output += f"Messages: {session['messages']}\n"
            output += f"Model: {session['model']}\n"
            
            if include_history and session.get('messages') > 0:
                output += "\n📜 Conversation History:\n"
                output += "Coming soon..."  # Would need new endpoint
                
            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
        except ValueError as e:
            return self._error_response(str(e))
        except Exception as e:
            return self._error_response(f"Failed to get session details: {e}")
            
    async def clear_session(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Clear/delete a specific review session."""
        session_name = args.get('session_name')
        project_root = args.get('project_root')
        confirm = args.get('confirm', True)
        
        if not session_name or not project_root:
            return self._error_response("session_name and project_root are required")
            
        if not confirm:
            return self._error_response("Deletion cancelled (confirm=false)")
            
        # Build project-scoped key
        session_key = f"{project_root}:{session_name}"
        
        try:
            result = await self.client.clear_session(session_key)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"✅ {result.get('message', 'Session cleared')}"
                }]
            }
        except ValueError as e:
            return self._error_response(str(e))
        except Exception as e:
            return self._error_response(f"Failed to clear session: {e}")
            
    # Service management methods
    async def _service_status(self) -> Dict[str, Any]:
        """Check service status."""
        try:
            health = await self.client.check_health()
            
            output = "🏥 Review Service Status\n"
            output += "=" * 40 + "\n\n"
            output += f"✅ Status: Running\n"
            output += f"📊 Active sessions: {health['active_sessions']}\n"
            output += f"🕐 Timestamp: {health['timestamp']}\n"
            
            if health.get('sessions'):
                output += f"\nActive session names:\n"
                for session in health['sessions']:
                    # Extract display name from project-scoped key
                    display_name = session.split(':', 1)[-1] if ':' in session else session
                    output += f"  • {display_name}\n"
                    
            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
        except Exception:
            return {
                "content": [{
                    "type": "text",
                    "text": "🏥 Review Service Status\n" +
                           "=" * 40 + "\n\n" +
                           "❌ Status: Not Running\n\n" +
                           "Start the service with:\n" +
                           "  llm-review --service restart\n\n" +
                           "Or it will auto-start on first review."
                }]
            }
            
    async def _service_start(self) -> Dict[str, Any]:
        """Start the service."""
        if sys.platform == "darwin":
            try:
                subprocess.run(["launchctl", "start", "com.reviewer.api"], check=True)
                return {
                    "content": [{
                        "type": "text",
                        "text": "✅ Service start command sent.\nCheck status in a few seconds."
                    }]
                }
            except subprocess.CalledProcessError:
                return self._error_response("Failed to start service via launchctl")
        else:
            return self._error_response("Service management is only available on macOS")
            
    async def _service_stop(self) -> Dict[str, Any]:
        """Stop the service."""
        if sys.platform == "darwin":
            try:
                subprocess.run(["launchctl", "stop", "com.reviewer.api"], check=True)
                return {
                    "content": [{
                        "type": "text",
                        "text": "✅ Service stopped."
                    }]
                }
            except subprocess.CalledProcessError:
                return self._error_response("Failed to stop service")
        else:
            return self._error_response("Service management is only available on macOS")
            
    async def _service_restart(self) -> Dict[str, Any]:
        """Restart the service."""
        if sys.platform == "darwin":
            try:
                subprocess.run(["launchctl", "stop", "com.reviewer.api"], check=False)
                import time
                time.sleep(1)
                subprocess.run(["launchctl", "start", "com.reviewer.api"], check=False)
                return {
                    "content": [{
                        "type": "text",
                        "text": "✅ Service restart command sent.\nCheck status in a few seconds."
                    }]
                }
            except Exception as e:
                return self._error_response(f"Failed to restart service: {e}")
        else:
            return self._error_response("Service management is only available on macOS")
            
    async def _service_logs(self, lines: int) -> Dict[str, Any]:
        """Get service logs."""
        try:
            log_path = "/tmp/reviewer.log"
            if not Path(log_path).exists():
                return {
                    "content": [{
                        "type": "text",
                        "text": "📜 No service logs found."
                    }]
                }
            
            result = subprocess.run(
                ["tail", "-n", str(lines), log_path],
                capture_output=True,
                text=True
            )
            
            output = f"📜 Service Logs (last {lines} lines)\n"
            output += "=" * 40 + "\n"
            output += result.stdout or "No logs available."
            
            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
        except Exception as e:
            return self._error_response(f"Failed to read logs: {e}")
            
    async def _service_errors(self, lines: int) -> Dict[str, Any]:
        """Get service error logs."""
        try:
            log_path = "/tmp/reviewer.error.log"
            if not Path(log_path).exists():
                return {
                    "content": [{
                        "type": "text",
                        "text": "📜 No error logs found."
                    }]
                }
            
            result = subprocess.run(
                ["tail", "-n", str(lines), log_path],
                capture_output=True,
                text=True
            )
            
            output = f"❌ Service Error Logs (last {lines} lines)\n"
            output += "=" * 40 + "\n"
            output += result.stdout or "No errors."
            
            return {
                "content": [{
                    "type": "text",
                    "text": output
                }]
            }
        except Exception as e:
            return self._error_response(f"Failed to read error logs: {e}")
            
    # Formatting helpers
    def _format_compact_output(self, result: Dict[str, Any], mode: str) -> str:
        """Format review output in compact mode."""
        session_info = result.get('session_info', {})
        review_result = result.get('review_result', {})
        
        lines = []
        
        # Minimal header
        if session_info.get('status') == 'new':
            lines.append(f"Session: {session_info.get('name', 'unknown')}")
        else:
            lines.append(f"Session: {session_info.get('name', 'unknown')} (iteration {session_info.get('iteration', 0)})")
            
        lines.append(f"Mode: {mode}")
        lines.append("")
        
        # Review content
        content = review_result.get('review_content', 'No issues found.')
        lines.append(content)
        
        return "\n".join(lines)
        
    def _format_human_output(self, result: Dict[str, Any], mode: str, verbose: bool) -> str:
        """Format review output in human-readable mode."""
        session_info = result.get('session_info', {})
        review_result = result.get('review_result', {})
        
        lines = []
        
        # Header with emojis
        lines.append("🔍 Code Review Results")
        lines.append("=" * 50)
        
        # Session info
        if session_info.get('status') == 'new':
            lines.append(f"🆕 New Session: {session_info.get('name', 'unknown')}")
        else:
            lines.append(f"🔄 Continuing Session: {session_info.get('name', 'unknown')}")
            lines.append(f"   Iteration: {session_info.get('iteration', 0)}")
            lines.append(f"   Previous issues: {session_info.get('previous_issues_count', 0)}")
            
        # Mode description
        mode_desc = {
            'critical': '🚨 Critical Issues Only',
            'full': '📋 Full Review (All Issues)',
            'ai-generated': '🤖 AI-Generated Code Review',
            'prototype': '🚀 Prototype Mode (Security Deprioritized)'
        }
        lines.append(f"\nMode: {mode_desc.get(mode, mode)}")
        lines.append("")
        
        # Review content with formatting
        content = review_result.get('review_content', '')
        if content:
            lines.append(content)
        else:
            lines.append("✅ No issues found!")
            
        # Statistics
        if verbose and 'navigation_summary' in review_result:
            nav = review_result['navigation_summary']
            lines.append("\n📊 Review Statistics:")
            lines.append(f"  • Files explored: {nav.get('files_explored', 0)}")
            lines.append(f"  • Files read: {nav.get('files_read', 0)}")
            lines.append(f"  • Total iterations: {nav.get('total_iterations', 0)}")
            
        # Token usage
        if 'token_details' in review_result:
            tokens = review_result['token_details']
            lines.append(f"\n💰 Token Usage:")
            lines.append(f"  • Input: {tokens.get('input_tokens', 0):,}")
            lines.append(f"  • Output: {tokens.get('output_tokens', 0):,}")
            lines.append(f"  • Total: {tokens.get('total_tokens', 0):,}")
            
        return "\n".join(lines)
        
    def _format_markdown_output(self, result: Dict[str, Any], mode: str) -> str:
        """Format review output as markdown."""
        session_info = result.get('session_info', {})
        review_result = result.get('review_result', {})
        
        lines = []
        
        # Markdown header
        lines.append("# Code Review Report")
        lines.append("")
        lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Session**: {session_info.get('name', 'unknown')}")
        lines.append(f"**Mode**: {mode}")
        lines.append("")
        
        # Review content
        lines.append("## Review Results")
        lines.append("")
        
        content = review_result.get('review_content', 'No issues found.')
        lines.append(content)
        
        # Add metadata
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Metadata")
        lines.append("")
        
        if 'navigation_summary' in review_result:
            nav = review_result['navigation_summary']
            lines.append("### Navigation Summary")
            lines.append(f"- Files explored: {nav.get('files_explored', 0)}")
            lines.append(f"- Files read: {nav.get('files_read', 0)}")
            lines.append("")
            
        if 'token_details' in review_result:
            tokens = review_result['token_details']
            lines.append("### Token Usage")
            lines.append(f"- Input tokens: {tokens.get('input_tokens', 0):,}")
            lines.append(f"- Output tokens: {tokens.get('output_tokens', 0):,}")
            lines.append(f"- Total tokens: {tokens.get('total_tokens', 0):,}")
            
        return "\n".join(lines)
        
    def _format_sessions_list(self, sessions: list) -> str:
        """Format sessions as a simple list."""
        if not sessions:
            return "📋 No active review sessions found."
            
        output = f"📋 Active Review Sessions ({len(sessions)})\n"
        output += "=" * 40 + "\n\n"
        
        for i, session in enumerate(sessions, 1):
            output += f"{i}. {session['name']}\n"
            output += f"   Last reviewed: {self._format_time(session['last_reviewed'])}\n"
            output += f"   Iterations: {session['iteration']}\n\n"
            
        return output
        
    def _format_sessions_detailed(self, sessions: list) -> str:
        """Format sessions with detailed information."""
        if not sessions:
            return "📋 No active review sessions found."
            
        output = f"📋 Active Review Sessions ({len(sessions)})\n"
        output += "=" * 40 + "\n\n"
        
        for session in sessions:
            output += f"Session: {session['name']}\n"
            output += f"  Created: {session['created_at']}\n"
            output += f"  Last reviewed: {session['last_reviewed']}\n"
            output += f"  Iterations: {session['iteration']}\n"
            output += f"  Messages: {session['messages']}\n"
            output += "-" * 30 + "\n"
            
        return output
        
    def _format_time(self, timestamp: str) -> str:
        """Format timestamp as relative time."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo)
            delta = now - dt
            
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
        except:
            return timestamp
            
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Format error response."""
        return {
            "content": [{
                "type": "text",
                "text": f"❌ Error: {message}"
            }]
        }