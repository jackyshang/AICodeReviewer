"""Codebase indexing for AI navigation - builds file trees and symbol mappings."""

import ast
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pathspec


@dataclass
class Symbol:
    """Represents a code symbol (class, function, method)."""
    name: str
    type: str  # 'class', 'function', 'method'
    file_path: str
    line_number: int
    parent: Optional[str] = None  # For methods, the parent class name


@dataclass
class FileNode:
    """Represents a file in the project tree."""
    name: str
    path: str
    is_dir: bool
    children: List['FileNode'] = field(default_factory=list)
    size: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            'name': self.name,
            'path': self.path,
            'is_dir': self.is_dir
        }
        if self.children:
            result['children'] = [child.to_dict() for child in self.children]
        if self.size is not None:
            result['size'] = self.size
        return result


@dataclass
class CodebaseIndex:
    """Complete index of a codebase for AI navigation."""
    file_tree: FileNode
    symbols: Dict[str, List[Symbol]]  # symbol name -> list of locations
    imports: Dict[str, List[str]]  # file -> list of imported files
    test_mapping: Dict[str, List[str]]  # test file -> source files it tests
    stats: Dict[str, int]  # Statistics about the index
    build_time: float


class CodebaseIndexer:
    """Builds comprehensive index of a codebase for AI navigation."""
    
    SUPPORTED_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.csx', '.vb', '.fs', '.fsx', '.fsi',  # .NET languages
        '.csproj', '.vbproj', '.fsproj', '.sln',  # .NET project files
        '.razor', '.cshtml', '.vbhtml',  # .NET web files
        '.php'  # PHP files
    }
    
    def __init__(self, repo_path: Path, exclude_patterns: Optional[List[str]] = None):
        """Initialize the indexer.
        
        Args:
            repo_path: Path to the repository root
            exclude_patterns: List of gitignore-style patterns to exclude
        """
        self.repo_path = repo_path
        self.exclude_patterns = exclude_patterns or self._get_default_excludes()
        self.gitignore_spec = self._load_gitignore()
        
    def _get_default_excludes(self) -> List[str]:
        """Get default exclude patterns."""
        return [
            '__pycache__',
            '*.pyc',
            'node_modules',
            '.git',
            '.venv',
            'venv',
            'env',
            'dist',
            'build',
            '.pytest_cache',
            '.mypy_cache',
            '*.egg-info',
            '.tox',
            'htmlcov',
            '.coverage',
            '*.log',
            '.DS_Store',
            'Thumbs.db',
            # .NET specific exclusions
            'bin/',
            'obj/',
            '*.dll',
            '*.pdb',
            '*.exe',
            'TestResults/',
            '*.user',
            '*.suo',
            '.vs/',
            'packages/',
            '*.nupkg',
            '*.cache',
            '_ReSharper*',
            '*.dotCover'
        ]
    
    def _load_gitignore(self) -> pathspec.PathSpec:
        """Load .gitignore patterns."""
        patterns = self.exclude_patterns.copy()
        gitignore_path = self.repo_path / '.gitignore'
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                patterns.extend(line.strip() for line in f if line.strip() and not line.startswith('#'))
                
        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    
    def should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded."""
        relative_path = path.relative_to(self.repo_path)
        return self.gitignore_spec.match_file(str(relative_path))
    
    def build_index(self) -> CodebaseIndex:
        """Build complete codebase index.
        
        Returns:
            CodebaseIndex with all navigation data
        """
        start_time = time.time()
        
        # Build file tree
        file_tree = self._build_file_tree()
        
        # Extract symbols from all source files
        symbols: Dict[str, List[Symbol]] = {}
        imports: Dict[str, List[str]] = {}
        test_mapping: Dict[str, List[str]] = {}
        
        for file_path in self._get_source_files():
            file_symbols = []
            file_imports = []
            
            if file_path.suffix == '.py':
                file_symbols, file_imports = self._extract_python_symbols(file_path)
            elif file_path.suffix in {'.cs', '.vb'}:
                file_symbols, file_imports = self._extract_dotnet_symbols(file_path)
            elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                file_symbols, file_imports = self._extract_javascript_symbols(file_path)
            elif file_path.suffix == '.php':
                file_symbols, file_imports = self._extract_php_symbols(file_path)
            
            # Add symbols to index
            for symbol in file_symbols:
                if symbol.name not in symbols:
                    symbols[symbol.name] = []
                symbols[symbol.name].append(symbol)
            
            # Add imports
            if file_imports:
                imports[str(file_path.relative_to(self.repo_path))] = file_imports
            
            # Check if it's a test file and map to source
            if self._is_test_file(file_path):
                source_files = self._find_tested_files(file_path)
                if source_files:
                    test_mapping[str(file_path.relative_to(self.repo_path))] = source_files
        
        # Calculate statistics
        stats = {
            'total_files': sum(1 for _ in self._get_all_files()),
            'source_files': sum(1 for _ in self._get_source_files()),
            'total_symbols': sum(len(locs) for locs in symbols.values()),
            'unique_symbols': len(symbols),
            'test_files': len(test_mapping)
        }
        
        build_time = time.time() - start_time
        
        return CodebaseIndex(
            file_tree=file_tree,
            symbols=symbols,
            imports=imports,
            test_mapping=test_mapping,
            stats=stats,
            build_time=build_time
        )
    
    def _build_file_tree(self) -> FileNode:
        """Build hierarchical file tree."""
        root = FileNode(
            name=self.repo_path.name,
            path=str(self.repo_path),
            is_dir=True
        )
        
        # Common directories to skip entirely
        skip_dirs = {'bin', 'obj', 'node_modules', '.git', 'TestResults', 'packages', '.vs'}
        
        def build_node(path: Path, parent_node: FileNode):
            """Recursively build file tree nodes."""
            try:
                for item in sorted(path.iterdir()):
                    # Skip broken symlinks
                    if item.is_symlink() and not item.exists():
                        continue
                    
                    # Early exit for common directories
                    if item.is_dir() and item.name in skip_dirs:
                        continue
                        
                    if self.should_exclude(item):
                        continue
                        
                    if item.is_dir():
                        dir_node = FileNode(
                            name=item.name,
                            path=str(item.relative_to(self.repo_path)),
                            is_dir=True
                        )
                        parent_node.children.append(dir_node)
                        build_node(item, dir_node)
                    else:
                        try:
                            # Use stat() which will fail for broken symlinks
                            size = item.stat().st_size
                            file_node = FileNode(
                                name=item.name,
                                path=str(item.relative_to(self.repo_path)),
                                is_dir=False,
                                size=size
                            )
                            parent_node.children.append(file_node)
                        except (OSError, IOError):
                            # Skip files we can't stat (broken symlinks, etc)
                            continue
            except (PermissionError, FileNotFoundError) as e:
                # Log the error but continue processing
                if isinstance(e, FileNotFoundError):
                    print(f"Warning: Path not found while building tree: {path}")
                pass
        
        build_node(self.repo_path, root)
        return root
    
    def _get_all_files(self):
        """Generator for all files in the repository."""
        for root, dirs, files in os.walk(self.repo_path):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self.should_exclude(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                
                # Skip broken symlinks - same check as in _build_file_tree
                if file_path.is_symlink() and not file_path.exists():
                    continue
                    
                if not self.should_exclude(file_path):
                    yield file_path
    
    def _get_source_files(self):
        """Generator for source code files."""
        for file_path in self._get_all_files():
            if file_path.suffix in self.SUPPORTED_EXTENSIONS:
                yield file_path
    
    def _extract_python_symbols(self, file_path: Path) -> Tuple[List[Symbol], List[str]]:
        """Extract symbols and imports from a Python file."""
        symbols = []
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            relative_path = str(file_path.relative_to(self.repo_path))
            
            for node in ast.walk(tree):
                # Extract classes
                if isinstance(node, ast.ClassDef):
                    symbols.append(Symbol(
                        name=node.name,
                        type='class',
                        file_path=relative_path,
                        line_number=node.lineno
                    ))
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            symbols.append(Symbol(
                                name=item.name,
                                type='method',
                                file_path=relative_path,
                                line_number=item.lineno,
                                parent=node.name
                            ))
                
                # Extract functions
                elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                    # Check if it's a top-level function (not a method)
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if node in ast.walk(parent)):
                        symbols.append(Symbol(
                            name=node.name,
                            type='function',
                            file_path=relative_path,
                            line_number=node.lineno
                        ))
                
                # Extract imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors or encoding issues
            pass
        
        return symbols, imports
    
    def _is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file."""
        name = file_path.name.lower()
        return (
            name.startswith('test_') or 
            name.endswith('_test.py') or
            'test' in file_path.parts
        )
    
    def _find_tested_files(self, test_file: Path) -> List[str]:
        """Find source files that a test file likely tests."""
        tested_files = []
        test_name = test_file.stem
        
        # Remove test_ prefix or _test suffix
        if test_name.startswith('test_'):
            source_name = test_name[5:]
        elif test_name.endswith('_test'):
            source_name = test_name[:-5]
        else:
            source_name = test_name
        
        # Look for matching source files
        for source_file in self._get_source_files():
            if source_file.stem == source_name and not self._is_test_file(source_file):
                tested_files.append(str(source_file.relative_to(self.repo_path)))
        
        return tested_files
    
    def to_json(self, index: CodebaseIndex) -> str:
        """Convert index to JSON string."""
        return json.dumps({
            'file_tree': index.file_tree.to_dict(),
            'symbols': {
                name: [
                    {
                        'name': s.name,
                        'type': s.type,
                        'file_path': s.file_path,
                        'line_number': s.line_number,
                        'parent': s.parent
                    }
                    for s in locations
                ]
                for name, locations in index.symbols.items()
            },
            'imports': index.imports,
            'test_mapping': index.test_mapping,
            'stats': index.stats,
            'build_time': index.build_time
        }, indent=2)
    
    def get_index_summary(self, index: CodebaseIndex) -> str:
        """Get a human-readable summary of the index."""
        lines = [
            f"Codebase Index Summary",
            f"=" * 50,
            f"Total files: {index.stats['total_files']}",
            f"Source files: {index.stats['source_files']}",
            f"Unique symbols: {index.stats['unique_symbols']}",
            f"Total symbol occurrences: {index.stats['total_symbols']}",
            f"Test files: {index.stats['test_files']}",
            f"Build time: {index.build_time:.2f} seconds"
        ]
        return '\n'.join(lines)
    
    def _extract_dotnet_symbols(self, file_path: Path) -> Tuple[List[Symbol], List[str]]:
        """Extract symbols and imports from C# or VB.NET files using regex."""
        symbols = []
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            relative_path = str(file_path.relative_to(self.repo_path))
            
            if file_path.suffix == '.cs':
                # Extract C# using/imports
                import_pattern = re.compile(r'^\s*using\s+([^;]+);', re.MULTILINE)
                imports = [match.group(1).strip() for match in import_pattern.finditer(content)]
                
                # Extract C# namespaces
                namespace_pattern = re.compile(r'namespace\s+(\w+(?:\.\w+)*)\s*{', re.MULTILINE)
                
                # Extract C# classes (including records)
                class_pattern = re.compile(
                    r'(?:public|private|protected|internal)?\s*(?:static|abstract|sealed|partial)?\s*'
                    r'(?:class|record|struct|interface)\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*[^{]+)?\s*(?:{|;)',
                    re.MULTILINE
                )
                
                # Extract C# methods
                method_pattern = re.compile(
                    r'(?:public|private|protected|internal)?\s*(?:static|virtual|override|async)?\s*'
                    r'(?!class|struct|interface)(?:[\w<>\[\]]+)\s+(\w+)\s*\([^)]*\)\s*(?:{|=>)',
                    re.MULTILINE
                )
                
                # Extract C# properties
                property_pattern = re.compile(
                    r'(?:public|private|protected|internal)?\s*(?:static|virtual|override)?\s*'
                    r'[\w<>\[\]]+\s+(\w+)\s*{\s*(?:get|set)',
                    re.MULTILINE
                )
                
                # Find line numbers for each pattern
                lines = content.split('\n')
                
                for match in class_pattern.finditer(content):
                    line_no = content[:match.start()].count('\n') + 1
                    symbols.append(Symbol(
                        name=match.group(1),
                        type='class',
                        file_path=relative_path,
                        line_number=line_no
                    ))
                
                for match in method_pattern.finditer(content):
                    name = match.group(1)
                    # Skip common false positives
                    if name not in {'if', 'while', 'for', 'switch', 'catch', 'using', 'new'}:
                        line_no = content[:match.start()].count('\n') + 1
                        symbols.append(Symbol(
                            name=name,
                            type='function',
                            file_path=relative_path,
                            line_number=line_no
                        ))
                
                for match in property_pattern.finditer(content):
                    line_no = content[:match.start()].count('\n') + 1
                    symbols.append(Symbol(
                        name=match.group(1),
                        type='property',
                        file_path=relative_path,
                        line_number=line_no
                    ))
            
        except (UnicodeDecodeError, IOError):
            # Skip files with encoding issues
            pass
        
        return symbols, imports
    
    def _extract_javascript_symbols(self, file_path: Path) -> Tuple[List[Symbol], List[str]]:
        """Extract symbols and imports from JavaScript/TypeScript files using regex."""
        symbols = []
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            relative_path = str(file_path.relative_to(self.repo_path))
            
            # Extract imports
            import_pattern = re.compile(
                r'import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
                re.MULTILINE
            )
            imports = [match.group(1) for match in import_pattern.finditer(content)]
            
            # Extract require statements
            require_pattern = re.compile(r'require\([\'"]([^\'"]+)[\'"]\)')
            imports.extend([match.group(1) for match in require_pattern.finditer(content)])
            
            # Extract classes
            class_pattern = re.compile(
                r'(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?',
                re.MULTILINE
            )
            
            # Extract functions
            function_pattern = re.compile(
                r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(',
                re.MULTILINE
            )
            
            # Extract arrow functions assigned to const/let/var
            arrow_pattern = re.compile(
                r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>',
                re.MULTILINE
            )
            
            # Find line numbers
            for match in class_pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    type='class',
                    file_path=relative_path,
                    line_number=line_no
                ))
            
            for match in function_pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    type='function',
                    file_path=relative_path,
                    line_number=line_no
                ))
            
            for match in arrow_pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    type='function',
                    file_path=relative_path,
                    line_number=line_no
                ))
            
        except (UnicodeDecodeError, IOError):
            pass
        
        return symbols, imports
    
    def _extract_php_symbols(self, file_path: Path) -> Tuple[List[Symbol], List[str]]:
        """Extract symbols and imports from PHP files using regex."""
        symbols = []
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            relative_path = str(file_path.relative_to(self.repo_path))
            
            # Extract PHP namespace/use statements
            namespace_pattern = re.compile(r'^\s*namespace\s+([^;]+);', re.MULTILINE)
            use_pattern = re.compile(r'^\s*use\s+([^;]+);', re.MULTILINE)
            include_pattern = re.compile(r'(?:include|require)(?:_once)?\s*\(?\s*[\'"]([^\'"]+)[\'"]', re.MULTILINE)
            
            # Extract imports
            for match in use_pattern.finditer(content):
                imports.append(match.group(1).strip())
            
            for match in include_pattern.finditer(content):
                imports.append(match.group(1).strip())
            
            # Extract PHP classes
            class_pattern = re.compile(
                r'(?:abstract\s+|final\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[^{]+)?\s*{',
                re.MULTILINE
            )
            
            # Extract PHP interfaces
            interface_pattern = re.compile(
                r'interface\s+(\w+)(?:\s+extends\s+[^{]+)?\s*{',
                re.MULTILINE
            )
            
            # Extract PHP traits
            trait_pattern = re.compile(
                r'trait\s+(\w+)\s*{',
                re.MULTILINE
            )
            
            # Extract PHP functions
            function_pattern = re.compile(
                r'(?:public|private|protected|static)?\s*function\s+(\w+)\s*\(',
                re.MULTILINE
            )
            
            # Extract PHP methods (functions inside classes)
            method_pattern = re.compile(
                r'(?:public|private|protected|static)?\s*function\s+(\w+)\s*\([^)]*\)\s*{',
                re.MULTILINE
            )
            
            # Find line numbers for classes
            for match in class_pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    type='class',
                    file_path=relative_path,
                    line_number=line_no
                ))
            
            # Find line numbers for interfaces
            for match in interface_pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    type='interface',
                    file_path=relative_path,
                    line_number=line_no
                ))
            
            # Find line numbers for traits
            for match in trait_pattern.finditer(content):
                line_no = content[:match.start()].count('\n') + 1
                symbols.append(Symbol(
                    name=match.group(1),
                    type='trait',
                    file_path=relative_path,
                    line_number=line_no
                ))
            
            # Find line numbers for functions
            for match in function_pattern.finditer(content):
                function_name = match.group(1)
                line_no = content[:match.start()].count('\n') + 1
                
                # Skip magic methods and constructors for cleaner output
                if function_name.startswith('__'):
                    continue
                
                # Determine if it's a method (inside class) or standalone function
                # Simple heuristic: check if we're inside a class block
                before_match = content[:match.start()]
                class_count = before_match.count('class ')
                class_end_count = before_match.count('}')
                
                symbol_type = 'method' if class_count > class_end_count else 'function'
                
                symbols.append(Symbol(
                    name=function_name,
                    type=symbol_type,
                    file_path=relative_path,
                    line_number=line_no
                ))
            
        except (UnicodeDecodeError, IOError):
            # Skip files with encoding issues
            pass
        
        return symbols, imports