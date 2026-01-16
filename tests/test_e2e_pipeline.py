#!/usr/bin/env python3
"""
End-to-End Pipeline Tests

Tests the complete flow from documentation generation to viewer compatibility.

Run with: python -m pytest tests/test_e2e_pipeline.py -v
"""

import json
import re
import pytest
from pathlib import Path
from typing import Dict, Any


# ============================================================
# VIEWER DATA FORMAT VALIDATION
# ============================================================

def validate_metadata_json(path: Path) -> Dict[str, Any]:
    """
    Validate metadata.json has required fields for viewer.
    
    Required fields:
    - generation_info (with timestamp, main_model, repo_path)
    
    Returns validation result dict.
    """
    result = {'valid': True, 'errors': [], 'warnings': []}
    
    if not path.exists():
        result['valid'] = False
        result['errors'].append(f"metadata.json not found at {path}")
        return result
    
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        result['valid'] = False
        result['errors'].append(f"Invalid JSON: {e}")
        return result
    
    # Check required fields
    if 'generation_info' not in data:
        result['warnings'].append("Missing 'generation_info' field")
    else:
        gen_info = data['generation_info']
        if 'repo_path' not in gen_info:
            result['warnings'].append("Missing 'repo_path' in generation_info")
    
    return result


def validate_module_tree_json(path: Path) -> Dict[str, Any]:
    """
    Validate module_tree.json structure.
    
    Expected structure:
    {
        "module_name": {
            "path": "src/module",
            "components": [...],
            "children": {}
        }
    }
    """
    result = {'valid': True, 'errors': [], 'warnings': [], 'module_count': 0}
    
    if not path.exists():
        result['valid'] = False
        result['errors'].append(f"module_tree.json not found at {path}")
        return result
    
    try:
        tree = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        result['valid'] = False
        result['errors'].append(f"Invalid JSON: {e}")
        return result
    
    if not isinstance(tree, dict):
        result['valid'] = False
        result['errors'].append(f"Expected dict, got {type(tree).__name__}")
        return result
    
    result['module_count'] = len(tree)
    
    if len(tree) == 0:
        result['warnings'].append("Module tree is empty")
    
    # Validate each module entry
    for module_name, module_data in tree.items():
        if not isinstance(module_data, dict):
            result['errors'].append(f"Module '{module_name}' data is not a dict")
            result['valid'] = False
            continue
        
        # Check for components (may be empty)
        if 'components' not in module_data:
            result['warnings'].append(f"Module '{module_name}' missing 'components' field")
    
    return result


def validate_overview_md(path: Path) -> Dict[str, Any]:
    """
    Validate overview.md has required content.
    
    Required:
    - Mermaid diagram
    - Diagram uses graph/flowchart
    - Diagram has click statements
    """
    result = {'valid': True, 'errors': [], 'warnings': []}
    
    if not path.exists():
        result['valid'] = False
        result['errors'].append(f"overview.md not found at {path}")
        return result
    
    content = path.read_text()
    
    # Check for Mermaid diagram
    mermaid_pattern = r'```mermaid\s*([\s\S]*?)```'
    match = re.search(mermaid_pattern, content)
    
    if not match:
        result['valid'] = False
        result['errors'].append("No Mermaid diagram found")
        return result
    
    diagram = match.group(1).strip()
    
    # Check diagram type
    if not re.search(r'^(graph|flowchart)\s+(TD|TB|LR|RL|BT)', diagram, re.MULTILINE):
        result['valid'] = False
        result['errors'].append("Diagram must use graph/flowchart type (not classDiagram)")
    
    # Check for click statements
    click_pattern = r'click\s+\w+\s+"[^"]+"'
    if not re.search(click_pattern, diagram):
        result['valid'] = False
        result['errors'].append("Diagram must have click statements linking to module files")
    
    return result


def validate_docs_folder(docs_path: Path) -> Dict[str, Any]:
    """
    Validate a complete documentation folder is viewer-compatible.
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'files_checked': [],
        'missing_module_docs': []
    }
    
    # Check required files
    required_files = ['metadata.json', 'module_tree.json', 'overview.md']
    for filename in required_files:
        filepath = docs_path / filename
        if not filepath.exists():
            result['valid'] = False
            result['errors'].append(f"Missing required file: {filename}")
        else:
            result['files_checked'].append(filename)
    
    if not result['valid']:
        return result
    
    # Validate each file
    metadata_result = validate_metadata_json(docs_path / 'metadata.json')
    if not metadata_result['valid']:
        result['valid'] = False
        result['errors'].extend(metadata_result['errors'])
    result['warnings'].extend(metadata_result.get('warnings', []))
    
    tree_result = validate_module_tree_json(docs_path / 'module_tree.json')
    if not tree_result['valid']:
        result['valid'] = False
        result['errors'].extend(tree_result['errors'])
    result['warnings'].extend(tree_result.get('warnings', []))
    result['module_count'] = tree_result.get('module_count', 0)
    
    overview_result = validate_overview_md(docs_path / 'overview.md')
    if not overview_result['valid']:
        result['valid'] = False
        result['errors'].extend(overview_result['errors'])
    result['warnings'].extend(overview_result.get('warnings', []))
    
    # Check module documentation files exist
    tree_path = docs_path / 'module_tree.json'
    if tree_path.exists():
        tree = json.loads(tree_path.read_text())
        for module_name in tree.keys():
            module_file = docs_path / f"{module_name}.md"
            if not module_file.exists():
                result['missing_module_docs'].append(module_name)
        
        if result['missing_module_docs']:
            result['warnings'].append(
                f"Missing module docs: {', '.join(result['missing_module_docs'][:5])}"
                + (f" (+{len(result['missing_module_docs']) - 5} more)" 
                   if len(result['missing_module_docs']) > 5 else "")
            )
    
    return result


# ============================================================
# TEST FIXTURES
# ============================================================

@pytest.fixture
def flask_docs_path():
    """Path to Flask demo documentation."""
    return Path(__file__).parent.parent / "demo" / "repos" / "flask"


@pytest.fixture
def demo_repos_path():
    """Path to demo repos folder."""
    return Path(__file__).parent.parent / "demo" / "repos"


# ============================================================
# TESTS
# ============================================================

class TestViewerDataFormat:
    """Tests for viewer data format compatibility."""
    
    def test_flask_docs_valid(self, flask_docs_path):
        """Test Flask demo docs are viewer-compatible."""
        if not flask_docs_path.exists():
            pytest.skip("Flask demo not available")
        
        result = validate_docs_folder(flask_docs_path)
        
        print(f"\nFlask docs validation:")
        print(f"  Valid: {result['valid']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Warnings: {result['warnings']}")
        print(f"  Module count: {result.get('module_count', 'N/A')}")
        
        assert result['valid'], f"Flask docs invalid: {result['errors']}"
    
    def test_all_demo_repos_valid(self, demo_repos_path):
        """Test all demo repos are viewer-compatible."""
        if not demo_repos_path.exists():
            pytest.skip("Demo repos folder not available")
        
        repos_checked = 0
        failures = []
        
        for repo_path in demo_repos_path.iterdir():
            if not repo_path.is_dir():
                continue
            
            # Skip if no module_tree.json (not a generated docs folder)
            if not (repo_path / 'module_tree.json').exists():
                continue
            
            repos_checked += 1
            result = validate_docs_folder(repo_path)
            
            if not result['valid']:
                failures.append({
                    'repo': repo_path.name,
                    'errors': result['errors']
                })
        
        print(f"\nChecked {repos_checked} repos")
        
        if failures:
            print("Failures:")
            for f in failures:
                print(f"  {f['repo']}: {f['errors']}")
        
        assert len(failures) == 0, f"Some repos invalid: {failures}"


class TestMetadataFormat:
    """Tests for metadata.json format."""
    
    def test_metadata_has_generation_info(self, flask_docs_path):
        metadata_path = flask_docs_path / 'metadata.json'
        if not metadata_path.exists():
            pytest.skip("metadata.json not available")
        
        data = json.loads(metadata_path.read_text())
        assert 'generation_info' in data, "Missing generation_info"
    
    def test_metadata_has_repo_path(self, flask_docs_path):
        metadata_path = flask_docs_path / 'metadata.json'
        if not metadata_path.exists():
            pytest.skip("metadata.json not available")
        
        data = json.loads(metadata_path.read_text())
        assert 'repo_path' in data.get('generation_info', {}), "Missing repo_path"


class TestModuleTreeFormat:
    """Tests for module_tree.json format."""
    
    def test_module_tree_not_empty(self, flask_docs_path):
        tree_path = flask_docs_path / 'module_tree.json'
        if not tree_path.exists():
            pytest.skip("module_tree.json not available")
        
        tree = json.loads(tree_path.read_text())
        assert len(tree) > 0, "Module tree is empty"
    
    def test_module_entries_have_components(self, flask_docs_path):
        tree_path = flask_docs_path / 'module_tree.json'
        if not tree_path.exists():
            pytest.skip("module_tree.json not available")
        
        tree = json.loads(tree_path.read_text())
        
        for module_name, module_data in tree.items():
            assert 'components' in module_data, f"Module '{module_name}' missing components"


class TestOverviewFormat:
    """Tests for overview.md format."""
    
    def test_overview_has_graph_diagram(self, flask_docs_path):
        overview_path = flask_docs_path / 'overview.md'
        if not overview_path.exists():
            pytest.skip("overview.md not available")
        
        content = overview_path.read_text()
        
        # Extract diagram
        match = re.search(r'```mermaid\s*([\s\S]*?)```', content)
        assert match, "No Mermaid diagram found"
        
        diagram = match.group(1)
        assert re.search(r'^(graph|flowchart)', diagram, re.MULTILINE), \
            "Diagram should use graph or flowchart type"
    
    def test_overview_has_click_statements(self, flask_docs_path):
        overview_path = flask_docs_path / 'overview.md'
        if not overview_path.exists():
            pytest.skip("overview.md not available")
        
        content = overview_path.read_text()
        
        assert 'click' in content.lower(), "Overview should have click statements"
        assert re.search(r'click\s+\w+\s+"[^"]+"', content), \
            "Click statements should link to .md files"


# ============================================================
# CLI RUNNER
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        docs_path = Path(sys.argv[1])
        
        if docs_path.exists() and docs_path.is_dir():
            print(f"Validating documentation folder: {docs_path}\n")
            result = validate_docs_folder(docs_path)
            
            print(f"Valid: {result['valid']}")
            print(f"Files checked: {result['files_checked']}")
            print(f"Module count: {result.get('module_count', 'N/A')}")
            
            if result['errors']:
                print(f"\nErrors:")
                for e in result['errors']:
                    print(f"  ❌ {e}")
            
            if result['warnings']:
                print(f"\nWarnings:")
                for w in result['warnings']:
                    print(f"  ⚠️  {w}")
            
            if result['missing_module_docs']:
                print(f"\nMissing module docs: {result['missing_module_docs']}")
            
            sys.exit(0 if result['valid'] else 1)
        else:
            print(f"Directory not found: {docs_path}")
            sys.exit(1)
    else:
        print("Usage: python test_e2e_pipeline.py <docs_folder_path>")
        print("Or run with pytest: python -m pytest tests/test_e2e_pipeline.py -v")


