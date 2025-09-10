"""Tests for git operations module."""

from pathlib import Path

import pytest
from git import Repo

from reviewer.git_operations import GitOperations


class TestGitOperations:
    """Test GitOperations class."""
    
    def test_init_with_valid_repo(self, temp_git_repo: Path):
        """Test initialization with valid git repository."""
        git_ops = GitOperations(temp_git_repo)
        assert git_ops.repo_path == temp_git_repo
        assert git_ops.repo is not None
    
    def test_init_with_non_git_directory(self, tmp_path: Path):
        """Test initialization with non-git directory."""
        with pytest.raises(ValueError, match="is not a git repository"):
            GitOperations(tmp_path)
    
    def test_has_uncommitted_changes_clean_repo(self, temp_git_repo: Path):
        """Test has_uncommitted_changes with clean repository."""
        git_ops = GitOperations(temp_git_repo)
        assert not git_ops.has_uncommitted_changes()
    
    def test_has_uncommitted_changes_with_modifications(self, sample_python_project: Path):
        """Test has_uncommitted_changes with modified files."""
        # Modify a file
        main_py = sample_python_project / "src" / "main.py"
        content = main_py.read_text()
        main_py.write_text(content + "\n# Modified")
        
        git_ops = GitOperations(sample_python_project)
        assert git_ops.has_uncommitted_changes()
    
    def test_get_uncommitted_files(self, sample_python_project: Path):
        """Test getting uncommitted files."""
        repo = Repo(sample_python_project)
        
        # Modify existing file
        main_py = sample_python_project / "src" / "main.py"
        content = main_py.read_text()
        main_py.write_text(content + "\n# Modified")
        
        # Add new file
        new_file = sample_python_project / "src" / "new_module.py"
        new_file.write_text("# New module\n")
        
        # Stage the new file
        repo.index.add([str(new_file)])
        
        # Create untracked file
        untracked = sample_python_project / "temp.txt"
        untracked.write_text("Temporary file\n")
        
        git_ops = GitOperations(sample_python_project)
        files = git_ops.get_uncommitted_files()
        
        assert "src/main.py" in files['modified']
        assert "src/new_module.py" in files['added']
        assert "temp.txt" in files['untracked']
        assert len(files['deleted']) == 0
    
    def test_get_diff_for_file(self, sample_python_project: Path):
        """Test getting diff for a specific file."""
        # Modify a file
        main_py = sample_python_project / "src" / "main.py"
        original_content = main_py.read_text()
        main_py.write_text(original_content.replace("Hello", "Hi"))
        
        git_ops = GitOperations(sample_python_project)
        diff = git_ops.get_diff_for_file("src/main.py")
        
        assert diff is not None
        assert "-    return f\"Hello, {name}!\"" in diff
        assert "+    return f\"Hi, {name}!\"" in diff
    
    def test_get_file_content(self, sample_python_project: Path):
        """Test getting file content."""
        git_ops = GitOperations(sample_python_project)
        
        # Get current content
        content = git_ops.get_file_content("src/main.py")
        assert content is not None
        assert "def greet(name: str)" in content
        
        # Get content from HEAD (before changes)
        main_py = sample_python_project / "src" / "main.py"
        main_py.write_text("# Modified content\n")
        
        original_content = git_ops.get_file_content("src/main.py", before_changes=True)
        assert original_content is not None
        assert "def greet(name: str)" in original_content
        assert "# Modified content" not in original_content
    
    def test_get_repo_info(self, sample_python_project: Path):
        """Test getting repository information."""
        git_ops = GitOperations(sample_python_project)
        info = git_ops.get_repo_info()
        
        assert info['repo_path'] == str(sample_python_project)
        assert info['current_branch'] == 'master' or info['current_branch'] == 'main'
        assert 'last_commit' in info
        assert info['last_commit']['message'] == "Add sample Python project"