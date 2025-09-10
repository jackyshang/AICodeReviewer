"""Command-line interface for the LLM Review tool."""

import os
import re
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

import click
import yaml
from rich.console import Console
import requests
from requests.exceptions import ConnectionError, RequestException

from reviewer.codebase_indexer import CodebaseIndexer
from reviewer.claude_client import ClaudeClient
from reviewer.gemini_client import GeminiClient
from reviewer.git_operations import GitOperations
from reviewer.navigation_tools import NavigationTools
from reviewer.review_formatter import ReviewFormatter


console = Console()

# Default service configuration
SERVICE_URL = os.environ.get("REVIEWER_SERVICE_URL", "http://localhost:8765")
SERVICE_PLIST_NAME = "com.reviewer.api"
SERVICE_LOG_PATH = "/tmp/reviewer.log"
SERVICE_ERROR_LOG_PATH = "/tmp/reviewer.error.log"


def check_service_available() -> bool:
    """Check if the review service is running."""
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=0.5)
        return response.status_code == 200
    except:
        return False


def _parse_ps_etime(etime_str: str) -> str:
    """Parse ps etime output and convert to human-readable format.
    
    ps etime can be in various formats:
    - MM:SS (minutes:seconds)
    - HH:MM:SS (hours:minutes:seconds)  
    - DD-HH:MM:SS (days-hours:minutes:seconds)
    - DDDD-HH:MM:SS (for very long uptimes)
    """
    try:
        # Strip whitespace
        etime_str = etime_str.strip()
        
        # Pattern for DD-HH:MM:SS or DDDD-HH:MM:SS
        days_pattern = r'^(\d+)-(\d{1,2}):(\d{2}):(\d{2})$'
        days_match = re.match(days_pattern, etime_str)
        if days_match:
            days, hours, minutes, seconds = days_match.groups()
            days, hours, minutes = int(days), int(hours), int(minutes)
            if days > 0:
                if hours > 0:
                    return f"{days} days, {hours} hours"
                else:
                    return f"{days} days"
            elif hours > 0:
                return f"{hours} hours, {minutes} minutes" if minutes > 0 else f"{hours} hours"
            else:
                return f"{minutes} minutes"
        
        # Pattern for HH:MM:SS
        hours_pattern = r'^(\d{1,2}):(\d{2}):(\d{2})$'
        hours_match = re.match(hours_pattern, etime_str)
        if hours_match:
            hours, minutes, seconds = hours_match.groups()
            hours, minutes = int(hours), int(minutes)
            if hours > 0:
                return f"{hours} hours, {minutes} minutes" if minutes > 0 else f"{hours} hours"
            else:
                return f"{minutes} minutes"
        
        # Pattern for MM:SS
        minutes_pattern = r'^(\d{1,2}):(\d{2})$'
        minutes_match = re.match(minutes_pattern, etime_str)
        if minutes_match:
            minutes, seconds = minutes_match.groups()
            minutes = int(minutes)
            return f"{minutes} minutes" if minutes > 0 else "less than 1 minute"
        
        # If no patterns match, return the original string
        return etime_str
        
    except (ValueError, AttributeError):
        return "unknown"


def list_active_sessions():
    """List all active review sessions from the service."""
    formatter = ReviewFormatter()
    
    if not check_service_available():
        formatter.print_warning("Review service is not running. Session persistence is not available.")
        formatter.print_info("To start the service: python -m reviewer.service")
        return
    
    try:
        response = requests.get(f"{SERVICE_URL}/sessions")
        if response.status_code == 200:
            data = response.json()
            sessions = data.get("sessions", [])
            
            if not sessions:
                formatter.print_info("No active review sessions.")
                return
            
            formatter.print_info(f"Active review sessions ({len(sessions)}):")
            for session in sessions:
                console.print(f"  • {session['name']:20} (iteration {session['iteration']}, last: {session['last_reviewed']})")
        else:
            formatter.print_error("Failed to retrieve sessions")
    except Exception as e:
        formatter.print_error(f"Error listing sessions: {str(e)}")


def _print_recent_errors(lines: int = 5):
    """Print recent error log entries."""
    try:
        with open(SERVICE_ERROR_LOG_PATH, "r") as f:
            log_lines = f.readlines()
            for line in log_lines[-lines:]:
                console.print(f"  {line.rstrip()}")
    except FileNotFoundError:
        console.print("  No error log found")
    except Exception as e:
        console.print(f"  Error reading log: {e}")


class SessionAwareGeminiClient(GeminiClient):
    """Wrapper for GeminiClient that uses the review service for persistence."""
    
    def __init__(self, session_name: str, service_url: str = SERVICE_URL, **kwargs):
        # Don't initialize parent yet - we'll use the service's client
        self.session_name = session_name
        self.service_url = service_url
        self.kwargs = kwargs
        self.is_new_session = None
        
    def setup_navigation_tools(self, nav_tools: NavigationTools):
        """Store navigation tools for later use."""
        self.nav_tools = nav_tools
        
    def format_initial_context(self, changed_files: Dict[str, list], codebase_summary: str,
                             diffs: Dict[str, str], show_all: bool = False, design_doc: Optional[str] = None,
                             story: Optional[str] = None, ai_generated: bool = False, prototype: bool = False) -> str:
        """Store context data and return formatted context."""
        # Store data for later use in review_code
        self.changed_files = changed_files
        self.codebase_summary = codebase_summary
        self.diffs = diffs
        self.show_all = show_all
        
        # For now, just return a placeholder - the service will build the actual context
        return "Session-based review"
    
    def review_code(self, initial_context: str, max_iterations: int = 20,
                    show_progress: bool = False, show_all: bool = False) -> Dict[str, Any]:
        """Perform review using the service for persistence."""
        formatter = ReviewFormatter()
        
        # Prepare request
        request_data = {
            "session_name": self.session_name,
            "project_root": str(self.nav_tools.repo_path),
            "initial_context": initial_context,
            "codebase_summary": getattr(self, 'codebase_summary', ''),
            "changed_files": getattr(self, 'changed_files', {}),
            "diffs": getattr(self, 'diffs', {}),
            "show_all": show_all or getattr(self, 'show_all', False),
            "max_iterations": max_iterations,
            "show_progress": show_progress,
            "debug": self.kwargs.get('debug', False),
            "model_name": self.kwargs.get('model_name', 'gemini-2.5-pro'),
            "ai_generated": self.kwargs.get('ai_generated', False),
            "prototype": self.kwargs.get('prototype', False),
            "design_doc": self.kwargs.get('design_doc'),
            "story": self.kwargs.get('story')
        }
        
        # Call service
        try:
            response = requests.post(f"{self.service_url}/review", json=request_data)
            if response.status_code == 200:
                result = response.json()
                
                # Display session info
                session_info = result['session_info']
                if session_info['status'] == 'new':
                    formatter.print_info(f"🆕 Starting NEW review session: {session_info['name']}")
                    console.print("[dim]🤖 Creating fresh Gemini chat instance[/dim]")
                else:
                    formatter.print_info(f"🔄 CONTINUING review session: {session_info['name']} (iteration {session_info['iteration']})")
                    console.print(f"[dim]🧠 Using existing Gemini chat with full conversation history[/dim]")
                    console.print(f"[dim]📅 Last reviewed: {self._format_time_ago(session_info['last_reviewed'])}[/dim]")
                    console.print(f"[dim]💬 Conversation history: {session_info['chat_messages_count']} messages[/dim]")
                    if session_info.get('previous_issues_count'):
                        console.print(f"[dim]📋 Previous issues: {session_info['previous_issues_count']}[/dim]")
                
                console.print()  # Add spacing
                
                # Return the review result in expected format
                return result['review_result']
            else:
                raise Exception(f"Service returned {response.status_code}: {response.text}")
        except ConnectionError:
            formatter.print_error("Could not connect to review service. Falling back to standard mode.")
            # Return None to signal fallback is needed
            return None
        except Exception as e:
            formatter.print_error(f"Service error: {str(e)}")
            raise
    
    def _format_time_ago(self, timestamp: str) -> str:
        """Format ISO timestamp as human-readable time ago."""
        from datetime import datetime
        
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


def manage_service(command: str):
    """Manage the Reviewer Service.
    
    Args:
        command: One of 'status', 'restart', 'logs', 'stop'
    """
    import subprocess
    
    formatter = ReviewFormatter()
    
    # Check platform compatibility
    if sys.platform != "darwin":
        formatter.print_error("Service management is only available on macOS.")
        formatter.print_info("For other platforms, run the service manually: python -m reviewer.service")
        return
    
    # Use module constants
    service_name = SERVICE_PLIST_NAME
    service_url = SERVICE_URL
    
    if command == "status":
        try:
            # Check if service is loaded
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                check=False
            )
            service_loaded = service_name in result.stdout
            is_running = check_service_available()
            
            # Get version from package
            try:
                from importlib.metadata import version as get_version
                version = get_version("reviewer")
            except ImportError:
                # Fallback for Python < 3.8
                try:
                    import pkg_resources
                    version = pkg_resources.get_distribution("reviewer").version
                except:
                    version = "unknown"
            except:
                version = "unknown"
            
            # Calculate uptime if service is running
            uptime_str = "unknown"
            if is_running:
                try:
                    response = requests.get(f"{service_url}/health", timeout=2)
                    if response.status_code == 200:
                        health_data = response.json()
                        # Try to get uptime from health endpoint
                        if 'uptime' in health_data:
                            uptime_seconds = health_data['uptime']
                            if uptime_seconds < 60:
                                uptime_str = f"{int(uptime_seconds)} seconds"
                            elif uptime_seconds < 3600:
                                uptime_str = f"{int(uptime_seconds // 60)} minutes"
                            else:
                                hours = int(uptime_seconds // 3600)
                                minutes = int((uptime_seconds % 3600) // 60)
                                uptime_str = f"{hours} hours, {minutes} minutes" if minutes > 0 else f"{hours} hours"
                        else:
                            # Fallback: try to get process start time via launchctl
                            ps_result = subprocess.run(
                                ["ps", "-eo", "pid,etime,comm"], 
                                capture_output=True, 
                                text=True, 
                                check=False
                            )
                            # Look for python process running reviewer.service
                            for line in ps_result.stdout.split('\n'):
                                if 'reviewer.service' in line:
                                    parts = line.split()
                                    if len(parts) >= 2:
                                        raw_etime = parts[1]
                                        uptime_str = _parse_ps_etime(raw_etime)
                                    break
                except RequestException:
                    # Failed to get service health - service may be starting up
                    pass
                except (ValueError, KeyError):
                    # Invalid health response format
                    pass
            
            # Display status in builder format
            console.print(f"Installed: {'✓ Yes' if service_loaded else '✗ No'}")
            console.print(f"Running:   {'✓ Yes' if is_running else '✗ No'}")
            console.print(f"Healthy:   {'✓ Yes' if is_running else '✗ No'}")
            console.print(f"Uptime:    {uptime_str}")
            console.print(f"Version:   {version}")
            
            # Show additional info if running
            if is_running:
                try:
                    response = requests.get(f"{service_url}/health", timeout=2)
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get('active_sessions', 0) > 0:
                            console.print(f"Sessions:  {health_data['active_sessions']} active")
                except RequestException:
                    # Service may be starting up or having connectivity issues
                    pass
                except (ValueError, KeyError):
                    # Invalid JSON response
                    pass
            
            # Show error diagnostics if service is loaded but not responding
            if service_loaded and not is_running:
                console.print()
                console.print("Recent errors:")
                _print_recent_errors()
            
            # Show installation hint if not loaded
            if not service_loaded:
                console.print()
                console.print("To install: ./install-service.sh")
                
        except subprocess.CalledProcessError as e:
            formatter.print_error(f"Failed to check service status: {e}")
        except FileNotFoundError:
            formatter.print_error("`launchctl` command not found. Is this macOS?")
        except Exception as e:
            formatter.print_error(f"Unexpected error checking service status: {e}")
    
    elif command == "restart":
        formatter.print_info("🔄 Restarting Reviewer Service...")
        try:
            # Stop the service
            subprocess.run(["launchctl", "stop", service_name], check=False)
            
            # Wait for service to stop (up to 5 seconds)
            console.print("⏳ Waiting for service to stop...")
            for i in range(5):
                if not check_service_available():
                    break
                time.sleep(1)
            else:
                formatter.print_warning("⚠️  Service may not have stopped completely")
            
            # Start the service
            subprocess.run(["launchctl", "start", service_name], check=False)
            
            # Wait for service to start (up to 10 seconds)
            console.print("⏳ Waiting for service to start...")
            for i in range(10):
                if check_service_available():
                    formatter.print_success("✅ Service restarted successfully")
                    return
                time.sleep(1)
            
            formatter.print_error("❌ Service failed to start within 10 seconds")
            formatter.print_info(f"Check logs: tail -f {SERVICE_ERROR_LOG_PATH}")
        except subprocess.CalledProcessError as e:
            formatter.print_error(f"Failed to restart service: {e}")
        except FileNotFoundError:
            formatter.print_error("`launchctl` command not found. Is this macOS?")
        except Exception as e:
            formatter.print_error(f"Unexpected error restarting service: {e}")
    
    elif command == "logs":
        formatter.print_info("📜 Reviewer Service Logs (Ctrl+C to exit):")
        console.print("=" * 44)
        try:
            # Use subprocess.call to allow user to see output and use Ctrl+C
            subprocess.call(["tail", "-f", SERVICE_LOG_PATH])
        except KeyboardInterrupt:
            console.print()  # Clean exit on Ctrl+C
        except FileNotFoundError:
            formatter.print_error(f"Log file not found: {SERVICE_LOG_PATH}")
        except PermissionError:
            formatter.print_error(f"Permission denied reading log file: {SERVICE_LOG_PATH}")
        except Exception as e:
            formatter.print_error(f"Unexpected error reading logs: {e}")
    
    elif command == "stop":
        formatter.print_info("⏹  Stopping Reviewer Service...")
        try:
            subprocess.run(["launchctl", "stop", service_name], check=True)
            formatter.print_success("✅ Service stopped")
        except subprocess.CalledProcessError as e:
            formatter.print_error(f"Failed to stop service: {e}")
        except FileNotFoundError:
            formatter.print_error("`launchctl` command not found. Is this macOS?")
        except Exception as e:
            formatter.print_error(f"Unexpected error stopping service: {e}")


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from .reviewer.yaml file.

    Args:
        config_path: Optional path to config file

    Returns:
        Configuration dictionary
    """
    default_config = {
        "review": {
            "provider": "gemini-2.5-pro",  # Pro by default for quality
            "mode": "ai_navigation",
            "navigation": {"max_files_per_review": 50, "max_depth": 10, "timeout_seconds": 300},
            "output": {
                "format": "markdown",
                "show_navigation_path": True,
                "show_token_usage": True,
                "show_cost": True,
            },
        }
    }

    # Look for config file
    if not config_path:
        # Try current directory first, then parent directories
        current = Path.cwd()
        while current != current.parent:
            potential_config = current / ".reviewer.yaml"
            if potential_config.exists():
                config_path = potential_config
                break
            current = current.parent

    if config_path and config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
            # Merge with defaults
            return {**default_config, **user_config}
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")

    return default_config


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Reviewer CLI - AI-powered code review tool.
    
    \b
    COMMANDS:
      review        Review uncommitted git changes (default)
      service       Manage the Reviewer API service  
      list-sessions List all active review sessions
      
    \b
    EXAMPLES:
      reviewer                                    # Review current changes
      reviewer review "Add user authentication"  # Review with story context
      reviewer service status                    # Check service status
      reviewer list-sessions                     # List active sessions
    """
    # If no subcommand was invoked, run the default review
    if ctx.invoked_subcommand is None:
        ctx.invoke(review_command)


@main.command("review")
@click.argument("story", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode (show API requests/responses)")
@click.option("--output-file", "-o", type=click.Path(), help="Save review to markdown file")
@click.option("--include-unchanged", is_flag=True, help="Include unchanged files for context")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
@click.option("--no-spinner", is_flag=True, help="Disable progress spinner")
@click.option(
    "--fast",
    is_flag=True,
    help="Use Gemini 2.5 Flash for faster analysis (default: Pro for quality)",
)
@click.option(
    "--full",
    "-f",
    is_flag=True,
    help="Show all issues including suggestions (default: critical only)",
)
@click.option(
    "--human",
    is_flag=True,
    help="Human-readable format with colors and formatting (default: compact for AI)",
)
@click.option(
    "--design-doc",
    "-D",
    type=click.Path(exists=True),
    help="Path to project design document (default: README.md in repo root)",
)
@click.option("--claude", is_flag=True, help="[DISABLED] Use Claude API instead of Gemini")
@click.option(
    "--ai-generated",
    is_flag=True,
    help="Review mode for AI-generated code (detects hallucinations, incomplete implementations)",
)
@click.option(
    "--prototype",
    is_flag=True,
    help="Prototype mode: deprioritizes security issues for local development",
)
@click.option(
    "--session-name",
    "-s",
    help="Named session for continuous review (maintains conversation history)",
)
@click.option(
    "--no-session",
    is_flag=True,
    help="Disable session persistence even if service is available",
)
@click.option(
    "--no-rate-limit",
    is_flag=True,
    help="Disable rate limiting for API calls (use with caution)",
)
def review_command(
    story: Optional[str],
    verbose: bool,
    debug: bool,
    output_file: Optional[str],
    include_unchanged: bool,
    config: Optional[str],
    no_spinner: bool,
    fast: bool,
    full: bool,
    human: bool,
    design_doc: Optional[str],
    claude: bool,
    ai_generated: bool,
    prototype: bool,
    session_name: Optional[str],
    no_session: bool,
    no_rate_limit: bool,
):
    """AI-powered code review for your uncommitted changes.

    \b
    STORY: Optional story/purpose context for the changes. Can be either:
      - Direct text describing the changes
      - Path to a file containing the story context (e.g., JIRA ticket)

    \b
    Default behavior:
    - Shows only CRITICAL issues (bugs, security, breaking changes)
    - Compact output format optimized for AI agents
    - Uses Gemini 2.5 Pro for quality analysis
    - Automatically uses README.md as design context if present

    \b
    EXAMPLES:
      # Critical issues only, compact format (default)
      reviewer

      # With story context
      reviewer "Implement JWT authentication for user login"

      # With story from file
      reviewer ./stories/JIRA-123.md

      # Show all issues including suggestions
      reviewer --full

      # Human-readable format with colors
      reviewer --human

      # Fast review with Flash model
      reviewer --fast

      # Full review in human format with story
      reviewer "Add rate limiting to API endpoints" --full --human

      # Use custom design document
      reviewer --design-doc docs/architecture.md

      # Review AI-generated code
      reviewer --ai-generated

      # Review prototype code (security deprioritized)
      reviewer --prototype

      # Combined: AI-generated prototype with story
      reviewer "Add user auth" --ai-generated --prototype

      # Create or continue a named session
      reviewer --session-name "user-auth-feature"

      # Continue previous session with new changes
      reviewer --session-name "user-auth-feature" "Add password reset"

      # Review without session persistence
      reviewer --no-session

      # Use Claude instead of Gemini (currently disabled)
      # reviewer --claude
    """
    formatter = ReviewFormatter()

    try:
        # Load configuration
        config_path = Path(config) if config else None
        settings = load_config(config_path)


        # Step 1: Initialize git operations
        if verbose:
            formatter.print_info("[Step 1/6] Checking for uncommitted changes...")

        git_ops = GitOperations()

        # Check for changes
        if not git_ops.has_uncommitted_changes():
            formatter.print_warning("No uncommitted changes found.")
            return

        # Get repository info
        repo_info = git_ops.get_repo_info()
        repo_root = Path(repo_info["repo_path"]).resolve()
        changed_files = git_ops.get_uncommitted_files()
        total_changed = sum(len(files) for files in changed_files.values())

        if verbose:
            formatter.print_success(
                f"Found {total_changed} changed files in {repo_info['repo_path']}"
            )
            for status, files in changed_files.items():
                if files:
                    formatter.print_info(f"  {status.capitalize()}: {len(files)} files")

        # Read story/purpose context
        story_content = None
        if story:
            # Check if story is a file path
            story_path = Path(story)
            if story_path.exists() and story_path.is_file():
                # Security check: ensure path is within project boundaries
                story_abs_path = story_path.resolve()
                
                # Check if the story file is within the repository
                try:
                    story_abs_path.relative_to(repo_root)
                except ValueError:
                    # Path is outside repo - exit with error for security
                    formatter.print_error(
                        f"Security error: Story file '{story_path}' is outside the repository. "
                        f"Only files within the project directory can be read."
                    )
                    sys.exit(1)
                else:
                    # Safe to read - file is within repo
                    try:
                        with open(story_abs_path, "r", encoding="utf-8") as f:
                            story_content = f.read()
                        if verbose:
                            formatter.print_info(f"Using story context from file: {story_path}")
                    except Exception as e:
                        # Exit with error if file cannot be read
                        formatter.print_error(f"Failed to read story file '{story_path}': {e}")
                        sys.exit(1)
            else:
                # Treat as direct text
                story_content = story
                if verbose:
                    formatter.print_info("Using provided story context")

        # Read design document
        design_content = None
        design_doc_path = None

        if design_doc:
            # Use provided design doc
            design_doc_path = Path(design_doc)
        else:
            # Look for README.md in repo root
            readme_path = Path(repo_info["repo_path"]) / "README.md"
            if readme_path.exists():
                design_doc_path = readme_path

        if design_doc_path:
            try:
                with open(design_doc_path, "r", encoding="utf-8") as f:
                    design_content = f.read()
                if verbose:
                    formatter.print_info(f"Using design document: {design_doc_path}")
            except Exception as e:
                if verbose:
                    formatter.print_warning(f"Could not read design document: {e}")

        # Step 2: Build codebase index
        if verbose:
            formatter.print_info("\n[Step 2/6] Building codebase index...")

        # Pass exclude patterns from config if available
        exclude_patterns = settings.get("review", {}).get("exclude_patterns", None)
        indexer = CodebaseIndexer(Path(repo_info["repo_path"]), exclude_patterns=exclude_patterns)
        index = indexer.build_index()

        if verbose:
            formatter.print_success(
                f"Indexed {index.stats['total_files']} files, "
                f"found {index.stats['unique_symbols']} unique symbols "
                f"in {index.build_time:.2f} seconds"
            )

        if debug:
            formatter.print_info(
                f"  Symbol types found: {', '.join(set(s.type for symbols in index.symbols.values() for s in symbols))}"
            )

        # Step 3: Initialize navigation tools
        if verbose:
            formatter.print_info("\n[Step 3/6] Setting up navigation tools...")
        nav_tools = NavigationTools(Path(repo_info["repo_path"]), index, debug=debug)

        # Step 4: Initialize AI client
        if claude:
            # Claude support is temporarily disabled to implement proper cost tracking
            # and spending limits. Will be re-enabled once $1 spending limit is implemented.
            formatter.print_error("Claude support is temporarily disabled.")
            formatter.print_info("Please use Gemini instead by removing the --claude flag.")
            sys.exit(1)
        else:
            if verbose:
                formatter.print_info("\n[Step 4/6] Initializing Gemini AI...")

            try:
                # Use fast model if requested, otherwise use default (Pro)
                if fast:
                    model_name = "gemini-2.5-flash"
                    if verbose:
                        formatter.print_info("Using Gemini 2.5 Flash for faster analysis...")
                else:
                    model_name = settings["review"]["provider"]  # Default is Pro
                    if verbose:
                        formatter.print_info("Using Gemini 2.5 Pro for quality analysis...")

                # Check if we should use session-aware client
                use_session = False
                if session_name and not no_session:
                    if check_service_available():
                        use_session = True
                        if verbose:
                            formatter.print_info(f"Using persistent session: {session_name}")
                    else:
                        formatter.print_warning("Session service not available. Using standard mode.")
                        formatter.print_info("To enable sessions: python -m reviewer.service")

                # Create appropriate client
                if use_session:
                    ai_client = SessionAwareGeminiClient(
                        session_name=session_name,
                        model_name=model_name,
                        debug=debug,
                        ai_generated=ai_generated,
                        prototype=prototype,
                        design_doc=design_content,
                        story=story_content
                    )
                else:
                    # Get rate limiting settings from config
                    gemini_settings = settings.get("review", {}).get("gemini_settings", {})
                    rate_limiting_config = gemini_settings.get("rate_limiting", {})
                    raw_config_val = rate_limiting_config.get("enabled", True)
                    # Handle string values like "false", "no", "0", "off"
                    enable_rate_limiting = str(raw_config_val).lower() not in ('false', 'no', '0', 'off')
                    
                    # CLI flag overrides config
                    if no_rate_limit:
                        enable_rate_limiting = False
                    
                    ai_client = GeminiClient(
                        model_name=model_name, 
                        debug=debug,
                        enable_rate_limiting=enable_rate_limiting
                    )
                
                ai_client.setup_navigation_tools(nav_tools)
            except ValueError as e:
                formatter.print_error(str(e))
                formatter.print_info("Please set your GEMINI_API_KEY environment variable.")
                sys.exit(1)

        # Step 5: Prepare context
        if verbose:
            formatter.print_info("\n[Step 5/6] Preparing review context...")

        codebase_summary = indexer.get_index_summary(index)
        diffs = git_ops.get_all_diffs()
        initial_context = ai_client.format_initial_context(
            changed_files, codebase_summary, diffs, show_all=full, design_doc=design_content, 
            story=story_content, ai_generated=ai_generated, prototype=prototype
        )

        if verbose:
            formatter.print_info(f"Initial context size: {len(initial_context)} characters")

        # Step 6: Perform review
        if verbose:
            formatter.print_info("\n[Step 6/6] Running AI code review...")
            formatter.print_info(
                "🤖 Gemini is exploring your codebase and reviewing changes..."
            )

        # Show spinner if not verbose and spinner is enabled
        if not verbose and not no_spinner:
            with formatter.show_progress("🤖 Reviewing code...") as progress:
                task = progress.add_task("", total=None)
                start_time = time.time()
                review_result = ai_client.review_code(
                    initial_context, show_progress=False, show_all=full
                )
                end_time = time.time()
                progress.update(task, completed=100)
        else:
            start_time = time.time()
            # Always pass verbose to show_progress when not using spinner
            review_result = ai_client.review_code(
                initial_context, show_progress=verbose, show_all=full
            )
            end_time = time.time()
        
        # Handle fallback to standard client if session client failed
        if review_result is None and isinstance(ai_client, SessionAwareGeminiClient):
            formatter.print_info("Creating standard Gemini client for non-persistent review...")
            # Create a standard client with same parameters
            fallback_client = GeminiClient(
                model_name=ai_client.kwargs.get('model_name', 'gemini-2.5-pro'),
                debug=ai_client.kwargs.get('debug', False)
            )
            fallback_client.setup_navigation_tools(nav_tools)
            
            # Regenerate the initial context for the standard client
            initial_context = fallback_client.format_initial_context(
                changed_files=changed_files,
                codebase_summary=codebase_summary,
                diffs=diffs,
                show_all=full,
                design_doc=design_content,
                story=story_content,
                ai_generated=ai_generated,
                prototype=prototype
            )
            
            # Perform review with the correct context
            start_time = time.time()
            review_result = fallback_client.review_code(
                initial_context, show_progress=verbose, show_all=full
            )
            end_time = time.time()

        if verbose:
            formatter.print_info(f"\nReview completed in {end_time - start_time:.2f} seconds")

        # Add additional data to review result
        review_result["repo_info"] = repo_info
        review_result["changed_files"] = changed_files

        # Format and display results
        formatter.display_review_terminal(
            review_result, verbose=verbose, human_format=human, show_all=full
        )

        # Save to file if requested
        if output_file:
            markdown = formatter.format_review_markdown(review_result, output_file, show_all=full)
            if verbose:
                formatter.print_success(f"Review saved to: {output_file}")

        # Show token usage and cost estimate
        if verbose and settings["review"]["output"].get("show_cost", True):
            tokens = review_result.get("token_details", {}).get("total_tokens", 0)
            if tokens == 0:  # Fallback to estimate
                tokens = review_result["navigation_summary"].get("total_tokens_estimate", 0)

            # Cost estimates based on model
            # Note: Claude cost calculation removed until Claude support is re-enabled
            if fast:
                # Gemini 2.5 Flash pricing (much cheaper)
                # Input: $0.075 per 1M tokens, Output: $0.30 per 1M tokens
                if "token_details" in review_result:
                    input_tokens = review_result["token_details"]["input_tokens"]
                    output_tokens = review_result["token_details"]["output_tokens"]
                    cost = (input_tokens / 1_000_000) * 0.075 + (output_tokens / 1_000_000) * 0.30
                else:
                    cost = (tokens / 1_000_000) * 0.15  # Average estimate
                model_name = "Gemini 2.5 Flash"
            else:
                # Gemini 2.5 Pro pricing
                # Input: $1.25 per 1M tokens, Output: $5.00 per 1M tokens
                if "token_details" in review_result:
                    input_tokens = review_result["token_details"]["input_tokens"]
                    output_tokens = review_result["token_details"]["output_tokens"]
                    cost = (input_tokens / 1_000_000) * 1.25 + (output_tokens / 1_000_000) * 5.00
                else:
                    cost = (tokens / 1_000_000) * 2.50  # Average estimate
                model_name = "Gemini 2.5 Pro Preview"

            if verbose:
                # Display token usage
                formatter.print_info("\n📊 Token Usage:")
                if "token_details" in review_result:
                    formatter.print_info(
                        f"  Input tokens: {review_result['token_details']['input_tokens']:,}"
                    )
                    formatter.print_info(
                        f"  Output tokens: {review_result['token_details']['output_tokens']:,}"
                    )
                    formatter.print_info(
                        f"  Total tokens: {review_result['token_details']['total_tokens']:,}"
                    )
                else:
                    formatter.print_info(f"  Estimated tokens: {tokens:,}")
                formatter.print_info(f"  Model: {model_name}")
                formatter.print_info(f"  Estimated cost: ${cost:.4f}")

    except KeyboardInterrupt:
        formatter.print_warning("\nReview cancelled by user.")
        sys.exit(0)
    except Exception as e:
        formatter.print_error(f"An error occurred: {str(e)}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.group()
def service():
    """Manage the Reviewer API service."""
    pass


@service.command()
def status():
    """Check the status of the Reviewer service."""
    manage_service("status")


@service.command()
def restart():
    """Restart the Reviewer service."""
    manage_service("restart")


@service.command()
def logs():
    """View logs from the Reviewer service."""
    manage_service("logs")


@service.command()
def stop():
    """Stop the Reviewer service."""
    manage_service("stop")


@main.command("list-sessions")
def list_sessions_command():
    """List all active review sessions."""
    list_active_sessions()


if __name__ == "__main__":
    main()
