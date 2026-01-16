#!/usr/bin/env python3
"""
Viewer Verification Script

Verifies that a repository's documentation is compatible with the generic viewer.
Run this BEFORE claiming a repo works with the viewer.

Usage:
    python scripts/verify_viewer.py <repo_name>
    python scripts/verify_viewer.py --all  # Verify all repos
"""

import json
import os
import re
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def fail(msg):
    print(f"  {RED}✗{RESET} {msg}")

def warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def verify_repo(repo_path: Path) -> dict:
    """Verify a single repository's viewer compatibility."""
    results = {
        'name': repo_path.name,
        'passed': 0,
        'failed': 0,
        'warnings': 0,
        'errors': []
    }
    
    print(f"\n{BOLD}Verifying: {repo_path.name}{RESET}")
    print("=" * 50)
    
    # Check 1: Required files exist
    print("\n[1] Required Files:")
    required_files = ['metadata.json', 'module_tree.json', 'overview.md']
    for f in required_files:
        fpath = repo_path / f
        if fpath.exists():
            ok(f"{f} exists")
            results['passed'] += 1
        else:
            fail(f"{f} MISSING")
            results['failed'] += 1
            results['errors'].append(f"Missing required file: {f}")
    
    # Check 2: metadata.json is valid JSON
    print("\n[2] metadata.json format:")
    metadata_path = repo_path / 'metadata.json'
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
            ok("Valid JSON")
            results['passed'] += 1
            
            if 'generation_info' in metadata:
                ok("Has generation_info")
                results['passed'] += 1
            else:
                warn("Missing generation_info")
                results['warnings'] += 1
        except json.JSONDecodeError as e:
            fail(f"Invalid JSON: {e}")
            results['failed'] += 1
            results['errors'].append(f"Invalid metadata.json: {e}")
    
    # Check 3: module_tree.json is valid
    print("\n[3] module_tree.json format:")
    tree_path = repo_path / 'module_tree.json'
    module_count = 0
    if tree_path.exists():
        try:
            with open(tree_path) as f:
                tree = json.load(f)
            ok("Valid JSON")
            results['passed'] += 1
            
            module_count = len(tree)
            ok(f"Contains {module_count} top-level module(s)")
            results['passed'] += 1
            
            # Check module structure
            for key, data in tree.items():
                if 'components' in data:
                    ok(f"Module '{key}' has components list")
                    results['passed'] += 1
                else:
                    warn(f"Module '{key}' missing components")
                    results['warnings'] += 1
                break  # Just check first module
                
        except json.JSONDecodeError as e:
            fail(f"Invalid JSON: {e}")
            results['failed'] += 1
            results['errors'].append(f"Invalid module_tree.json: {e}")
    
    # Check 4: overview.md has Mermaid diagram
    print("\n[4] overview.md content:")
    overview_path = repo_path / 'overview.md'
    has_diagram = False
    has_click_statements = False
    diagram_nodes = []
    
    if overview_path.exists():
        with open(overview_path) as f:
            content = f.read()
        
        # Check for Mermaid diagram
        mermaid_match = re.search(r'```mermaid\n([\s\S]*?)```', content)
        if mermaid_match:
            has_diagram = True
            ok("Has Mermaid diagram")
            results['passed'] += 1
            
            diagram = mermaid_match.group(1)
            
            # Check diagram type
            if re.match(r'^\s*(graph|flowchart)\s+(TD|LR|TB|RL)', diagram):
                ok("Valid diagram type (graph/flowchart)")
                results['passed'] += 1
            else:
                warn("Unusual diagram type (may still work)")
                results['warnings'] += 1
            
            # Check for click statements (legacy - now auto-mapped)
            clicks = re.findall(r'click\s+(\w+)', diagram)
            if clicks:
                has_click_statements = True
                ok(f"Has {len(clicks)} click statements (legacy)")
                results['passed'] += 1
            else:
                ok("No click statements (will use auto-mapping)")
                results['passed'] += 1
            
            # Extract node definitions
            nodes = re.findall(r'(\w+)\s*\[["\']?([^"\'\]]+)["\']?\]', diagram)
            diagram_nodes = [n[0] for n in nodes]
            ok(f"Found {len(diagram_nodes)} node definitions")
            results['passed'] += 1
            
            # Check for common Mermaid issues
            if re.search(r'\|[^|"]+\.[^|]+\|', diagram):
                warn("Edge labels contain periods (viewer will auto-sanitize)")
                results['warnings'] += 1
            
        else:
            fail("No Mermaid diagram found")
            results['failed'] += 1
            results['errors'].append("overview.md has no Mermaid diagram")
    
    # Check 5: Node-to-module mapping potential
    print("\n[5] Node-to-Module Mapping:")
    if has_diagram and tree_path.exists():
        with open(tree_path) as f:
            tree = json.load(f)
        
        module_keys = list(tree.keys())
        
        # Check if diagram nodes can map to modules
        mapped_count = 0
        for node in diagram_nodes:
            node_lower = node.lower()
            for module_key in module_keys:
                module_lower = module_key.lower().replace('_', '')
                if node_lower in module_lower or module_lower in node_lower:
                    mapped_count += 1
                    break
        
        if mapped_count > 0:
            ok(f"{mapped_count}/{len(diagram_nodes)} nodes can map to modules")
            results['passed'] += 1
        elif module_count == 1:
            warn("Only 1 module exists - limited navigation available")
            results['warnings'] += 1
        else:
            warn("No automatic node-to-module mappings found")
            results['warnings'] += 1
    
    # Check 6: Module documentation files
    print("\n[6] Module Documentation:")
    md_files = list(repo_path.glob('*.md'))
    md_files = [f for f in md_files if f.name != 'overview.md']
    
    if md_files:
        ok(f"Found {len(md_files)} module documentation file(s)")
        for f in md_files[:5]:  # Show first 5
            print(f"      - {f.name}")
        if len(md_files) > 5:
            print(f"      ... and {len(md_files) - 5} more")
        results['passed'] += 1
    else:
        warn("No additional module documentation files")
        results['warnings'] += 1
    
    # Summary
    print(f"\n{BOLD}Summary for {repo_path.name}:{RESET}")
    print(f"  Passed:   {GREEN}{results['passed']}{RESET}")
    print(f"  Failed:   {RED}{results['failed']}{RESET}")
    print(f"  Warnings: {YELLOW}{results['warnings']}{RESET}")
    
    if results['failed'] == 0:
        print(f"\n  {GREEN}{BOLD}✓ VIEWER COMPATIBLE{RESET}")
    else:
        print(f"\n  {RED}{BOLD}✗ NOT COMPATIBLE - Fix errors above{RESET}")
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_viewer.py <repo_name>")
        print("       python scripts/verify_viewer.py --all")
        sys.exit(1)
    
    demo_repos_path = Path(__file__).parent.parent / 'demo' / 'repos'
    
    if sys.argv[1] == '--all':
        # Verify all repos
        repos = [d for d in demo_repos_path.iterdir() if d.is_dir()]
        if not repos:
            print("No repos found in demo/repos/")
            sys.exit(1)
        
        all_results = []
        for repo_path in repos:
            results = verify_repo(repo_path)
            all_results.append(results)
        
        # Final summary
        print("\n" + "=" * 60)
        print(f"{BOLD}FINAL SUMMARY{RESET}")
        print("=" * 60)
        
        passed_repos = [r for r in all_results if r['failed'] == 0]
        failed_repos = [r for r in all_results if r['failed'] > 0]
        
        print(f"\nCompatible repos: {GREEN}{len(passed_repos)}{RESET}")
        for r in passed_repos:
            print(f"  {GREEN}✓{RESET} {r['name']}")
        
        if failed_repos:
            print(f"\nIncompatible repos: {RED}{len(failed_repos)}{RESET}")
            for r in failed_repos:
                print(f"  {RED}✗{RESET} {r['name']}: {', '.join(r['errors'][:2])}")
        
        sys.exit(1 if failed_repos else 0)
    else:
        # Verify single repo
        repo_name = sys.argv[1]
        repo_path = demo_repos_path / repo_name
        
        if not repo_path.exists():
            print(f"Repo not found: {repo_path}")
            print(f"Available repos: {[d.name for d in demo_repos_path.iterdir() if d.is_dir()]}")
            sys.exit(1)
        
        results = verify_repo(repo_path)
        sys.exit(1 if results['failed'] > 0 else 0)


if __name__ == '__main__':
    main()
