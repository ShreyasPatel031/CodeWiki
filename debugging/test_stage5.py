#!/usr/bin/env python3
"""
Quick test script for Stage 5 (HTML generation) only.
Uses existing docs directory without regenerating from Stage 1.
"""

import sys
from pathlib import Path

# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add the project root to path
sys.path.insert(0, str(PROJECT_ROOT))

from codewiki.cli.html_generator import HTMLGenerator

def test_stage5(docs_dir: str = None):
    """Test Stage 5 HTML generation with existing docs."""
    if docs_dir is None:
        docs_dir = str(PROJECT_ROOT / "test_repos" / "gemini-cli" / "docs")
    docs_path = Path(docs_dir).resolve()
    output_path = docs_path / "index.html"
    
    print(f"[TEST] Stage 5 - HTML Generation Test")
    print(f"[TEST] Docs directory: {docs_path}")
    print(f"[TEST] Output path: {output_path}")
    
    # Check if docs exist
    if not docs_path.exists():
        print(f"[ERROR] Docs directory not found: {docs_path}")
        return False
    
    # Check for required files
    required = ["module_tree.json", "overview.md"]
    for f in required:
        fpath = docs_path / f
        if not fpath.exists():
            print(f"[ERROR] Required file missing: {fpath}")
            return False
        print(f"[TEST] Found: {f} ({fpath.stat().st_size} bytes)")
    
    # Remove existing index.html if present
    if output_path.exists():
        print(f"[TEST] Removing existing index.html...")
        output_path.unlink()
    
    # Create HTML generator
    print(f"[TEST] Creating HTMLGenerator...")
    html_generator = HTMLGenerator()
    print(f"[TEST] Template directory: {html_generator.template_dir}")
    
    # Get repo info
    print(f"[TEST] Detecting repository info...")
    repo_path = docs_path.parent
    repo_info = html_generator.detect_repository_info(repo_path)
    print(f"[TEST] Repo name: {repo_info.get('name')}")
    print(f"[TEST] Repo URL: {repo_info.get('url')}")
    
    # Generate HTML
    print(f"[TEST] Generating HTML...")
    try:
        html_generator.generate(
            output_path=output_path,
            title=repo_info['name'],
            repository_url=repo_info.get('url'),
            github_pages_url=repo_info.get('github_pages_url'),
            docs_dir=docs_path
        )
        print(f"[TEST] HTML generation complete!")
    except Exception as e:
        print(f"[ERROR] HTML generation failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify output
    if output_path.exists():
        size = output_path.stat().st_size
        print(f"[SUCCESS] index.html created: {size} bytes")
        return True
    else:
        print(f"[ERROR] index.html was not created!")
        return False

if __name__ == "__main__":
    docs_dir = sys.argv[1] if len(sys.argv) > 1 else None
    success = test_stage5(docs_dir)
    sys.exit(0 if success else 1)

