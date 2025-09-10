#!/usr/bin/env python3
"""Test complex C# project with interfaces, inheritance, etc."""

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

def create_complex_csharp_project():
    """Create a complex C# project structure."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)
        
        # Create directory structure
        (repo_path / "src").mkdir()
        (repo_path / "src" / "Interfaces").mkdir()
        (repo_path / "src" / "Models").mkdir()
        (repo_path / "src" / "Services").mkdir()
        (repo_path / "src" / "Repositories").mkdir()
        
        # Create interface
        (repo_path / "src" / "Interfaces" / "IUserRepository.cs").write_text('''using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MyApp.Models;

namespace MyApp.Interfaces
{
    public interface IUserRepository
    {
        Task<User> GetByIdAsync(int id);
        Task<IEnumerable<User>> GetAllAsync();
        Task<User> CreateAsync(User user);
        Task UpdateAsync(User user);
        Task DeleteAsync(int id);
    }
}
''')

        # Create base model
        (repo_path / "src" / "Models" / "BaseEntity.cs").write_text('''using System;

namespace MyApp.Models
{
    public abstract class BaseEntity
    {
        public int Id { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime? UpdatedAt { get; set; }
        
        protected BaseEntity()
        {
            CreatedAt = DateTime.UtcNow;
        }
    }
}
''')

        # Create user model inheriting from base
        (repo_path / "src" / "Models" / "User.cs").write_text('''using System;

namespace MyApp.Models
{
    public class User : BaseEntity
    {
        public string Email { get; set; }
        public string FirstName { get; set; }
        public string LastName { get; set; }
        public bool IsActive { get; set; }
        
        public string FullName => $"{FirstName} {LastName}";
    }
}
''')

        # Create repository implementation
        (repo_path / "src" / "Repositories" / "UserRepository.cs").write_text('''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MyApp.Interfaces;
using MyApp.Models;

namespace MyApp.Repositories
{
    public class UserRepository : IUserRepository
    {
        private readonly List<User> _users = new();
        
        public async Task<User> GetByIdAsync(int id)
        {
            return await Task.FromResult(_users.FirstOrDefault(u => u.Id == id));
        }
        
        public async Task<IEnumerable<User>> GetAllAsync()
        {
            return await Task.FromResult(_users.AsEnumerable());
        }
        
        public async Task<User> CreateAsync(User user)
        {
            user.Id = _users.Count + 1;
            _users.Add(user);
            return await Task.FromResult(user);
        }
        
        public async Task UpdateAsync(User user)
        {
            var existing = _users.FirstOrDefault(u => u.Id == user.Id);
            if (existing != null)
            {
                existing.Email = user.Email;
                existing.FirstName = user.FirstName;
                existing.LastName = user.LastName;
                existing.UpdatedAt = DateTime.UtcNow;
            }
            await Task.CompletedTask;
        }
        
        public async Task DeleteAsync(int id)
        {
            _users.RemoveAll(u => u.Id == id);
            await Task.CompletedTask;
        }
    }
}
''')

        # Commit initial state
        repo.index.add(['*'])
        repo.index.commit("Initial complex C# project")
        
        # Now make problematic changes - add a service with issues
        (repo_path / "src" / "Services" / "UserService.cs").write_text('''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MyApp.Interfaces;
using MyApp.Models;

namespace MyApp.Services
{
    public class UserService
    {
        private readonly IUserRepository _repository;
        
        // ISSUE: No null check in constructor
        public UserService(IUserRepository repository)
        {
            _repository = repository;
        }
        
        // SECURITY: No authorization check
        public async Task<User> GetUserAsync(int id)
        {
            // ISSUE: No error handling
            return await _repository.GetByIdAsync(id);
        }
        
        // BUG: Possible null reference
        public async Task<string> GetUserEmailAsync(int id)
        {
            var user = await _repository.GetByIdAsync(id);
            return user.Email.ToLower(); // Will crash if user is null
        }
        
        // PERFORMANCE: Loading all users into memory
        public async Task<List<User>> SearchUsersAsync(string searchTerm)
        {
            var allUsers = await _repository.GetAllAsync();
            return allUsers
                .Where(u => u.FullName.Contains(searchTerm)) // Case sensitive
                .ToList(); // Forces evaluation of entire collection
        }
        
        // DESIGN: Violates single responsibility principle
        public async Task<bool> CreateUserAndSendEmailAsync(User user, string password)
        {
            // Validation logic mixed with business logic
            if (string.IsNullOrEmpty(user.Email))
                return false;
                
            if (password.Length < 8) // Magic number
                return false;
            
            // Repository operation
            await _repository.CreateAsync(user);
            
            // Email sending logic (should be in separate service)
            SendWelcomeEmail(user.Email);
            
            // Password hashing (should be in separate service)
            var hashedPassword = HashPassword(password);
            SavePassword(user.Id, hashedPassword);
            
            return true;
        }
        
        // SECURITY: Weak password hashing
        private string HashPassword(string password)
        {
            // Just using simple hash - should use bcrypt or similar
            return password.GetHashCode().ToString();
        }
        
        private void SendWelcomeEmail(string email)
        {
            // Email logic...
        }
        
        private void SavePassword(int userId, string hashedPassword)
        {
            // Password storage logic...
        }
    }
}
''')

        # Add a generic repository pattern with issues
        (repo_path / "src" / "Repositories" / "GenericRepository.cs").write_text('''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MyApp.Models;

namespace MyApp.Repositories
{
    // ISSUE: Missing interface definition
    public class GenericRepository<T> where T : BaseEntity
    {
        private readonly List<T> _entities = new();
        
        // ISSUE: Not thread-safe
        public async Task<T> GetByIdAsync(int id)
        {
            return await Task.FromResult(_entities.FirstOrDefault(e => e.Id == id));
        }
        
        // PERFORMANCE: O(n) lookup could be O(1) with Dictionary
        public async Task<T> FindAsync(Func<T, bool> predicate)
        {
            return await Task.FromResult(_entities.FirstOrDefault(predicate));
        }
        
        // BUG: Doesn't handle concurrent modifications
        public async Task<IEnumerable<T>> GetAllAsync()
        {
            return await Task.FromResult(_entities); // Returns reference to internal list!
        }
        
        // ISSUE: No validation
        public async Task<T> CreateAsync(T entity)
        {
            entity.Id = _entities.Count + 1; // Not thread-safe ID generation
            _entities.Add(entity);
            return await Task.FromResult(entity);
        }
    }
}
''')

        console.print("[bold]Running review on complex C# project...[/bold]\n")
        
        # Run the review
        git_ops = GitOperations(repo_path)
        indexer = CodebaseIndexer(repo_path)
        index = indexer.build_index()
        
        console.print(f"[cyan]Index Statistics:[/cyan]")
        console.print(f"  Total files: {index.stats['total_files']}")
        console.print(f"  Source files: {index.stats['source_files']}")
        console.print(f"  Unique symbols: {index.stats['unique_symbols']}")
        console.print(f"  Build time: {index.build_time:.3f}s\n")
        
        console.print(f"[cyan]Detected C# Symbols:[/cyan]")
        for symbol_name, locations in sorted(index.symbols.items())[:10]:  # First 10
            loc = locations[0]
            console.print(f"  {symbol_name} ({loc.type}) - {loc.file_path}:{loc.line_number}")
        if len(index.symbols) > 10:
            console.print(f"  ... and {len(index.symbols) - 10} more\n")
        
        nav_tools = NavigationTools(repo_path, index)
        gemini = GeminiClient()
        gemini.setup_navigation_tools(nav_tools)
        
        changed_files = git_ops.get_uncommitted_files()
        codebase_summary = indexer.get_index_summary(index)
        diffs = git_ops.get_all_diffs()
        
        initial_context = gemini.format_initial_context(changed_files, codebase_summary, diffs)
        initial_context += "\n\nThis is a C# .NET project using repository pattern with dependency injection. Please review for SOLID principles, security, performance, and C# best practices."
        
        console.print(f"[cyan]Initial context size:[/cyan] {len(initial_context)} characters\n")
        
        review_result = gemini.review_code(initial_context, max_iterations=10)
        
        console.print("[bold green]Review Complete![/bold green]\n")
        console.print(f"[cyan]Navigation Summary:[/cyan]")
        console.print(f"  Total API calls: {review_result['iterations']}")
        console.print(f"  Files explored: {len(review_result['navigation_history'])}")
        console.print(f"  Token estimate: {review_result['navigation_summary']['total_tokens_estimate']:,}\n")
        
        console.print("[cyan]Files explored:[/cyan]")
        for step in review_result['navigation_history']:
            if step['function'] == 'read_file':
                console.print(f"  - {step['args']['filepath']}")
        
        console.print(f"\n[bold]Review Results:[/bold]\n{review_result['review']}")

if __name__ == "__main__":
    if not os.environ.get('GEMINI_API_KEY'):
        console.print("[red]Error: GEMINI_API_KEY not set[/red]")
    else:
        create_complex_csharp_project()