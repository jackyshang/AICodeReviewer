"""Git operations for detecting and analyzing uncommitted changes."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import git
from git import Repo


class GitOperations:
    """Handles git-related operations for the code review tool."""

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize GitOperations with a repository path.
        
        Args:
            repo_path: Path to the git repository. If None, uses current directory.
        """
        if isinstance(repo_path, str):
            self.repo_path = Path(repo_path)
        else:
            self.repo_path = repo_path or Path.cwd()
        self.repo = self._get_repo()

    def _get_repo(self) -> Repo:
        """Get the git repository object.
        
        Returns:
            git.Repo object
            
        Raises:
            ValueError: If the path is not a git repository
        """
        try:
            return Repo(self.repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"{self.repo_path} is not a git repository")

    def has_uncommitted_changes(self) -> bool:
        """Check if there are any uncommitted changes.
        
        Returns:
            True if there are uncommitted changes, False otherwise
        """
        return self.repo.is_dirty(untracked_files=True)

    def get_uncommitted_files(self) -> Dict[str, List[str]]:
        """Get lists of uncommitted files grouped by status.
        
        Returns:
            Dictionary with keys:
                - 'modified': List of modified files
                - 'added': List of added/staged files
                - 'deleted': List of deleted files
                - 'untracked': List of untracked files
        """
        result = {
            'modified': [],
            'added': [],
            'deleted': [],
            'untracked': []
        }

        # Get staged changes
        staged_diff = self.repo.index.diff('HEAD')
        for item in staged_diff:
            if item.change_type == 'M':
                result['modified'].append(item.a_path)
            elif item.change_type == 'A':
                result['added'].append(item.a_path)
            elif item.change_type == 'D':
                result['deleted'].append(item.a_path)

        # Get unstaged changes
        unstaged_diff = self.repo.index.diff(None)
        for item in unstaged_diff:
            if item.change_type == 'M' and item.a_path not in result['modified']:
                result['modified'].append(item.a_path)
            elif item.change_type == 'D' and item.a_path not in result['deleted']:
                result['deleted'].append(item.a_path)

        # Get untracked files
        result['untracked'] = self.repo.untracked_files

        return result

    def get_diff_for_file(self, file_path: str, staged: bool = False) -> Optional[str]:
        """Get the diff for a specific file.
        
        Args:
            file_path: Path to the file relative to repo root
            staged: If True, get staged diff; if False, get unstaged diff
            
        Returns:
            Diff string or None if no changes
        """
        try:
            if staged:
                diff = self.repo.git.diff('--cached', file_path)
            else:
                diff = self.repo.git.diff(file_path)
            return diff if diff else None
        except git.GitCommandError:
            return None

    def get_all_diffs(self) -> Dict[str, str]:
        """Get all diffs for uncommitted changes.
        
        Returns:
            Dictionary mapping file paths to their diff content
        """
        diffs = {}
        files = self.get_uncommitted_files()
        
        for status, file_list in files.items():
            if status == 'untracked':
                # For untracked files, show the entire content as addition
                for file_path in file_list:
                    full_path = self.repo_path / file_path
                    if full_path.exists() and full_path.is_file():
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            # Format as a diff showing all lines as additions
                            lines = content.splitlines()
                            diff_content = f"--- /dev/null\n+++ b/{file_path}\n@@ -0,0 +1,{len(lines)} @@\n"
                            diff_content += '\n'.join(f"+{line}" for line in lines)
                            diffs[file_path] = diff_content
                        except (UnicodeDecodeError, IOError):
                            diffs[file_path] = f"Binary or unreadable file: {file_path}"
            else:
                # For tracked files, get the actual diff
                for file_path in file_list:
                    # Try staged diff first, then unstaged
                    diff = self.get_diff_for_file(file_path, staged=True)
                    if not diff:
                        diff = self.get_diff_for_file(file_path, staged=False)
                    if diff:
                        diffs[file_path] = diff

        return diffs

    def get_file_content(self, file_path: str, before_changes: bool = False) -> Optional[str]:
        """Get the content of a file.
        
        Args:
            file_path: Path to the file relative to repo root
            before_changes: If True, get content before uncommitted changes
            
        Returns:
            File content or None if file doesn't exist
        """
        if before_changes:
            try:
                # Get file content from HEAD
                return self.repo.git.show(f'HEAD:{file_path}')
            except git.GitCommandError:
                return None
        else:
            full_path = self.repo_path / file_path
            if full_path.exists() and full_path.is_file():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except (UnicodeDecodeError, IOError):
                    return None
            return None

    def get_repo_info(self) -> Dict[str, str]:
        """Get basic repository information.
        
        Returns:
            Dictionary with repo info (current branch, last commit, etc.)
        """
        # TODO: Add more detailed repo statistics
        info = {
            'repo_path': str(self.repo_path),
            'current_branch': self.repo.active_branch.name if not self.repo.head.is_detached else 'detached',
            'is_dirty': self.repo.is_dirty(untracked_files=True),
            'total_commits': len(list(self.repo.iter_commits())),  # This could be slow on large repos
        }
        
        # Get last commit info
        if self.repo.head.is_valid():
            last_commit = self.repo.head.commit
            info['last_commit'] = {
                'hash': last_commit.hexsha[:8],
                'message': last_commit.message.strip(),
                'author': str(last_commit.author),
                'date': last_commit.committed_datetime.isoformat()
            }
        
        return info