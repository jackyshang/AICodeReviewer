"""Navigation tools for AI-driven code exploration."""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from reviewer.codebase_indexer import CodebaseIndex, Symbol


class NavigationTools:
    """Provides navigation functions for AI to explore codebases."""
    
    def __init__(self, repo_path: Path, index: CodebaseIndex, debug: bool = False):
        """Initialize navigation tools.
        
        Args:
            repo_path: Path to the repository root
            index: Pre-built codebase index
            debug: Enable debug logging
        """
        self.repo_path = repo_path
        self.index = index
        self._file_cache: Dict[str, str] = {}  # Cache for read files
        self.debug = debug
        
    def read_file(self, filepath: str) -> str:
        """Read and return file content.
        
        Args:
            filepath: Path to file relative to repo root
            
        Returns:
            File content or error message
        """
        # Check cache first
        if filepath in self._file_cache:
            if self.debug:
                print(f"\n🔍 DEBUG: Reading file from cache: {filepath}")
            return self._file_cache[filepath]
            
        full_path = self.repo_path / filepath
        
        # Security check - ensure path is within repo
        try:
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(self.repo_path.resolve())):
                return f"Error: Access denied - path outside repository: {filepath}"
        except Exception:
            return f"Error: Invalid path: {filepath}"
        
        if not full_path.exists():
            return f"Error: File not found: {filepath}"
            
        if not full_path.is_file():
            return f"Error: Not a file: {filepath}"
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._file_cache[filepath] = content
                
                if self.debug:
                    print(f"\n📄 DEBUG: File Read by Gemini: {filepath}")
                    print(f"   Size: {len(content)} characters, {len(content.splitlines())} lines")
                    print("   Content Preview (first 500 chars):")
                    print("   " + "-" * 70)
                    preview = content[:500]
                    for line in preview.splitlines():
                        print(f"   | {line}")
                    if len(content) > 500:
                        print("   | ... (truncated)")
                    print("   " + "-" * 70)
                
                return content
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {filepath}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def search_symbol(self, symbol_name: str) -> List[Dict[str, any]]:
        """Find where a class/function/variable is defined.
        
        Args:
            symbol_name: Name of the symbol to search for
            
        Returns:
            List of locations where symbol is defined
        """
        results = []
        
        if symbol_name in self.index.symbols:
            for symbol in self.index.symbols[symbol_name]:
                results.append({
                    'name': symbol.name,
                    'type': symbol.type,
                    'file': symbol.file_path,
                    'line': symbol.line_number,
                    'parent': symbol.parent
                })
        
        return results
    
    def find_usages(self, symbol_name: str) -> List[Dict[str, any]]:
        """Find all places where symbol is used.
        
        Args:
            symbol_name: Name of the symbol to find usages for
            
        Returns:
            List of locations where symbol is used
        """
        results = []
        
        # Use ripgrep if available, otherwise fall back to grep
        try:
            # Try ripgrep first (faster)
            cmd = ['rg', '-n', '--no-heading', f'\\b{re.escape(symbol_name)}\\b', str(self.repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                # Fall back to grep
                cmd = ['grep', '-rn', f'\\b{symbol_name}\\b', str(self.repo_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            # ripgrep not installed, use grep
            cmd = ['grep', '-rn', f'\\b{symbol_name}\\b', str(self.repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return [{'error': 'Search timeout - symbol name too common or codebase too large'}]
        
        if result.stdout:
            for line in result.stdout.splitlines():
                # Parse grep output: filename:line_number:content
                match = re.match(r'^(.+?):(\d+):(.*)$', line)
                if match:
                    filepath = match.group(1)
                    # Convert absolute path to relative
                    try:
                        rel_path = Path(filepath).relative_to(self.repo_path)
                        results.append({
                            'file': str(rel_path),
                            'line': int(match.group(2)),
                            'content': match.group(3).strip()
                        })
                    except ValueError:
                        # Path not relative to repo, skip
                        continue
        
        return results[:100]  # Limit results to prevent overwhelming output
    
    def get_imports(self, filepath: str) -> List[str]:
        """Get all imports from a file.
        
        Args:
            filepath: Path to file relative to repo root
            
        Returns:
            List of imported modules/files
        """
        # Check if we have this info in the index
        if filepath in self.index.imports:
            return self.index.imports[filepath]
        
        # Otherwise, try to extract imports from the file
        content = self.read_file(filepath)
        if content.startswith("Error:"):
            return []
        
        imports = []
        
        # Python imports
        if filepath.endswith('.py'):
            # Match import statements
            import_pattern = re.compile(r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$', re.MULTILINE)
            for match in import_pattern.finditer(content):
                if match.group(1):  # from X import Y
                    imports.append(match.group(1))
                else:  # import X
                    # Handle multiple imports: import a, b, c
                    for imp in match.group(2).split(','):
                        imp = imp.strip().split(' as ')[0]  # Remove aliases
                        imports.append(imp)
        
        # JavaScript/TypeScript imports
        elif filepath.endswith(('.js', '.ts', '.jsx', '.tsx')):
            # Match ES6 imports
            import_pattern = re.compile(r'^\s*import\s+.*?\s+from\s+[\'"](.+?)[\'"]', re.MULTILINE)
            imports.extend(match.group(1) for match in import_pattern.finditer(content))
            
            # Match require statements
            require_pattern = re.compile(r'require\([\'"](.+?)[\'"]\)')
            imports.extend(match.group(1) for match in require_pattern.finditer(content))
        
        return list(set(imports))  # Remove duplicates
    
    def get_file_tree(self) -> str:
        """Get project structure as tree.
        
        Returns:
            Tree representation of project structure
        """
        def build_tree_string(node, prefix="", is_last=True):
            """Recursively build tree string."""
            lines = []
            
            # Add current node
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + node.name)
            
            # Add children
            if node.children:
                extension = "    " if is_last else "│   "
                for i, child in enumerate(node.children):
                    is_last_child = i == len(node.children) - 1
                    lines.extend(build_tree_string(child, prefix + extension, is_last_child))
            
            return lines
        
        tree_lines = [self.index.file_tree.name]
        for i, child in enumerate(self.index.file_tree.children):
            is_last = i == len(self.index.file_tree.children) - 1
            tree_lines.extend(build_tree_string(child, "", is_last))
        
        return '\n'.join(tree_lines)
    
    def search_text(self, pattern: str, file_pattern: Optional[str] = None) -> List[Dict[str, any]]:
        """Search for text pattern across codebase.
        
        Args:
            pattern: Regular expression pattern to search for
            file_pattern: Optional file pattern to limit search (e.g., "*.py")
            
        Returns:
            List of matches
        """
        results = []
        
        try:
            # Build command
            if file_pattern:
                cmd = ['rg', '-n', '--no-heading', pattern, '--glob', file_pattern, str(self.repo_path)]
            else:
                cmd = ['rg', '-n', '--no-heading', pattern, str(self.repo_path)]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 and 'rg' in cmd[0]:
                # Fall back to grep
                if file_pattern:
                    cmd = ['grep', '-rn', '--include', file_pattern, pattern, str(self.repo_path)]
                else:
                    cmd = ['grep', '-rn', pattern, str(self.repo_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        except FileNotFoundError:
            # ripgrep not installed, use grep
            if file_pattern:
                cmd = ['grep', '-rn', '--include', file_pattern, pattern, str(self.repo_path)]
            else:
                cmd = ['grep', '-rn', pattern, str(self.repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return [{'error': 'Search timeout - pattern too broad or codebase too large'}]
        
        if result.stdout:
            for line in result.stdout.splitlines()[:100]:  # Limit results
                # Parse output
                match = re.match(r'^(.+?):(\d+):(.*)$', line)
                if match:
                    filepath = match.group(1)
                    try:
                        rel_path = Path(filepath).relative_to(self.repo_path)
                        results.append({
                            'file': str(rel_path),
                            'line': int(match.group(2)),
                            'content': match.group(3).strip()
                        })
                    except ValueError:
                        continue
        
        return results
    
    def get_navigation_summary(self) -> Dict[str, any]:
        """Get summary of navigation activity.
        
        Returns:
            Dictionary with navigation statistics
        """
        return {
            'files_cached': len(self._file_cache),
            'total_tokens_estimate': sum(len(content) for content in self._file_cache.values()) // 4,
            'files_read': list(self._file_cache.keys()),
            'index_stats': self.index.stats
        }