"""JSON-RPC 2.0 protocol handler for MCP."""

import json
from typing import Dict, Any, Optional, List
import sys

class JSONRPCProtocol:
    """Handles JSON-RPC 2.0 protocol for MCP communication."""
    
    def __init__(self):
        self.buffer = ""
        
    def parse_message(self, data: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON-RPC message from input data."""
        try:
            message = json.loads(data.strip())
            
            # Validate JSON-RPC 2.0
            if message.get('jsonrpc') != '2.0':
                return None
                
            return message
        except json.JSONDecodeError:
            return None
            
    def extract_messages(self, data: str) -> List[Dict[str, Any]]:
        """Extract complete JSON messages from streaming input."""
        self.buffer += data
        messages = []
        
        # Simple approach: split by newlines and try to parse each
        lines = self.buffer.split('\n')
        self.buffer = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                # Try to parse as complete JSON
                message = json.loads(line)
                if message.get('jsonrpc') == '2.0':
                    messages.append(message)
            except json.JSONDecodeError:
                # If we can't parse it, it might be incomplete
                # Add back to buffer
                self.buffer += line
                
        return messages
        
    def create_response(self, request_id: Any, result: Any) -> str:
        """Create a JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        return json.dumps(response)
        
    def create_error(self, request_id: Any, code: int, message: str, 
                    data: Optional[Any] = None) -> str:
        """Create a JSON-RPC error response."""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
            
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }
        return json.dumps(response)
        
    def create_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a JSON-RPC notification (no id)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            notification["params"] = params
        return json.dumps(notification)

    def send_response(self, response: str):
        """Send response to stdout for MCP."""
        print(response, flush=True)
        
    def log(self, message: str):
        """Log to stderr to avoid interfering with protocol."""
        print(f"[MCP] {message}", file=sys.stderr, flush=True)