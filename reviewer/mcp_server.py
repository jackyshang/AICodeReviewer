#!/usr/bin/env python3
"""MCP Server entry point for Reviewer Tool."""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reviewer.mcp.server import ReviewerMCPServer

async def main():
    """Main entry point."""
    server = ReviewerMCPServer()
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("Shutting down MCP server", file=sys.stderr)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

def run():
    """Entry point for console script."""
    # The MCP server doesn't need GEMINI_API_KEY directly
    # It communicates with the Review Service API which has its own key
    asyncio.run(main())

if __name__ == "__main__":
    run()