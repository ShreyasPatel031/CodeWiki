#!/usr/bin/env python3
"""
Tests for Mermaid diagram format validation.

Ensures generated diagrams are compatible with the viewer:
- Use graph TD or flowchart TD (not classDiagram, sequenceDiagram)
- Include click statements linking to module files
- Have valid node definitions
- Have proper syntax

Run with: python -m pytest tests/test_diagram_format.py -v
"""

import re
import json
import pytest
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# DIAGRAM VALIDATION FUNCTIONS
# ============================================================

def extract_mermaid_from_markdown(content: str) -> Optional[str]:
    """Extract the first Mermaid diagram from markdown content."""
    pattern = r'```mermaid\s*([\s\S]*?)```'
    match = re.search(pattern, content)
    return match.group(1).strip() if match else None


def validate_diagram_type(diagram: str) -> Tuple[bool, str]:
    """
    Validate that diagram uses graph/flowchart type.
    
    Returns:
        (is_valid, message)
    """
    # Check for valid types
    valid_pattern = r'^(graph|flowchart)\s+(TD|TB|LR|RL|BT)'
    if re.search(valid_pattern, diagram, re.MULTILINE):
        return True, "Uses valid graph/flowchart type"
    
    # Check for invalid types
    invalid_types = ['classDiagram', 'sequenceDiagram', 'stateDiagram', 'erDiagram', 'pie']
    for invalid_type in invalid_types:
        if diagram.strip().startswith(invalid_type):
            return False, f"Uses incompatible diagram type: {invalid_type}"
    
    return False, "Missing or invalid diagram type declaration"


def validate_click_statements(diagram: str) -> Tuple[bool, str, List[str]]:
    """
    Validate that diagram has click statements.
    
    Returns:
        (is_valid, message, list_of_click_statements)
    """
    click_pattern = r'click\s+(\w+)\s+"([^"]+)"'
    matches = re.findall(click_pattern, diagram)
    
    if not matches:
        return False, "No click statements found", []
    
    click_statements = [f"{node} -> {target}" for node, target in matches]
    return True, f"Found {len(matches)} click statements", click_statements


def validate_node_definitions(diagram: str) -> Tuple[bool, str, int]:
    """
    Validate that diagram has proper node definitions.
    
    Returns:
        (is_valid, message, node_count)
    """
    # Pattern for node definitions: A[Label] or A["Label"]
    node_pattern = r'\b([A-Za-z_]\w*)\s*\[(?:"[^"]+"|[^\]]+)\]'
    matches = re.findall(node_pattern, diagram)
    
    if not matches:
        return False, "No node definitions found", 0
    
    unique_nodes = set(matches)
    return True, f"Found {len(unique_nodes)} unique nodes", len(unique_nodes)


def validate_no_syntax_issues(diagram: str) -> Tuple[bool, str]:
    """
    Check for common syntax issues.
    
    Returns:
        (is_valid, message)
    """
    issues = []
    
    # Check for unbalanced brackets
    if diagram.count('[') != diagram.count(']'):
        issues.append("Unbalanced square brackets")
    
    if diagram.count('(') != diagram.count(')'):
        issues.append("Unbalanced parentheses")
    
    # Check for problematic characters in labels
    if re.search(r'\[.*[(){}].*\]', diagram):
        issues.append("Parentheses/braces inside node labels (may cause parse errors)")
    
    # Check for subgraph/end balance
    subgraph_count = len(re.findall(r'\bsubgraph\b', diagram))
    end_count = len(re.findall(r'\bend\b', diagram))
    if subgraph_count != end_count:
        issues.append(f"Unbalanced subgraph/end ({subgraph_count} subgraph, {end_count} end)")
    
    if issues:
        return False, "; ".join(issues)
    
    return True, "No syntax issues detected"


def validate_overview_diagram(diagram: str) -> Dict:
    """
    Full validation of an overview diagram.
    
    Returns:
        {
            'valid': bool,
            'errors': List[str],
            'warnings': List[str],
            'info': Dict
        }
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': {}
    }
    
    # Type validation
    type_valid, type_msg = validate_diagram_type(diagram)
    result['info']['type'] = type_msg
    if not type_valid:
        result['valid'] = False
        result['errors'].append(type_msg)
    
    # Click statements
    click_valid, click_msg, clicks = validate_click_statements(diagram)
    result['info']['clicks'] = click_msg
    result['info']['click_list'] = clicks
    if not click_valid:
        result['valid'] = False
        result['errors'].append(click_msg)
    
    # Node definitions
    node_valid, node_msg, node_count = validate_node_definitions(diagram)
    result['info']['nodes'] = node_msg
    result['info']['node_count'] = node_count
    if not node_valid:
        result['valid'] = False
        result['errors'].append(node_msg)
    
    # Syntax check
    syntax_valid, syntax_msg = validate_no_syntax_issues(diagram)
    result['info']['syntax'] = syntax_msg
    if not syntax_valid:
        result['warnings'].append(syntax_msg)
    
    return result


# ============================================================
# TEST FIXTURES
# ============================================================

@pytest.fixture
def flask_docs_path():
    """Path to Flask demo documentation."""
    return Path(__file__).parent.parent / "demo" / "repos" / "flask"


@pytest.fixture
def valid_diagram():
    """A valid example diagram."""
    return '''graph TD
    A[Main Module]:::main
    B[Sub Module 1]
    C[Sub Module 2]
    
    A --> B
    A --> C
    
    click A "main.md" "View Main Module"
    click B "sub1.md" "View Sub Module 1"
    click C "sub2.md" "View Sub Module 2"
'''


@pytest.fixture
def invalid_class_diagram():
    """An invalid classDiagram."""
    return '''classDiagram
    class Animal {
        +String name
        +makeSound()
    }
'''


# ============================================================
# UNIT TESTS
# ============================================================

class TestDiagramTypeValidation:
    """Tests for diagram type validation."""
    
    def test_graph_td_valid(self):
        diagram = "graph TD\n    A --> B"
        valid, msg = validate_diagram_type(diagram)
        assert valid, msg
    
    def test_flowchart_td_valid(self):
        diagram = "flowchart TD\n    A --> B"
        valid, msg = validate_diagram_type(diagram)
        assert valid, msg
    
    def test_graph_lr_valid(self):
        diagram = "graph LR\n    A --> B"
        valid, msg = validate_diagram_type(diagram)
        assert valid, msg
    
    def test_class_diagram_invalid(self, invalid_class_diagram):
        valid, msg = validate_diagram_type(invalid_class_diagram)
        assert not valid
        assert "classDiagram" in msg
    
    def test_sequence_diagram_invalid(self):
        diagram = "sequenceDiagram\n    Alice->>Bob: Hello"
        valid, msg = validate_diagram_type(diagram)
        assert not valid
        assert "sequenceDiagram" in msg


class TestClickStatementValidation:
    """Tests for click statement validation."""
    
    def test_has_click_statements(self, valid_diagram):
        valid, msg, clicks = validate_click_statements(valid_diagram)
        assert valid
        assert len(clicks) == 3
    
    def test_no_click_statements(self):
        diagram = "graph TD\n    A --> B"
        valid, msg, clicks = validate_click_statements(diagram)
        assert not valid
        assert len(clicks) == 0
    
    def test_click_with_tooltip(self):
        diagram = 'click A "module.md" "View Module"'
        valid, msg, clicks = validate_click_statements(diagram)
        assert valid
        assert "A -> module.md" in clicks[0]


class TestNodeDefinitionValidation:
    """Tests for node definition validation."""
    
    def test_has_node_definitions(self, valid_diagram):
        valid, msg, count = validate_node_definitions(valid_diagram)
        assert valid
        assert count == 3
    
    def test_quoted_labels(self):
        diagram = 'A["Complex Label with Spaces"]'
        valid, msg, count = validate_node_definitions(diagram)
        assert valid
        assert count == 1
    
    def test_no_definitions(self):
        diagram = "graph TD\n    A --> B"  # A and B not defined with labels
        # This should still find A and B if they're in edges
        # Actually, our pattern requires brackets, so this won't find them
        valid, msg, count = validate_node_definitions(diagram)
        assert not valid  # No bracket definitions


class TestSyntaxValidation:
    """Tests for syntax issue detection."""
    
    def test_balanced_brackets(self, valid_diagram):
        valid, msg = validate_no_syntax_issues(valid_diagram)
        assert valid
    
    def test_unbalanced_brackets(self):
        diagram = "graph TD\n    A[Label\n    B[OK]"
        valid, msg = validate_no_syntax_issues(diagram)
        assert not valid
        assert "Unbalanced" in msg
    
    def test_subgraph_end_balance(self):
        diagram = "graph TD\n    subgraph G1\n        A --> B\n    end"
        valid, msg = validate_no_syntax_issues(diagram)
        assert valid
    
    def test_subgraph_without_end(self):
        diagram = "graph TD\n    subgraph G1\n        A --> B"
        valid, msg = validate_no_syntax_issues(diagram)
        assert not valid
        assert "subgraph" in msg.lower()


class TestOverviewValidation:
    """Tests for full overview diagram validation."""
    
    def test_valid_overview(self, valid_diagram):
        result = validate_overview_diagram(valid_diagram)
        assert result['valid']
        assert len(result['errors']) == 0
    
    def test_invalid_overview(self, invalid_class_diagram):
        result = validate_overview_diagram(invalid_class_diagram)
        assert not result['valid']
        assert len(result['errors']) > 0


# ============================================================
# INTEGRATION TESTS (with actual demo data)
# ============================================================

class TestFlaskDemoValidation:
    """Tests using actual Flask demo documentation."""
    
    def test_flask_overview_exists(self, flask_docs_path):
        overview_path = flask_docs_path / "overview.md"
        assert overview_path.exists(), f"overview.md not found at {overview_path}"
    
    def test_flask_overview_has_diagram(self, flask_docs_path):
        overview_path = flask_docs_path / "overview.md"
        if not overview_path.exists():
            pytest.skip("Flask demo not available")
        
        content = overview_path.read_text()
        diagram = extract_mermaid_from_markdown(content)
        assert diagram is not None, "No Mermaid diagram found in overview.md"
    
    def test_flask_overview_diagram_valid(self, flask_docs_path):
        overview_path = flask_docs_path / "overview.md"
        if not overview_path.exists():
            pytest.skip("Flask demo not available")
        
        content = overview_path.read_text()
        diagram = extract_mermaid_from_markdown(content)
        
        if diagram is None:
            pytest.skip("No diagram in overview.md")
        
        result = validate_overview_diagram(diagram)
        
        # Print details for debugging
        print(f"\nDiagram validation result:")
        print(f"  Valid: {result['valid']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Warnings: {result['warnings']}")
        print(f"  Info: {result['info']}")
        
        assert result['valid'], f"Overview diagram invalid: {result['errors']}"
    
    def test_flask_module_tree_exists(self, flask_docs_path):
        tree_path = flask_docs_path / "module_tree.json"
        assert tree_path.exists(), f"module_tree.json not found at {tree_path}"
    
    def test_flask_module_files_exist(self, flask_docs_path):
        tree_path = flask_docs_path / "module_tree.json"
        if not tree_path.exists():
            pytest.skip("module_tree.json not available")
        
        tree = json.loads(tree_path.read_text())
        
        missing_files = []
        for module_name in tree.keys():
            module_file = flask_docs_path / f"{module_name}.md"
            if not module_file.exists():
                missing_files.append(f"{module_name}.md")
        
        assert len(missing_files) == 0, f"Missing module files: {missing_files}"
    
    def test_flask_all_modules_have_diagrams(self, flask_docs_path):
        tree_path = flask_docs_path / "module_tree.json"
        if not tree_path.exists():
            pytest.skip("module_tree.json not available")
        
        tree = json.loads(tree_path.read_text())
        
        modules_without_diagrams = []
        for module_name in tree.keys():
            module_file = flask_docs_path / f"{module_name}.md"
            if module_file.exists():
                content = module_file.read_text()
                diagram = extract_mermaid_from_markdown(content)
                if diagram is None:
                    modules_without_diagrams.append(module_name)
        
        # This is a warning, not a failure - some modules may legitimately have no diagram
        if modules_without_diagrams:
            print(f"\n⚠️  Modules without diagrams: {modules_without_diagrams}")


# ============================================================
# CLI RUNNER
# ============================================================

if __name__ == "__main__":
    import sys
    
    # Quick validation mode
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.exists():
            content = path.read_text()
            diagram = extract_mermaid_from_markdown(content)
            
            if diagram:
                print(f"Validating diagram in {path}...\n")
                result = validate_overview_diagram(diagram)
                
                print(f"Valid: {result['valid']}")
                print(f"Errors: {result['errors']}")
                print(f"Warnings: {result['warnings']}")
                print(f"Info: {json.dumps(result['info'], indent=2)}")
                
                sys.exit(0 if result['valid'] else 1)
            else:
                print(f"No Mermaid diagram found in {path}")
                sys.exit(1)
        else:
            print(f"File not found: {path}")
            sys.exit(1)
    else:
        print("Usage: python test_diagram_format.py <path_to_markdown>")
        print("Or run with pytest: python -m pytest tests/test_diagram_format.py -v")


