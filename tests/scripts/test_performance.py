#!/usr/bin/env python3
"""Test performance of llm-review indexing."""

import time
from pathlib import Path
from reviewer.codebase_indexer import CodebaseIndexer

def test_indexing_performance(repo_path: Path):
    """Test indexing performance with detailed timing."""
    
    print(f"Testing indexing performance for: {repo_path}")
    print("-" * 60)
    
    # Initialize indexer
    start = time.time()
    indexer = CodebaseIndexer(repo_path)
    init_time = time.time() - start
    print(f"Indexer initialization: {init_time:.3f}s")
    
    # Count files
    start = time.time()
    all_files = list(indexer._get_all_files())
    file_scan_time = time.time() - start
    print(f"\nFile scanning: {file_scan_time:.3f}s")
    print(f"Total files found: {len(all_files)}")
    
    # Count source files
    start = time.time()
    source_files = list(indexer._get_source_files())
    source_scan_time = time.time() - start
    print(f"\nSource file filtering: {source_scan_time:.3f}s")
    print(f"Source files found: {len(source_files)}")
    
    # Show file type breakdown
    extensions = {}
    for f in source_files:
        ext = f.suffix
        extensions[ext] = extensions.get(ext, 0) + 1
    
    print("\nSource file breakdown:")
    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ext}: {count} files")
    
    # Full index build
    print("\nBuilding full index...")
    start = time.time()
    index = indexer.build_index()
    total_time = time.time() - start
    
    print(f"\nTotal indexing time: {total_time:.3f}s")
    print(f"Index stats: {index.stats}")
    
    # Identify slow parts
    print("\nPerformance analysis:")
    print(f"  File scanning: {file_scan_time:.3f}s ({file_scan_time/total_time*100:.1f}%)")
    print(f"  Source filtering: {source_scan_time:.3f}s ({source_scan_time/total_time*100:.1f}%)")
    print(f"  Symbol extraction: ~{total_time - file_scan_time - source_scan_time:.3f}s")
    
    # Check if bin/obj are being processed
    bin_obj_files = [f for f in all_files if '/bin/' in str(f) or '/obj/' in str(f)]
    print(f"\nFiles in bin/obj directories: {len(bin_obj_files)}")
    
    if bin_obj_files:
        print("WARNING: bin/obj directories are being processed!")
        print("Sample files:")
        for f in bin_obj_files[:5]:
            print(f"  {f}")

if __name__ == "__main__":
    # Test on a sample directory (pass as argument or use current directory)
    import sys
    if len(sys.argv) > 1:
        repo_path = Path(sys.argv[1])
    else:
        repo_path = Path.cwd()
    
    if not repo_path.exists():
        print(f"Error: Path {repo_path} does not exist")
        sys.exit(1)
    
    print(f"Testing performance on: {repo_path}")
    test_indexing_performance(repo_path)