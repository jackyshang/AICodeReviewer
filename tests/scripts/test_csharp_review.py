#!/usr/bin/env python3
"""Test C# file review specifically."""

import os
import tempfile
from pathlib import Path

from git import Repo
from rich.console import Console

import sys
sys.path.insert(0, str(Path(__file__).parent))

from reviewer.git_operations import GitOperations
from reviewer.codebase_indexer import CodebaseIndexer
from reviewer.navigation_tools import NavigationTools
from reviewer.gemini_client import GeminiClient

console = Console()

def test_csharp_review():
    """Test reviewing a C# file."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)
        
        # Create initial C# file
        (repo_path / "UserService.cs").write_text('''using System;

namespace MyApp.Services
{
    public class UserService
    {
        public string GetUserName(int id)
        {
            return $"User{id}";
        }
    }
}
''')
        
        repo.index.add(['UserService.cs'])
        repo.index.commit("Initial commit")
        
        # Make problematic changes
        (repo_path / "UserService.cs").write_text('''using System;
using System.Data.SqlClient;

namespace MyApp.Services
{
    public class UserService
    {
        private string connectionString = "Server=localhost;Database=myapp;";
        
        public string GetUserName(int id)
        {
            return $"User{id}";
        }
        
        // SECURITY: SQL Injection vulnerability!
        public User GetUserByName(string name)
        {
            var query = $"SELECT * FROM Users WHERE Name = '{name}'";
            using (var conn = new SqlConnection(connectionString))
            {
                // Execute query directly with user input
                var command = new SqlCommand(query, conn);
                conn.Open();
                var reader = command.ExecuteReader();
                if (reader.Read())
                {
                    return new User { 
                        Id = reader.GetInt32(0),
                        Name = reader.GetString(1)
                    };
                }
            }
            return null;
        }
        
        // BUG: No null check, will throw NullReferenceException
        public void ProcessUser(User user)
        {
            Console.WriteLine(user.Name.ToUpper());
        }
        
        // PERFORMANCE: This is O(n²) complexity
        public List<User> FindDuplicates(List<User> users)
        {
            var duplicates = new List<User>();
            for (int i = 0; i < users.Count; i++)
            {
                for (int j = i + 1; j < users.Count; j++)
                {
                    if (users[i].Name == users[j].Name)
                    {
                        duplicates.Add(users[j]);
                    }
                }
            }
            return duplicates;
        }
    }
    
    public class User
    {
        public int Id { get; set; }
        public string Name { get; set; }
    }
}
''')
        
        console.print("[bold]Running review on C# file...[/bold]\n")
        
        # Run the review
        git_ops = GitOperations(repo_path)
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        
        console.print(f"Index stats: {index.stats}")
        console.print(f"Symbols found: {list(index.symbols.keys())}\n")
        
        nav_tools = NavigationTools(repo_path, index)
        gemini = GeminiClient()
        gemini.setup_navigation_tools(nav_tools)
        
        changed_files = git_ops.get_uncommitted_files()
        codebase_summary = indexer.get_index_summary(index)
        diffs = git_ops.get_all_diffs()
        
        # Add explicit instruction about C#
        initial_context = gemini.format_initial_context(changed_files, codebase_summary, diffs)
        initial_context += "\n\nNote: This is a C# .NET project. Please pay special attention to C#-specific security issues, null safety, and performance patterns."
        
        review_result = gemini.review_code(initial_context, max_iterations=5)
        
        console.print("[bold green]Review Complete![/bold green]\n")
        console.print(review_result['review'])

if __name__ == "__main__":
    if not os.environ.get('GEMINI_API_KEY'):
        console.print("[red]Error: GEMINI_API_KEY not set[/red]")
    else:
        test_csharp_review()