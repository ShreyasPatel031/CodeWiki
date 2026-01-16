"""
Go language analyzer using tree-sitter for AST parsing.
Extracts structs, interfaces, functions, and methods from Go source files.
"""
import logging
from typing import List, Tuple
from pathlib import Path
import os

from tree_sitter import Parser, Language
import tree_sitter_go
from codewiki.src.be.dependency_analyzer.models.core import Node, CallRelationship

logger = logging.getLogger(__name__)


class TreeSitterGoAnalyzer:
    """Analyzer for Go source files using tree-sitter."""
    
    def __init__(self, file_path: str, content: str, repo_path: str = None):
        self.file_path = Path(file_path)
        self.content = content
        self.repo_path = repo_path or ""
        self.nodes: List[Node] = []
        self.call_relationships: List[CallRelationship] = []
        self._analyze()
    
    def _get_module_path(self) -> str:
        """Get module path from file path."""
        if self.repo_path:
            try:
                rel_path = os.path.relpath(str(self.file_path), self.repo_path)
            except ValueError:
                rel_path = str(self.file_path)
        else:
            rel_path = str(self.file_path)
        
        # Remove .go extension
        if rel_path.endswith('.go'):
            rel_path = rel_path[:-3]
        
        return rel_path.replace('/', '.').replace('\\', '.')
    
    def _get_relative_path(self) -> str:
        """Get relative path from repo root."""
        if self.repo_path:
            try:
                return os.path.relpath(str(self.file_path), self.repo_path)
            except ValueError:
                return str(self.file_path)
        return str(self.file_path)
    
    def _get_component_id(self, name: str, parent_type: str = None) -> str:
        """Generate dot-separated component ID."""
        module_path = self._get_module_path()
        if parent_type:
            return f"{module_path}.{parent_type}.{name}"
        return f"{module_path}.{name}"
    
    def _analyze(self):
        """Parse the Go file and extract nodes and relationships."""
        language_capsule = tree_sitter_go.language()
        go_language = Language(language_capsule)
        parser = Parser(go_language)
        tree = parser.parse(bytes(self.content, "utf8"))
        root = tree.root_node
        lines = self.content.splitlines()
        
        top_level_nodes = {}
        
        self._extract_nodes(root, top_level_nodes, lines)
        self._extract_relationships(root, top_level_nodes)
    
    def _extract_nodes(self, node, top_level_nodes, lines):
        """Extract struct, interface, function, and method definitions."""
        node_type = None
        node_name = None
        
        # Struct type declaration
        if node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = next((c for c in child.children if c.type == "type_identifier"), None)
                    type_node = next((c for c in child.children if c.type in ["struct_type", "interface_type"]), None)
                    
                    if name_node and type_node:
                        node_name = name_node.text.decode()
                        if type_node.type == "struct_type":
                            node_type = "struct"
                        elif type_node.type == "interface_type":
                            node_type = "interface"
        
        # Function declaration
        elif node.type == "function_declaration":
            name_node = next((c for c in node.children if c.type == "identifier"), None)
            if name_node:
                node_name = name_node.text.decode()
                node_type = "function"
        
        # Method declaration (function with receiver)
        elif node.type == "method_declaration":
            name_node = next((c for c in node.children if c.type == "field_identifier"), None)
            receiver_node = next((c for c in node.children if c.type == "parameter_list"), None)
            
            if name_node and receiver_node:
                method_name = name_node.text.decode()
                receiver_type = self._extract_receiver_type(receiver_node)
                if receiver_type:
                    node_name = f"{receiver_type}.{method_name}"
                    node_type = "method"
        
        if node_type and node_name:
            component_id = self._get_component_id(node_name)
            relative_path = self._get_relative_path()
            
            node_obj = Node(
                id=component_id,
                name=node_name,
                component_type=node_type,
                file_path=str(self.file_path),
                relative_path=relative_path,
                source_code="\n".join(lines[node.start_point[0]:node.end_point[0]+1]),
                start_line=node.start_point[0]+1,
                end_line=node.end_point[0]+1,
                has_docstring=False,
                docstring="",
                parameters=None,
                node_type=node_type,
                base_classes=None,
                class_name=None,
                display_name=f"{node_type} {node_name}",
                component_id=component_id
            )
            self.nodes.append(node_obj)
            top_level_nodes[node_name] = node_obj
        
        # Recursively process children
        for child in node.children:
            self._extract_nodes(child, top_level_nodes, lines)
    
    def _extract_receiver_type(self, param_list) -> str:
        """Extract the receiver type from a method's parameter list."""
        for child in param_list.children:
            if child.type == "parameter_declaration":
                # Look for type_identifier or pointer_type
                for param_child in child.children:
                    if param_child.type == "type_identifier":
                        return param_child.text.decode()
                    elif param_child.type == "pointer_type":
                        type_id = next((c for c in param_child.children if c.type == "type_identifier"), None)
                        if type_id:
                            return type_id.text.decode()
        return None
    
    def _extract_relationships(self, node, top_level_nodes):
        """Extract call relationships between components."""
        
        # Interface embedding
        if node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = next((c for c in child.children if c.type == "type_identifier"), None)
                    interface_node = next((c for c in child.children if c.type == "interface_type"), None)
                    
                    if name_node and interface_node:
                        interface_name = name_node.text.decode()
                        # Find embedded interfaces
                        for iface_child in interface_node.children:
                            if iface_child.type == "type_identifier":
                                embedded_name = iface_child.text.decode()
                                if not self._is_builtin_type(embedded_name):
                                    self.call_relationships.append(CallRelationship(
                                        caller=self._get_component_id(interface_name),
                                        callee=self._get_component_id(embedded_name),
                                        call_line=node.start_point[0]+1,
                                        is_resolved=False
                                    ))
        
        # Struct embedding and field types
        if node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = next((c for c in child.children if c.type == "type_identifier"), None)
                    struct_node = next((c for c in child.children if c.type == "struct_type"), None)
                    
                    if name_node and struct_node:
                        struct_name = name_node.text.decode()
                        self._extract_struct_dependencies(struct_node, struct_name, top_level_nodes)
        
        # Function/method calls
        if node.type == "call_expression":
            containing = self._find_containing_func_or_method(node, top_level_nodes)
            if containing:
                callee = self._extract_call_target(node)
                if callee and not self._is_builtin_type(callee):
                    self.call_relationships.append(CallRelationship(
                        caller=containing,
                        callee=self._get_component_id(callee),
                        call_line=node.start_point[0]+1,
                        is_resolved=False
                    ))
        
        # Recursively process children
        for child in node.children:
            self._extract_relationships(child, top_level_nodes)
    
    def _extract_struct_dependencies(self, struct_node, struct_name, top_level_nodes):
        """Extract dependencies from struct field types."""
        for child in struct_node.children:
            if child.type == "field_declaration_list":
                for field in child.children:
                    if field.type == "field_declaration":
                        type_name = self._extract_type_from_field(field)
                        if type_name and not self._is_builtin_type(type_name):
                            self.call_relationships.append(CallRelationship(
                                caller=self._get_component_id(struct_name),
                                callee=self._get_component_id(type_name),
                                call_line=field.start_point[0]+1,
                                is_resolved=False
                            ))
    
    def _extract_type_from_field(self, field) -> str:
        """Extract type name from a field declaration."""
        for child in field.children:
            if child.type == "type_identifier":
                return child.text.decode()
            elif child.type == "pointer_type":
                type_id = next((c for c in child.children if c.type == "type_identifier"), None)
                if type_id:
                    return type_id.text.decode()
            elif child.type == "slice_type":
                element = next((c for c in child.children if c.type == "type_identifier"), None)
                if element:
                    return element.text.decode()
            elif child.type == "map_type":
                # Get the value type for maps
                for map_child in child.children:
                    if map_child.type == "type_identifier":
                        return map_child.text.decode()
        return None
    
    def _extract_call_target(self, call_node) -> str:
        """Extract the target of a function/method call."""
        func = next((c for c in call_node.children if c.type == "identifier"), None)
        if func:
            return func.text.decode()
        
        # Method call: obj.Method()
        selector = next((c for c in call_node.children if c.type == "selector_expression"), None)
        if selector:
            field = next((c for c in selector.children if c.type == "field_identifier"), None)
            if field:
                return field.text.decode()
        
        return None
    
    def _find_containing_func_or_method(self, node, top_level_nodes) -> str:
        """Find the containing function or method for a node."""
        current = node.parent
        while current:
            if current.type == "function_declaration":
                name_node = next((c for c in current.children if c.type == "identifier"), None)
                if name_node:
                    return self._get_component_id(name_node.text.decode())
            elif current.type == "method_declaration":
                name_node = next((c for c in current.children if c.type == "field_identifier"), None)
                receiver_node = next((c for c in current.children if c.type == "parameter_list"), None)
                if name_node and receiver_node:
                    method_name = name_node.text.decode()
                    receiver_type = self._extract_receiver_type(receiver_node)
                    if receiver_type:
                        return self._get_component_id(f"{receiver_type}.{method_name}")
            current = current.parent
        return None
    
    def _is_builtin_type(self, type_name: str) -> bool:
        """Check if type is a Go built-in type."""
        builtins = {
            "bool", "byte", "complex64", "complex128", "error", "float32", "float64",
            "int", "int8", "int16", "int32", "int64", "rune", "string",
            "uint", "uint8", "uint16", "uint32", "uint64", "uintptr",
            "any", "comparable", "nil", "true", "false", "iota"
        }
        return type_name in builtins


def analyze_go_file(file_path: str, content: str, repo_path: str = None) -> Tuple[List[Node], List[CallRelationship]]:
    """Analyze a Go file and return nodes and call relationships."""
    analyzer = TreeSitterGoAnalyzer(file_path, content, repo_path)
    return analyzer.nodes, analyzer.call_relationships
