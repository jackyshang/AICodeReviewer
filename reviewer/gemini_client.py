"""Gemini API client with tool calling support for code review - New SDK."""

import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

from reviewer.navigation_tools import NavigationTools
from reviewer.rate_limiter import RateLimitManager

# Load environment variables from .env file
load_dotenv()

# Global rate limit manager instance
_rate_limit_manager = RateLimitManager()


class GeminiClient:
    """Client for interacting with Gemini API with navigation tools.
    
    Design Note: Each review mode has its own output format because:
    - AI-generated modes need EVIDENCE field to show hallucinations/stubs
    - Full review mode uses a multi-tier priority format
    - Default/prototype modes use simpler formats
    This intentional differentiation improves review quality for each use case.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-pro", debug: bool = False, enable_rate_limiting: bool = True):
        """Initialize Gemini client.
        
        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var
            model_name: Name of the Gemini model to use
            debug: Enable debug logging of API requests/responses
            enable_rate_limiting: Enable rate limiting for API calls (default: True)
        """
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY environment variable.")
        
        # Initialize client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.chat = None
        self.navigation_tools = None
        self.debug = debug
        self.enable_rate_limiting = enable_rate_limiting
        
        # Get rate limiter for this model
        if self.enable_rate_limiting:
            self.rate_limiter = _rate_limit_manager.get_limiter(model_name)
        
    def setup_navigation_tools(self, nav_tools: NavigationTools):
        """Set up navigation tools for the AI to use.
        
        Args:
            nav_tools: NavigationTools instance
        """
        self.navigation_tools = nav_tools
        
        # Define tools for the new SDK - all functions in one Tool
        self.tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="read_file",
                    description="Read and return the content of a file",
                    parameters={
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path to the file relative to repository root"
                            }
                        },
                        "required": ["filepath"]
                    }
                ),
                types.FunctionDeclaration(
                    name="search_symbol",
                    description="Find where a class, function, or variable is defined",
                    parameters={
                        "type": "object",
                        "properties": {
                            "symbol_name": {
                                "type": "string",
                                "description": "Name of the symbol to search for"
                            }
                        },
                        "required": ["symbol_name"]
                    }
                ),
                types.FunctionDeclaration(
                    name="find_usages",
                    description="Find all places where a symbol is used in the codebase",
                    parameters={
                        "type": "object",
                        "properties": {
                            "symbol_name": {
                                "type": "string",
                                "description": "Name of the symbol to find usages for"
                            }
                        },
                        "required": ["symbol_name"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_imports",
                    description="Get all imports from a specific file",
                    parameters={
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path to the file relative to repository root"
                            }
                        },
                        "required": ["filepath"]
                    }
                ),
                types.FunctionDeclaration(
                    name="get_file_tree",
                    description="Get the project file tree structure",
                    parameters={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                types.FunctionDeclaration(
                    name="search_text",
                    description="Search for text pattern in files",
                    parameters={
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Text or regex pattern to search for"
                            },
                            "file_pattern": {
                                "type": "string",
                                "description": "Optional file pattern to limit search (e.g., '*.py')"
                            }
                        },
                        "required": ["pattern"]
                    }
                )
            ]
        )
        
    def _execute_function(self, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute a navigation tool function.
        
        Args:
            function_name: Name of the function to execute
            args: Arguments for the function
            
        Returns:
            Result from the navigation tool
        """
        if not self.navigation_tools:
            raise ValueError("Navigation tools not set up")
        
        # Map function names to navigation tool methods
        function_map = {
            'read_file': self.navigation_tools.read_file,
            'search_symbol': self.navigation_tools.search_symbol,
            'find_usages': self.navigation_tools.find_usages,
            'get_imports': self.navigation_tools.get_imports,
            'get_file_tree': self.navigation_tools.get_file_tree,
            'search_text': self.navigation_tools.search_text,
        }
        
        if function_name not in function_map:
            raise ValueError(f"Unknown function: {function_name}")
        
        # Call the function with the provided arguments
        func = function_map[function_name]
        return func(**args)
    
    def review_code(self, initial_context: str, max_iterations: int = 20, show_progress: bool = False, show_all: bool = False) -> Dict[str, Any]:
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
        
        # Create a new chat session with tools
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                tools=[self.tool],
                temperature=0.7,
                top_p=0.95,
            )
        )
        
        navigation_history = []
        
        # Initialize token counters
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        
        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: Initial API Request")
            print("="*80)
            print(f"Context length: {len(initial_context)} characters")
            print("\nFull Initial Context Sent to Gemini:")
            print("-" * 80)
            print(initial_context)
            print("-" * 80)
            print("="*80 + "\n")
        
        # Apply rate limiting before sending initial context
        if self.enable_rate_limiting:
            if self.debug:
                print(f"DEBUG: Acquiring rate limit token for {self.model_name}...")
            if not self.rate_limiter.acquire(timeout=30.0):
                raise RuntimeError(f"Rate limit timeout for {self.model_name}. Please try again later.")
            if self.debug:
                print(f"DEBUG: Rate limit token acquired. Available tokens: {self.rate_limiter.available_tokens():.1f}")
        
        # Send initial context
        response = self.chat.send_message(initial_context)
        
        # Accumulate tokens from initial response
        if hasattr(response, 'usage_metadata'):
            total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            total_tokens += getattr(response.usage_metadata, 'total_token_count', 0) or 0
        
        # Handle tool calls iteratively
        iterations = 0
        while iterations < max_iterations:
            # Check if response contains tool calls
            if not hasattr(response, 'function_calls') or not response.function_calls:
                break
            
            tool_calls = response.function_calls
            
            if self.debug:
                print(f"\n🔧 DEBUG: Iteration {iterations + 1} - {len(tool_calls)} function calls")
                for fc in tool_calls:
                    print(f"   - {fc.name}({json.dumps(fc.args, indent=2)})")
            
            # Execute function calls
            function_responses = []
            for fc in tool_calls:
                try:
                    result = self._execute_function(fc.name, fc.args)
                    
                    # Track navigation history
                    navigation_history.append({
                        'function': fc.name,
                        'args': fc.args,
                        'result_preview': str(result)[:200] + '...' if len(str(result)) > 200 else str(result)
                    })
                    
                    function_responses.append({
                        'name': fc.name,
                        'response': {'result': result}
                    })
                    
                    if self.debug:
                        print(f"\n✅ DEBUG: Function Result for {fc.name}")
                        print("-" * 80)
                        result_str = str(result)
                        print(f"Result length: {len(result_str)} characters")
                        if len(result_str) > 1000:
                            print("Result preview (first 1000 chars):")
                            print(result_str[:1000] + "...")
                        else:
                            print("Full result:")
                            print(result_str)
                        print("-" * 80)
                        
                except Exception as e:
                    if self.debug:
                        print(f"\n❌ DEBUG: Error executing {fc.name}: {str(e)}")
                    function_responses.append({
                        'name': fc.name,
                        'response': {'error': str(e)}
                    })
            
            # Send function results back
            # Build parts with function responses
            response_parts = []
            for fr in function_responses:
                response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fr['name'],
                            response=fr['response']
                        )
                    )
                )
            
            if self.debug:
                print(f"\n📤 DEBUG: Sending {len(function_responses)} function results back to Gemini")
            
            # Apply rate limiting before sending function responses
            if self.enable_rate_limiting:
                if self.debug:
                    print(f"DEBUG: Acquiring rate limit token for function response...")
                if not self.rate_limiter.acquire(timeout=30.0):
                    raise RuntimeError(f"Rate limit timeout for {self.model_name}. Please try again later.")
                if self.debug:
                    print(f"DEBUG: Rate limit token acquired. Available tokens: {self.rate_limiter.available_tokens():.1f}")
                
            # Send all function responses as parts
            # Send all responses together in a single message
            response = self.chat.send_message(response_parts)
            
            # Accumulate tokens from this response
            if hasattr(response, 'usage_metadata'):
                total_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                total_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
                total_tokens += getattr(response.usage_metadata, 'total_token_count', 0) or 0
            
            iterations += 1
            
            if show_progress:
                print(f"  ← Received response (iteration {iterations})")
        
        # Extract final review from last response
        final_review = ""
        if hasattr(response, 'text'):
            final_review = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text'):
                            final_review += part.text
        
        # Use accumulated token counts
        token_details = {
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'total_tokens': total_tokens
        }
        
        return {
            'review_content': final_review,
            'navigation_history': navigation_history,
            'iterations': iterations,
            'navigation_summary': {
                'total_files_explored': len([h for h in navigation_history if h['function'] == 'read_file']),
                'symbols_searched': len([h for h in navigation_history if h['function'] in ['search_symbol', 'find_usages']]),
                'total_navigation_calls': len(navigation_history),
            },
            'token_details': token_details
        }
    
    def format_initial_context(self, changed_files: Dict[str, List[str]], codebase_summary: str, 
                             diffs: Dict[str, str], show_all: bool = False, design_doc: Optional[str] = None,
                             story: Optional[str] = None, ai_generated: bool = False, prototype: bool = False) -> str:
        """Format the initial context for code review.
        
        Args:
            changed_files: Dictionary of file status to list of files
            codebase_summary: Summary of codebase structure and symbols
            diffs: Dictionary of file path to diff content
            show_all: Whether to show all issues or just critical ones
            design_doc: Optional design document content for compliance checking
            story: Optional story/purpose context for the changes
            
        Returns:
            Formatted context string
        """
        return self._get_context(changed_files, codebase_summary, diffs, show_all, design_doc, story, ai_generated, prototype)
    
    def _get_context(self, changed_files: Dict[str, List[str]], codebase_summary: str, 
                     diffs: Dict[str, str], show_all: bool = False, design_doc: Optional[str] = None,
                     story: Optional[str] = None, ai_generated: bool = False, prototype: bool = False) -> str:
        """Build the context for the AI model."""
        # Determine which prompt mode to use
        if ai_generated and prototype:
            # Combined mode: AI-generated prototype
            return self._get_ai_prototype_context(changed_files, codebase_summary, diffs, design_doc, story)
        elif ai_generated:
            # AI-generated code review mode
            return self._get_ai_generated_context(changed_files, codebase_summary, diffs, design_doc, story)
        elif prototype:
            # Prototype mode (small-scale, 2-5 users)
            return self._get_prototype_context(changed_files, codebase_summary, diffs, design_doc, story)
        elif show_all:
            # Full review mode with three-tier priority system
            return self._get_full_review_context(changed_files, codebase_summary, diffs, design_doc, story)
        else:
            # Default critical-only mode (for CI/CD)
            return self._get_default_context(changed_files, codebase_summary, diffs, design_doc, story)
    
    def _get_full_review_context(self, changed_files: Dict[str, List[str]], codebase_summary: str,
                                diffs: Dict[str, str], design_doc: Optional[str] = None,
                                story: Optional[str] = None) -> str:
        """Build context for full review mode with three-tier priority system."""
        context_parts = [
            "You are an expert code reviewer providing comprehensive feedback.",
            "",
            "## REVIEW PRIORITIES",
            "Categorize all feedback by priority, focusing on value-based assessment.",
            "",
            "### 🔴 HIGH PRIORITY (Must fix):",
            "1. Development principles violations (if design doc provided)",
            "2. Missing or inadequate tests",
            "3. Critical security vulnerabilities (immediate exploitable risks)",
            "4. Bugs and defects",
            "5. Performance anti-patterns worth fixing",
            "6. Data integrity risks with real impact",
            "",
            "### 🟡 MEDIUM PRIORITY (Should consider):",
            "- Important maintainability issues",
            "- Missing error handling for likely scenarios",
            "- Documentation for complex logic",
            "",
            "### 🟢 DEFER (Note for future):",
            "- Security hardening and defense-in-depth improvements",
            "- Theoretical or low-risk security findings",
            "- Style preferences beyond requirements",
            "- Minor optimizations",
            "- Refactoring opportunities",
            "",
            "## VALUE-BASED ASSESSMENT",
            "When evaluating issues, always consider:",
            "- Will fixing this provide REAL, MEASURABLE value?",
            "- Is the effort proportional to the benefit?",
            "- Is this solving an actual problem or just 'nice to have'?",
            "",
            "## OUTPUT FORMAT",
            "",
            "### 🔴 HIGH PRIORITY ISSUES",
            "**Issue 1: [Title]**",
            "- File: path/to/file.ext (line X)",
            "- Problem: [Clear description]",
            "- Solution: [Specific fix]",
            "- Impact: [Why this matters]",
            "",
            "### 🟡 MEDIUM PRIORITY SUGGESTIONS",
            "**Suggestion 1: [Title]**",
            "- File: path/to/file.ext",
            "- Current: [What exists]",
            "- Better: [Improvement]",
            "- Benefit: [Why consider this]",
            "",
            "### 🟢 DEFERRED ITEMS",
            "**Future Consideration: [Type]**",
            "- Brief note for future sprint",
            "",
            "## Your Review Process",
            "1. Verify test coverage for all changes",
            "2. Check design document compliance",
            "3. Identify bugs and defects",
            "4. Assess security issues:",
            "   - Critical exploitable flaws → HIGH priority",
            "   - Hardening improvements → DEFER for security sprint",
            "5. Evaluate performance and data integrity (value-based)",
            "6. Note maintainability and code quality issues",
            "7. Suggest improvements where beneficial",
            "",
            "Remember: Focus on pragmatic, high-value feedback."
        ]
        
        # Add common sections
        self._add_common_context_sections(context_parts, codebase_summary, changed_files, 
                                          design_doc, story, diffs, "full")
        
        return '\n'.join(context_parts)
    
    def _get_default_context(self, changed_files: Dict[str, List[str]], codebase_summary: str,
                           diffs: Dict[str, str], design_doc: Optional[str] = None,
                           story: Optional[str] = None) -> str:
        """Build context for default critical-only mode (CI/CD)."""
        context_parts = [
            "You are an expert code reviewer focused on identifying issues that must be fixed before merging.",
            "",
            "## VALUE-BASED REVIEW APPROACH",
            "Focus on HIGH-VALUE fixes that provide real benefits. Avoid superficial improvements that look good on paper but provide little actual value.",
            "",
            "## HIGH PRIORITY ISSUES (Must fix before merge):",
            "",
            "1. **DEVELOPMENT PRINCIPLES COMPLIANCE** (if design document provided)",
            "   - Violations of documented architecture patterns",
            "   - Deviations from required coding standards",
            "   - Breaking established conventions",
            "",
            "2. **TEST COVERAGE VERIFICATION**",
            "   - Every functional change MUST have tests",
            "   - Navigate to test files and verify they actually test the changes",
            "   - Tests must be meaningful, not just placeholder assertions",
            "",
            "3. **CRITICAL SECURITY VULNERABILITIES**",
            "   - Injection flaws (SQL, Command, LDAP, XPath, etc.)",
            "   - Authentication or authorization bypass",
            "   - Remote Code Execution (RCE)",
            "   - Exposed secrets, credentials, or API keys",
            "   - Unsafe deserialization",
            "",
            "4. **BUGS AND DEFECTS**",
            "   - Logic errors causing incorrect behavior",
            "   - Runtime errors or crashes",
            "   - Incorrect assumptions or implementations",
            "   - Breaking changes to existing functionality",
            "",
            "5. **PERFORMANCE ANTI-PATTERNS** (only if worth fixing)",
            "   HIGH priority only if:",
            "   - Fundamental algorithmic issues (O(n²) when O(n) is available)",
            "   - Loading entire datasets unnecessarily",
            "   - N+1 query problems",
            "   - Blocking I/O that should be async",
            "   NOT high priority:",
            "   - Micro-optimizations with negligible impact",
            "   - Theoretical improvements without benchmarks",
            "",
            "6. **DATA INTEGRITY RISKS** (with real consequences)",
            "   HIGH priority only if:",
            "   - Race conditions causing actual data corruption",
            "   - Missing transactions for critical operations",
            "   - Improper data validation leading to corruption",
            "   NOT high priority:",
            "   - Theoretical edge cases with minimal real-world impact",
            "",
            "## OUTPUT FORMAT",
            "For each HIGH priority issue:",
            "FILE: path/to/file.ext",
            "LINE: <line_number>",
            "ISSUE: <clear description of the problem>",
            "FIX: <specific, actionable solution>",
            "",
            "## IMPORTANT INSTRUCTIONS",
            "- Only report issues that MUST be fixed before merge",
            "- Skip style issues, minor improvements, and theoretical problems",
            "- For performance/data issues, consider effort vs. benefit",
            "- Be pragmatic, not academic",
            "",
            "## Your Review Process",
            "1. **First**: Verify compliance with design document (if provided)",
            "   - Check each change against documented principles",
            "   - Flag any architectural violations",
            "",
            "2. **Second**: Check if tests exist for all functional changes",
            "   - Use find_usages() to locate test files",
            "   - Use read_file() to verify test quality",
            "   - Flag missing or inadequate tests",
            "",
            "3. **Third**: Look for critical security vulnerabilities",
            "   - Focus on immediately exploitable issues",
            "   - Check for exposed secrets or credentials",
            "",
            "4. **Fourth**: Look for bugs and logical errors",
            "   - Trace through code paths",
            "   - Consider edge cases",
            "   - Verify assumptions",
            "",
            "5. **Fifth**: Identify HIGH-VALUE performance/data issues only",
            "   - Must be actual anti-patterns, not preferences",
            "   - Fix must be worth the effort",
            "",
            "Start by examining the changed files and their corresponding tests."
        ]
        
        # Add common sections
        self._add_common_context_sections(context_parts, codebase_summary, changed_files, 
                                          design_doc, story, diffs, "default")
        
        return '\n'.join(context_parts)
    
    def _get_ai_generated_context(self, changed_files: Dict[str, List[str]], codebase_summary: str,
                                  diffs: Dict[str, str], design_doc: Optional[str] = None,
                                  story: Optional[str] = None) -> str:
        """Build context for reviewing AI-generated code.
        
        Note: This mode uses a different output format that includes EVIDENCE field
        to show specific code demonstrating hallucinations or stub implementations.
        """
        context_parts = [
            "You are an expert code reviewer specializing in AI-generated code quality assessment.",
            "",
            "## CONTEXT",
            "This code was generated by an AI coding assistant. AI-generated code often has specific patterns of issues that differ from human-written code.",
            "",
            "## REVIEW PRIORITIES",
            "",
            "### 🔴 CRITICAL ISSUES (Must fix before proceeding)",
            "",
            "1. **IMPLEMENTATION VERIFICATION**",
            "   - Verify ALL claimed features actually exist and work",
            "   - Check for stub functions that just return placeholder values",
            "   - Identify functions that only print/log but don't implement logic",
            "   - Find methods that raise NotImplementedError or just pass",
            "   Example: \"Function claims to validate email but only returns True\"",
            "",
            "2. **HALLUCINATION DETECTION**",
            "   - Imports for modules that don't exist in the codebase",
            "   - Function calls to undefined functions",
            "   - Usage of undefined variables or attributes",
            "   - References to files/configs that don't exist",
            "   Example: \"Imports 'from utils.validator import EmailValidator' but utils/validator.py doesn't exist\"",
            "",
            "3. **TEST REALITY CHECK**",
            "   - Tests that don't actually test the feature (e.g., assert True)",
            "   - Test names that don't match what they test",
            "   - Missing assertions in test functions",
            "   - Tests that pass even when the feature is broken",
            "   Example: \"test_user_authentication() only checks if function exists, not if auth works\"",
            "",
            "4. **INCOMPLETE IMPLEMENTATION**",
            "   - TODO/FIXME comments in critical code paths",
            "   - Partial implementations that break core functionality",
            "   - Exception handlers that silently swallow errors",
            "   - Missing required functionality mentioned in comments/docstrings",
            "   Example: \"save_to_database() has TODO comment and doesn't actually save\"",
            "",
            "### 🟡 MEDIUM PRIORITY (Should fix)",
            "",
            "1. **OVER-ENGINEERING**",
            "   - Unnecessary abstraction layers for simple tasks",
            "   - Complex design patterns where simple functions would suffice",
            "   - Multiple classes/interfaces for basic operations",
            "   - Overly generic solutions for specific problems",
            "   Example: \"Created Factory + Builder + Strategy pattern for simple config loading\"",
            "",
            "2. **ERROR HANDLING GAPS**",
            "   - External API calls without try-catch",
            "   - File operations without error handling",
            "   - Missing validation for user inputs",
            "   - Errors only logged but not properly handled",
            "",
            "3. **INTEGRATION ISSUES**",
            "   - New code doesn't properly integrate with existing patterns",
            "   - Inconsistent error handling compared to rest of codebase",
            "   - Different naming conventions or styles",
            "",
            "4. **HARDCODED VALUES**",
            "   - API keys, URLs, or paths hardcoded instead of config",
            "   - Test data mixed with production code",
            "   - Magic numbers without explanation",
            "",
            "### 🟢 LOW PRIORITY (Note for later)",
            "",
            "1. **Code Organization**",
            "   - Could be refactored for clarity",
            "   - Duplicate code that could be extracted",
            "",
            "2. **Documentation**",
            "   - Missing docstrings for complex functions",
            "   - Outdated comments",
            "",
            "## REVIEW PROCESS",
            "",
            "1. First, check if the AI's implementation matches its claims",
            "2. Verify all imports and dependencies exist",
            "3. Check test quality - do they actually verify functionality?",
            "4. Look for incomplete implementations (TODO, FIXME, NotImplementedError)",
            "5. Assess complexity - is the solution appropriately simple for the problem?",
            "6. Verify error handling for external operations",
            "",
            "## OUTPUT FORMAT",
            "",
            "For each issue found:",
            "FILE: path/to/file.ext",
            "LINE: <line_number>",
            "ISSUE: <what is wrong>",
            "EVIDENCE: <specific code showing the problem>",
            "FIX: <how to fix it>",
            ""
        ]
        
        # Add common sections
        self._add_common_context_sections(context_parts, codebase_summary, changed_files, 
                                          design_doc, story, diffs, "ai_generated")
        
        return '\n'.join(context_parts)
    
    def _get_prototype_context(self, changed_files: Dict[str, List[str]], codebase_summary: str,
                              diffs: Dict[str, str], design_doc: Optional[str] = None,
                              story: Optional[str] = None) -> str:
        """Build context for reviewing prototype code (2-5 users)."""
        context_parts = [
            "You are reviewing code for a small-scale prototype (2-5 users).",
            "",
            "## CONTEXT",
            "This is prototype code that will later evolve into production code. It should maintain good practices but with adjusted priorities for small-scale local use.",
            "",
            "## ADJUSTED PRIORITIES FOR SMALL-SCALE PROTOTYPES",
            "",
            "### 🔴 CRITICAL ISSUES (Must fix)",
            "- Code that doesn't work or crashes",
            "- Logic errors causing incorrect behavior",
            "- Missing core functionality",
            "- Poor code structure that will make production migration difficult",
            "- Over-engineering that adds unnecessary complexity",
            "- Broken imports or dependencies",
            "",
            "### 🟡 MEDIUM PRIORITY (Should consider)",
            "- Missing error handling for common failure cases",
            "- Hardcoded values that should be configurable",
            "- Code organization issues that hurt maintainability",
            "- Lack of basic input validation (not for security, but for functionality)",
            "- Missing logging for debugging",
            "- Test coverage for core features",
            "",
            "### 🟢 DEFERRED (Not critical for 2-5 users)",
            "- Security hardening (advanced auth, encryption, rate limiting)",
            "- Scalability optimizations (caching, connection pooling)",
            "- Performance optimizations for large datasets",
            "- Comprehensive security validations",
            "- DDoS protection, CSRF tokens",
            "- Advanced monitoring and metrics",
            "",
            "## KEY PRINCIPLES",
            "- Write clean, maintainable code that can evolve into production",
            "- Follow best practices for code structure and organization",
            "- Handle errors gracefully for good user experience",
            "- Keep it simple - avoid over-engineering",
            "- Security basics are OK, but not enterprise-grade security",
            "",
            "Focus on: Clean, working code that demonstrates functionality and can be evolved.",
            "",
            "## OUTPUT FORMAT",
            "",
            "For each issue:",
            "FILE: path/to/file.ext",
            "LINE: <line_number>",
            "ISSUE: <clear description of the problem>",
            "FIX: <specific, actionable solution>",
            ""
        ]
        
        # Add common sections
        self._add_common_context_sections(context_parts, codebase_summary, changed_files, 
                                          design_doc, story, diffs, "prototype")
        
        return '\n'.join(context_parts)
    
    def _get_ai_prototype_context(self, changed_files: Dict[str, List[str]], codebase_summary: str,
                                  diffs: Dict[str, str], design_doc: Optional[str] = None,
                                  story: Optional[str] = None) -> str:
        """Build context for reviewing AI-generated prototype code.
        
        Note: Like AI-generated mode, includes EVIDENCE field for showing specific
        problematic code, but with prototype-specific priorities.
        """
        context_parts = [
            "You are reviewing AI-generated code for a small-scale prototype (2-5 users).",
            "",
            "## CONTEXT",
            "This code was generated by an AI assistant for a prototype that will evolve into production code.",
            "",
            "## REVIEW PRIORITIES FOR AI-GENERATED PROTOTYPES",
            "",
            "### 🔴 CRITICAL ISSUES (Must fix)",
            "",
            "1. **AI IMPLEMENTATION VERIFICATION**",
            "   - Verify ALL claimed features actually work",
            "   - Check for stub functions that just return placeholders",
            "   - Ensure the AI didn't just write TODO comments",
            "   - Functions that only print/log but don't implement logic",
            "",
            "2. **HALLUCINATION CHECK**",
            "   - Imports for modules that don't exist",
            "   - Functions called but not defined",
            "   - Files/configs referenced but not created",
            "   - Made-up library functions or APIs",
            "",
            "3. **CODE QUALITY FOR FUTURE PRODUCTION**",
            "   - Poor structure that will be hard to evolve",
            "   - Over-engineered solutions for simple problems",
            "   - Missing error handling for common cases",
            "   - Broken core functionality",
            "",
            "4. **TEST REALITY CHECK**",
            "   - Tests that don't actually test (assert True)",
            "   - Missing tests for core features",
            "   - Test names that don't match what they test",
            "",
            "### 🟡 MEDIUM PRIORITY",
            "",
            "1. **MAINTAINABILITY ISSUES**",
            "   - Hardcoded values that should be configurable",
            "   - Poor naming that makes code hard to understand",
            "   - Missing logging for debugging",
            "   - Inconsistent patterns within the codebase",
            "",
            "2. **BASIC BEST PRACTICES**",
            "   - Input validation for functionality (not security)",
            "   - Reasonable error messages for users",
            "   - Code organization and file structure",
            "",
            "### 🟢 DEFERRED (Not critical for prototypes)",
            "",
            "- Enterprise security features (OAuth, JWT, encryption)",
            "- Scalability concerns (caching, load balancing)",
            "- Performance optimizations for large scale",
            "- Comprehensive security validations",
            "- Production monitoring and metrics",
            "",
            "## REVIEW PROCESS",
            "1. Verify the AI actually implemented claimed features",
            "2. Check all imports and dependencies exist",
            "3. Ensure tests are real, not placeholders",
            "4. Assess if complexity is appropriate",
            "5. Verify basic error handling exists",
            "6. Check code structure supports future evolution",
            "",
            "## KEY QUESTIONS",
            "1. Did the AI actually implement what it claimed?",
            "2. Is the code structured well enough to evolve into production?",
            "3. Are there hallucinations or made-up functions?",
            "4. Is it over-engineered for the problem at hand?",
            "5. Will this work reliably for 2-5 users?",
            "",
            "## OUTPUT FORMAT",
            "",
            "For each issue:",
            "FILE: path/to/file.ext",
            "LINE: <line_number>",
            "ISSUE: <what is wrong>",
            "EVIDENCE: <specific code showing the problem>",
            "FIX: <how to fix it>",
            ""
        ]
        
        # Add common sections
        self._add_common_context_sections(context_parts, codebase_summary, changed_files, 
                                          design_doc, story, diffs, "ai_prototype")
        
        return '\n'.join(context_parts)
    
    def _add_common_context_sections(self, context_parts: List[str], codebase_summary: str,
                                    changed_files: Dict[str, List[str]], design_doc: Optional[str],
                                    story: Optional[str], diffs: Dict[str, str], mode: str) -> None:
        """Add common context sections to the prompt."""
        # Add codebase overview
        context_parts.extend([
            "## Codebase Overview",
            codebase_summary,
            ""
        ])
        
        # Add design document if provided
        if design_doc:
            context_parts.extend([
                "## Project Design Document (MANDATORY COMPLIANCE)",
                "⚠️ The following principles are MANDATORY and violations are HIGH priority issues:",
                "",
                design_doc,
                ""
            ])
        
        # Add story/purpose context if provided
        if story:
            context_parts.extend([
                "## Story/Change Context",
                "🎯 The following describes the purpose and intent of these changes:",
                "",
                story,
                "",
                "Use this context to:",
                "- Understand the intended functionality and design decisions",
                "- Distinguish between intentional choices and actual issues",
                "- Provide more relevant and targeted feedback",
                "- Avoid suggesting changes that contradict the stated purpose",
                ""
            ])
        
        # Add changed files
        context_parts.extend([
            "## Changed Files",
            "The following files have uncommitted changes:"
        ])
        
        for status, files in changed_files.items():
            if files:
                context_parts.append(f"\n{status.capitalize()}:")
                for file in files:
                    context_parts.append(f"  - {file}")
        
        # Add navigation strategy based on mode
        if mode == "ai_generated" or mode == "ai_prototype":
            context_parts.extend([
                "",
                "## NAVIGATION STRATEGY FOR AI CODE",
                "1. For each claimed feature, navigate to its implementation",
                "2. Check test files - read the actual test code, not just file names",
                "3. Use search_symbol() to verify imported modules exist",
                "4. Use find_usages() to ensure functions are actually called",
                "5. Look for TODO/FIXME patterns across the codebase",
                "6. Analyze complexity of critical functions:",
                "   - Count abstraction layers (classes, interfaces, factories)",
                "   - Check cyclomatic complexity (nested conditions, loops)",
                "   - Identify unnecessary indirection or wrapper functions",
                "   - Look for simple operations wrapped in complex patterns",
                ""
            ])
        
        # Add available tools
        context_parts.extend([
            "## Available Tools",
            "- read_file(filepath): Read any file in the codebase",
            "- search_symbol(symbol_name): Find where symbols are defined",
            "- find_usages(symbol_name): Find where symbols are used",
            "- get_imports(filepath): Get imports from a file",
            "- get_file_tree(): View project structure",
            "- search_text(pattern, file_pattern): Search for text patterns",
            ""
        ])
        
        # Add the actual diffs
        if diffs:
            context_parts.extend([
                "## Git Diffs",
                "Here are the actual changes made to each file:",
                ""
            ])
            
            for filepath, diff in diffs.items():
                context_parts.extend([
                    f"### {filepath}",
                    "```diff",
                    diff,
                    "```",
                    ""
                ])