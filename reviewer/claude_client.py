"""Claude API client with tool calling support for code review."""

import json
import os
from typing import Any, Dict, List, Optional

import anthropic
from anthropic.types import MessageParam, ToolUseBlock, ToolResultBlockParam

from reviewer.navigation_tools import NavigationTools


class ClaudeClient:
    """Client for interacting with Claude API with navigation tools."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "claude-opus-4-20250514",
        debug: bool = False,
    ):
        """Initialize Claude client.

        Args:
            api_key: Claude API key. If None, reads from ANTHROPIC_API_KEY env var
            model_name: Name of the Claude model to use
            debug: Enable debug logging of API requests/responses
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Claude API key not provided. Set ANTHROPIC_API_KEY environment variable."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model_name = model_name
        self.navigation_tools = None
        self.debug = debug

    def setup_navigation_tools(self, nav_tools: NavigationTools):
        """Set up navigation tools for the AI to use.

        Args:
            nav_tools: NavigationTools instance
        """
        self.navigation_tools = nav_tools

        # Define tool schemas for Claude
        self.tools = [
            {
                "name": "read_file",
                "description": "Read and return the content of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file relative to repository root",
                        }
                    },
                    "required": ["filepath"],
                },
            },
            {
                "name": "search_symbol",
                "description": "Find where a class, function, or variable is defined",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name of the symbol to search for",
                        }
                    },
                    "required": ["symbol_name"],
                },
            },
            {
                "name": "find_usages",
                "description": "Find all places where a symbol is used in the codebase",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name of the symbol to find usages for",
                        }
                    },
                    "required": ["symbol_name"],
                },
            },
            {
                "name": "get_imports",
                "description": "Get all imports from a specific file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file relative to repository root",
                        }
                    },
                    "required": ["filepath"],
                },
            },
            {
                "name": "get_file_tree",
                "description": "Get the project directory structure as a tree",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "search_text",
                "description": "Search for a text pattern across the codebase",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regular expression pattern to search for",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Optional file pattern to limit search (e.g., '*.py')",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        ]

    def _execute_function(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a function call from Claude.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Function result
        """
        if not self.navigation_tools:
            return {"error": "Navigation tools not initialized"}

        # Map function names to actual methods
        function_map = {
            "read_file": lambda: self.navigation_tools.read_file(tool_input.get("filepath")),
            "search_symbol": lambda: self.navigation_tools.search_symbol(
                tool_input.get("symbol_name")
            ),
            "find_usages": lambda: self.navigation_tools.find_usages(tool_input.get("symbol_name")),
            "get_imports": lambda: self.navigation_tools.get_imports(tool_input.get("filepath")),
            "get_file_tree": lambda: self.navigation_tools.get_file_tree(),
            "search_text": lambda: self.navigation_tools.search_text(
                tool_input.get("pattern"), tool_input.get("file_pattern")
            ),
        }

        if tool_name in function_map:
            try:
                result = function_map[tool_name]()
                return result
            except Exception as e:
                return {"error": f"Error executing {tool_name}: {str(e)}"}
        else:
            return {"error": f"Unknown function: {tool_name}"}

    def review_code(
        self,
        initial_context: str,
        max_iterations: int = 20,
        show_progress: bool = False,
        show_all: bool = False,
    ) -> Dict[str, Any]:
        """Perform code review with AI navigation.

        Args:
            initial_context: Initial context including file changes and codebase index
            max_iterations: Maximum number of tool-calling iterations
            show_progress: Show progress of navigation steps
            show_all: Whether to show all issues or just critical ones

        Returns:
            Dictionary with review results and navigation history
        """
        if not self.navigation_tools:
            raise ValueError("Navigation tools not set up. Call setup_navigation_tools first.")

        navigation_history = []
        messages: List[MessageParam] = [{"role": "user", "content": initial_context}]

        # Track token usage across all API calls
        total_input_tokens = 0
        total_output_tokens = 0

        if self.debug:
            print("\n" + "=" * 80)
            print("DEBUG: Initial API Request")
            print("=" * 80)
            print(f"Context length: {len(initial_context)} characters")
            print("\nContext preview:")
            print(initial_context[:500] + "..." if len(initial_context) > 500 else initial_context)
            print("=" * 80 + "\n")

        # Send initial message
        response = self.client.messages.create(
            model=self.model_name, max_tokens=4096, tools=self.tools, messages=messages
        )

        # Track tokens from initial request
        if hasattr(response, "usage"):
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        # Handle tool calls iteratively
        iterations = 0
        final_content = ""

        while iterations < max_iterations:
            # Check if response contains tool calls
            tool_uses = [block for block in response.content if isinstance(block, ToolUseBlock)]

            if not tool_uses:
                # No more tool calls, extract final content
                text_blocks = [block.text for block in response.content if hasattr(block, "text")]
                final_content = "\n".join(text_blocks)
                break

            if self.debug:
                print(f"\nDEBUG: API Response {iterations + 1} - Tool Calls")
                print("-" * 40)
                for tool_use in tool_uses:
                    print(f"Tool: {tool_use.name}")
                    print(f"Input: {tool_use.input}")
                print("-" * 40)

            # Add assistant's response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls
            tool_results = []
            for tool_use in tool_uses:
                if show_progress:
                    print(f"  → Calling {tool_use.name}({tool_use.input})")

                result = self._execute_function(tool_use.name, tool_use.input)
                navigation_history.append(
                    {
                        "function": tool_use.name,
                        "args": tool_use.input,
                        "result_preview": (
                            str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                        ),
                    }
                )

                # Convert result to string format for Claude
                if isinstance(result, dict):
                    result_content = json.dumps(result, indent=2)
                elif isinstance(result, list):
                    result_content = json.dumps(result, indent=2)
                else:
                    result_content = str(result)

                tool_results.append(
                    ToolResultBlockParam(
                        type="tool_result", tool_use_id=tool_use.id, content=result_content
                    )
                )

                if self.debug:
                    print(f"\nDEBUG: Tool Result for {tool_use.name}")
                    print("-" * 40)
                    result_str = str(result)
                    print(result_str[:1000] + "..." if len(result_str) > 1000 else result_str)
                    print("-" * 40)

            # Send tool results back to Claude
            messages.append({"role": "user", "content": tool_results})

            if self.debug:
                print(f"\nDEBUG: Sending {len(tool_results)} tool results back to API")

            response = self.client.messages.create(
                model=self.model_name, max_tokens=4096, tools=self.tools, messages=messages
            )

            # Track tokens from follow-up requests
            if hasattr(response, "usage"):
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

            iterations += 1

            if show_progress:
                print(f"  ← Received response (iteration {iterations})")

        # Extract final review from last response if not already set
        if not final_content and response.content:
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            final_content = "\n".join(text_blocks)

        if self.debug:
            print(f"\nDEBUG: Final Review Response")
            print("=" * 80)
            print(f"Review length: {len(final_content)} characters")
            print("\nReview preview:")
            print(final_content[:1000] + "..." if len(final_content) > 1000 else final_content)
            print("=" * 80)

        # Get navigation summary
        nav_summary = (
            self.navigation_tools.get_navigation_summary() if self.navigation_tools else {}
        )

        # Calculate token details using accumulated totals
        token_details = {
            "input_tokens": (
                total_input_tokens if total_input_tokens > 0 else len(initial_context) // 4
            ),
            "output_tokens": (
                total_output_tokens if total_output_tokens > 0 else len(final_content) // 4
            ),
            "total_tokens": 0,
        }

        # Add estimated tokens from navigation if we don't have actual counts
        if total_input_tokens == 0:
            for step in navigation_history:
                if "result_preview" in step:
                    token_details["input_tokens"] += len(str(step["result_preview"])) // 4

        token_details["total_tokens"] = (
            token_details["input_tokens"] + token_details["output_tokens"]
        )

        return {
            "review": final_content,
            "navigation_history": navigation_history,
            "navigation_summary": nav_summary,
            "iterations": iterations,
            "token_details": token_details,
        }

    def format_initial_context(
        self,
        changed_files: Dict[str, str],
        codebase_summary: str,
        diffs: Dict[str, str],
        show_all: bool = False,
        design_doc: Optional[str] = None,
    ) -> str:
        """Format the initial context for Claude.

        Args:
            changed_files: Dictionary of changed files and their status
            codebase_summary: Summary from codebase indexer
            diffs: Dictionary of file diffs
            show_all: Whether to show all issues or just critical ones
            design_doc: Optional project design document content

        Returns:
            Formatted context string
        """
        if show_all:
            # Full review with both critical issues and suggestions
            context_parts = [
                "You are an expert code reviewer. I need you to review uncommitted changes in this codebase.",
                "",
                "IMPORTANT: Categorize all feedback into two severity levels:",
                "1. 🚨 CRITICAL ISSUES - Must be fixed before merging (bugs, security issues, breaking changes)",
                "2. 💡 SUGGESTIONS - Good to have improvements (style, performance, best practices)",
                "",
                "Format your review with clear sections for each severity level.",
                "",
                "## Codebase Overview",
                codebase_summary,
                "",
            ]

            # Add design document if provided
            if design_doc:
                context_parts.extend(
                    [
                        "## Project Design Document",
                        "The following design document provides important context about the project's architecture, conventions, and requirements.",
                        "USE THIS DOCUMENT to understand:",
                        "- Project-specific coding standards and conventions",
                        "- Architecture decisions and design patterns",
                        "- Security requirements and constraints",
                        "- Performance requirements",
                        "- API contracts and interfaces",
                        "",
                        design_doc,
                        "",
                    ]
                )

            context_parts.extend(
                ["## Changed Files", "The following files have uncommitted changes:"]
            )
        else:
            # Critical issues only - compact format for AI agents
            context_parts = [
                "You are an expert code reviewer performing a thorough security and quality review of uncommitted changes.",
                "",
                "Focus on CRITICAL ISSUES that must be fixed before merging:",
                "- Bugs, logic errors, or edge cases that will cause failures",
                "- Security vulnerabilities (injection, XSS, auth bypass, etc.)",
                "- Breaking changes to APIs, interfaces, or contracts",
                "- Data integrity, loss, or corruption risks",
                "- Missing error handling for critical operations",
                "- Performance issues that could cause system degradation",
                "- Incorrect assumptions or implementations",
                "",
                "Output each critical issue in this compact format:",
                "FILE: path/to/file.py",
                "LINE: <line_number>",
                "ISSUE: <clear description of the problem>",
                "FIX: <specific actionable solution>",
                "",
                "Important: Be thorough but only report issues that truly need fixing.",
                "Skip style issues, minor improvements, and nice-to-have suggestions.",
                "",
                "## Codebase Overview",
                codebase_summary,
                "",
            ]

            # Add design document if provided
            if design_doc:
                context_parts.extend(
                    [
                        "## Project Design Document",
                        "The following design document provides important context about the project's architecture, conventions, and requirements.",
                        "USE THIS DOCUMENT to understand:",
                        "- Project-specific coding standards and conventions",
                        "- Architecture decisions and design patterns",
                        "- Security requirements and constraints",
                        "- Performance requirements",
                        "- API contracts and interfaces",
                        "",
                        design_doc,
                        "",
                    ]
                )

            context_parts.extend(
                ["## Changed Files", "The following files have uncommitted changes:"]
            )

        for status, files in changed_files.items():
            if files:
                context_parts.append(f"\n{status.capitalize()}:")
                for file in files:
                    context_parts.append(f"  - {file}")

        if show_all:
            context_parts.extend(
                [
                    "",
                    "## Your Task",
                    "1. Use the navigation tools to explore the changed files and understand the context",
                    "2. Follow imports and check related files as needed",
                    "3. Look for potential issues and categorize them:",
                    "   CRITICAL (🚨):",
                    "   - Bugs or logic errors that will cause failures",
                    "   - Security vulnerabilities",
                    "   - Breaking changes to APIs or contracts",
                    "   - Missing critical error handling",
                    "   - Data loss or corruption risks",
                    "   ",
                    "   SUGGESTIONS (💡):",
                    "   - Code style inconsistencies",
                    "   - Performance optimizations",
                    "   - Missing tests or documentation",
                    "   - Refactoring opportunities",
                    "   - Best practice violations",
                    "4. Provide specific, actionable feedback with clear severity",
                    "",
                    "## Available Tools",
                    "- read_file(filepath): Read any file in the codebase",
                    "- search_symbol(symbol_name): Find where symbols are defined",
                    "- find_usages(symbol_name): Find where symbols are used",
                    "- get_imports(filepath): Get imports from a file",
                    "- get_file_tree(): View project structure",
                    "- search_text(pattern, file_pattern): Search for text patterns",
                    "",
                    "Start by examining the changed files to understand what was modified.",
                ]
            )
        else:
            context_parts.extend(
                [
                    "",
                    "## Your Task",
                    "1. Thoroughly examine all changed files to understand the modifications",
                    "2. Use navigation tools to explore related files and understand the full context:",
                    "   - Follow imports to check dependencies",
                    "   - Find usages to understand impact of changes",
                    "   - Check related files that might be affected",
                    "3. Identify CRITICAL issues that could cause problems:",
                    "   - Runtime errors, crashes, or incorrect behavior",
                    "   - Security vulnerabilities of any kind",
                    "   - Breaking changes that affect other parts of the system",
                    "   - Data integrity or loss issues",
                    "   - Missing error handling for edge cases",
                    "   - Logic errors or incorrect implementations",
                    "4. For each critical issue found, output in this format:",
                    "   FILE: <filepath>",
                    "   LINE: <line_number>",
                    "   ISSUE: <clear description>",
                    "   FIX: <specific solution>",
                    "",
                    "## Available Tools",
                    "- read_file(filepath): Read any file in the codebase",
                    "- search_symbol(symbol_name): Find where symbols are defined",
                    "- find_usages(symbol_name): Find where symbols are used",
                    "- get_imports(filepath): Get imports from a file",
                    "- get_file_tree(): View project structure",
                    "- search_text(pattern, file_pattern): Search for text patterns",
                    "",
                    "Be thorough in your analysis. Check the changed files and their dependencies.",
                    "Focus on finding real issues that need fixing, not style or minor improvements.",
                ]
            )

        # Add the actual diffs so the AI can see what changed
        if diffs:
            context_parts.extend(
                ["", "## Git Diffs", "Here are the actual changes made to each file:", ""]
            )

            for filepath, diff in diffs.items():
                context_parts.extend([f"### {filepath}", "```diff", diff, "```", ""])

        return "\n".join(context_parts)
