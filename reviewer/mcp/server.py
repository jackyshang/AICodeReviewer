"""MCP Server for Reviewer Tool."""

import json
import sys
import asyncio
import subprocess
import time
import os
from typing import Dict, Any, Optional, List

from .protocol import JSONRPCProtocol
from .tools import MCPTools

class ReviewerMCPServer:
    """MCP Server that acts as a thin client to the Review Service API."""
    
    def __init__(self):
        self.initialized = False
        self.protocol = JSONRPCProtocol()
        self.tools: Optional[MCPTools] = None
        self.ensure_service_running()
        
    def ensure_service_running(self):
        """Ensure the review service is running."""
        # Check if service is already running
        try:
            import requests
            resp = requests.get("http://localhost:8765/health", timeout=1)
            if resp.status_code == 200:
                self.protocol.log("Review service is already running")
                return
        except:
            pass
            
        self.protocol.log("Attempting to start review service...")
        
        # Try to start service
        if sys.platform == "darwin":
            # macOS: Use launchctl
            try:
                subprocess.run(
                    ["launchctl", "start", "com.reviewer.api"], 
                    capture_output=True
                )
                self.protocol.log("Sent start command via launchctl")
            except Exception as e:
                self.protocol.log(f"Failed to use launchctl: {e}")
        else:
            # Other platforms: Start directly
            try:
                subprocess.Popen(
                    [sys.executable, "-m", "reviewer.service"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                self.protocol.log("Started service directly")
            except Exception as e:
                self.protocol.log(f"Failed to start service: {e}")
            
        # Wait for service to start
        time.sleep(2)
        
    async def start(self):
        """Start the MCP server."""
        self.protocol.log("Starting Reviewer MCP Server")
        
        self.tools = MCPTools()
        await self.tools.__aenter__()
        
        try:
            await self.process_messages()
        finally:
            await self.tools.__aexit__(None, None, None)
            
    async def process_messages(self):
        """Process JSON-RPC messages from stdin."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol, sys.stdin
        )
        
        self.protocol.log("Ready to process messages")
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                    
                # Extract and handle messages
                messages = self.protocol.extract_messages(line.decode())
                for message in messages:
                    response = await self.handle_message(message)
                    if response:
                        self.protocol.send_response(response)
                        
            except Exception as e:
                self.protocol.log(f"Error processing message: {e}")
                
    async def handle_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Handle a JSON-RPC message."""
        method = message.get('method')
        params = message.get('params', {})
        msg_id = message.get('id')
        
        # Skip notifications (no id)
        if msg_id is None:
            self.protocol.log(f"Received notification: {method}")
            return None
        
        self.protocol.log(f"Handling request: {method}")
        
        try:
            if method == 'initialize':
                result = await self.handle_initialize(params)
            elif method == 'tools/list':
                result = await self.handle_tools_list(params)
            elif method == 'tools/call':
                result = await self.handle_tool_call(params)
            elif method == 'resources/list':
                result = await self.handle_resources_list(params)
            elif method == 'resources/read':
                result = await self.handle_resource_read(params)
            elif method == 'prompts/list':
                result = await self.handle_prompts_list(params)
            elif method == 'prompts/get':
                result = await self.handle_prompts_get(params)
            else:
                return self.protocol.create_error(
                    msg_id, -32601, f"Method not found: {method}"
                )
                
            return self.protocol.create_response(msg_id, result)
            
        except Exception as e:
            self.protocol.log(f"Error handling {method}: {e}")
            return self.protocol.create_error(
                msg_id, -32603, f"Internal error: {str(e)}"
            )
            
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        self.initialized = True
        client_info = params.get('clientInfo', {})
        self.protocol.log(f"Initialized by {client_info.get('name', 'unknown')}")
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "reviewer",
                "version": "1.0.0"
            }
        }
        
    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools."""
        return {
            "tools": [
                {
                    "name": "review_changes",
                    "description": "Review uncommitted git changes with AI-powered analysis. For iterative development, use 'session_name' to maintain context across multiple review rounds. Examples: 'Review my code', 'Do a security review', 'Check my AI-generated code for issues'",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Path to git repository. Can be absolute (/path/to/repo) or relative (./repo). Defaults to current directory if not specified.",
                                "examples": [".", "/Users/name/project", "../other-repo"]
                            },
                            "session_name": {
                                "type": "string",
                                "description": "🔄 RECOMMENDED: Named session for continuous review workflows. Sessions maintain conversation history across multiple review rounds, enabling the AI to provide context-aware feedback and track issue resolution. Essential for iterative development where you'll address feedback and review again. Scoped per project to prevent cross-contamination. Cannot be used with 'no_session'. Example: 'feature-auth', 'bug-fix-123', 'refactor-api'",
                                "pattern": "^[a-zA-Z0-9-_]+$"
                            },
                            "story": {
                                "type": "string",
                                "description": "Story/purpose context. If this is a valid file path, its contents will be read. Otherwise treated as literal text. Examples: 'Fix login bug', './stories/feature-123.md', 'Implement user authentication'"
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["critical", "full", "ai-generated", "prototype"],
                                "description": "Review mode:\n• critical: Only must-fix issues (default)\n• full: All issues including suggestions\n• ai-generated: Detect AI hallucinations and incomplete code\n• prototype: Skip security issues for rapid prototyping",
                                "default": "critical"
                            },
                            "no_session": {
                                "type": "boolean",
                                "description": "⚠️ Disable session persistence (one-shot review). Only use for quick, standalone reviews where you won't need to address feedback iteratively. For most development workflows, prefer using 'session_name' instead. Cannot be used with 'session_name'.",
                                "default": False
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["compact", "human", "markdown"],
                                "description": "Output format:\n• compact: Minimal output for AI processing\n• human: Formatted with emojis and sections\n• markdown: Full markdown report for documentation",
                                "default": "compact"
                            },
                            "include_unchanged": {
                                "type": "boolean",
                                "description": "Include unchanged files for additional context",
                                "default": False
                            },
                            "design_doc": {
                                "type": "string",
                                "description": "Path to design document for additional context. If not specified and README.md exists in project root, it will be used automatically."
                            },
                            "fast": {
                                "type": "boolean",
                                "description": "Use Gemini 2.5 Flash model for 5x faster analysis. Trade-off: slightly less thorough than Pro model.",
                                "default": False
                            },
                            "verbose": {
                                "type": "boolean",
                                "description": "Show step-by-step progress of what files are being analyzed. Useful for understanding the review process.",
                                "default": False
                            },
                            "debug": {
                                "type": "boolean",
                                "description": "Developer mode: Show raw API requests/responses. Only use if troubleshooting issues.",
                                "default": False
                            },
                            "config_path": {
                                "type": "string",
                                "description": "Path to .llm-review.yaml config file"
                            },
                            "save_to_file": {
                                "type": "string",
                                "description": "Save review output to specified markdown file"
                            }
                        }
                    }
                },
                {
                    "name": "list_review_sessions",
                    "description": "List all active code review sessions with filtering options",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_filter": {
                                "type": "string",
                                "description": "Filter sessions by project path (partial match)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of sessions to return",
                                "default": 20,
                                "minimum": 1,
                                "maximum": 100
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["created", "last_reviewed", "name", "iterations"],
                                "description": "Sort sessions by field",
                                "default": "last_reviewed"
                            },
                            "format": {
                                "type": "string",
                                "enum": ["list", "detailed", "json"],
                                "description": "Output format",
                                "default": "list"
                            }
                        }
                    }
                },
                {
                    "name": "manage_review_service",
                    "description": "Control the background review service that maintains session state. The service auto-starts when needed.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["status", "start", "stop", "restart", "logs", "errors"],
                                "description": "[REQUIRED] Action to perform:\n• status: Check if service is running\n• start: Start the service\n• stop: Stop the service\n• restart: Restart the service\n• logs: View recent service logs\n• errors: View error logs only"
                            },
                            "tail_lines": {
                                "type": "integer",
                                "description": "Number of log lines to display (only for 'logs' and 'errors' actions)",
                                "default": 20,
                                "minimum": 1,
                                "maximum": 1000
                            }
                        },
                        "required": ["action"]
                    }
                },
                {
                    "name": "get_session_details",
                    "description": "Retrieve metadata about a review session including creation time, iteration count, and message history stats",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_name": {
                                "type": "string",
                                "description": "[REQUIRED] Name of the session to query. Example: 'feature-auth'",
                                "pattern": "^[a-zA-Z0-9-_]+$"
                            },
                            "project_root": {
                                "type": "string",
                                "description": "[REQUIRED] Absolute path to project root. Sessions are scoped per project to prevent cross-contamination."
                            },
                            "include_history": {
                                "type": "boolean",
                                "description": "Include full conversation history (coming soon). Currently returns metadata only.",
                                "default": False
                            }
                        },
                        "required": ["session_name", "project_root"]
                    }
                },
                {
                    "name": "clear_session",
                    "description": "Delete a review session and all its conversation history. This action is irreversible.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_name": {
                                "type": "string",
                                "description": "[REQUIRED] Name of the session to delete",
                                "pattern": "^[a-zA-Z0-9-_]+$"
                            },
                            "project_root": {
                                "type": "string",
                                "description": "[REQUIRED] Absolute path to project root"
                            },
                            "confirm": {
                                "type": "boolean",
                                "description": "Safety confirmation. Set to false to cancel deletion.",
                                "default": True
                            }
                        },
                        "required": ["session_name", "project_root"]
                    }
                }
            ]
        }
        
    async def handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call."""
        name = params.get('name')
        arguments = params.get('arguments', {})
        
        self.protocol.log(f"Tool call: {name}")
        
        try:
            if name == 'review_changes':
                return await self.tools.review_changes(arguments)
            elif name == 'list_review_sessions':
                return await self.tools.list_review_sessions(arguments)
            elif name == 'manage_review_service':
                return await self.tools.manage_review_service(arguments)
            elif name == 'get_session_details':
                return await self.tools.get_session_details(arguments)
            elif name == 'clear_session':
                return await self.tools.clear_session(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            self.protocol.log(f"Error in tool call: {e}")
            import traceback
            self.protocol.log(f"Traceback: {traceback.format_exc()}")
            raise
            
    async def handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources."""
        return {
            "resources": [
                {
                    "uri": "review://sessions",
                    "name": "Active Review Sessions",
                    "description": "JSON array of all active review sessions across all projects. Each session includes: name, project_root, created_at, last_reviewed, iteration count, and message count.",
                    "mimeType": "application/json"
                },
                {
                    "uri": "review://config",
                    "name": "Review Configuration",
                    "description": "Current llm-review configuration in YAML format. Shows model settings, review options, and navigation limits.",
                    "mimeType": "application/yaml"
                }
            ]
        }
        
    async def handle_resource_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a resource."""
        uri = params.get('uri')
        
        if uri == "review://sessions":
            sessions = await self.tools.client.list_sessions()
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(sessions, indent=2)
                }]
            }
        elif uri == "review://config":
            from ..cli import load_config
            import yaml
            config = load_config()
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/yaml",
                    "text": yaml.dump(config)
                }]
            }
        else:
            raise ValueError(f"Unknown resource: {uri}")
            
    async def handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available prompts."""
        return {
            "prompts": [
                {
                    "name": "comprehensive_review",
                    "description": "Perform a comprehensive code review with all checks"
                },
                {
                    "name": "security_review",
                    "description": "Focus specifically on security vulnerabilities"
                },
                {
                    "name": "performance_review",
                    "description": "Focus on performance optimizations"
                },
                {
                    "name": "quick_review",
                    "description": "Quick review focusing only on critical issues"
                }
            ]
        }
        
    async def handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific prompt."""
        name = params.get('name')
        
        prompts = {
            "comprehensive_review": {
                "name": "comprehensive_review",
                "description": "Perform a comprehensive code review with all checks",
                "arguments": [
                    {
                        "name": "focus_areas",
                        "description": "Comma-separated areas to focus on (security, performance, style, etc.)",
                        "required": False
                    },
                    {
                        "name": "severity_threshold",
                        "description": "Minimum severity to report (critical, high, medium, low)",
                        "required": False,
                        "default": "low"
                    }
                ]
            },
            "security_review": {
                "name": "security_review",
                "description": "Focus specifically on security vulnerabilities",
                "arguments": []
            },
            "performance_review": {
                "name": "performance_review",
                "description": "Focus on performance optimizations",
                "arguments": [
                    {
                        "name": "profile_data",
                        "description": "Path to profiling data if available",
                        "required": False
                    }
                ]
            },
            "quick_review": {
                "name": "quick_review",
                "description": "Quick review focusing only on critical issues",
                "arguments": []
            }
        }
        
        prompt = prompts.get(name)
        if prompt:
            return prompt
        else:
            raise ValueError(f"Unknown prompt: {name}")