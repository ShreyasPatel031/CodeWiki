#!/usr/bin/env python3
"""
Test Go AST Parser using tree-sitter-go

Tests parsing of KubeElasti Go files to verify:
1. Struct extraction
2. Interface extraction  
3. Function extraction
4. Method extraction (with receivers)
5. Call relationships
"""

import logging
from typing import List, Tuple
from pathlib import Path
import os

from tree_sitter import Parser, Language
import tree_sitter_go

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Go code from KubeElasti
SAMPLE_GO_CODE = '''
package controller

import (
	"context"
	"sync"
	"time"

	"github.com/truefoundry/elasti/pkg/scaling"
	"k8s.io/apimachinery/pkg/types"
)

type (
	SwitchModeFunc          func(ctx context.Context, req ctrl.Request, mode string) (res ctrl.Result, err error)
	ElastiServiceReconciler struct {
		client.Client
		Scheme             *kRuntime.Scheme
		Logger             *zap.Logger
		InformerManager    *informer.Manager
		SwitchModeLocks    sync.Map
		ScaleHandler       *scaling.ScaleHandler
	}
)

// Manager handles informer operations
type Manager interface {
	Start(ctx context.Context) error
	Stop() error
	GetInformer(name string) Informer
}

// Reconcile is part of the main kubernetes reconciliation loop
func (r *ElastiServiceReconciler) Reconcile(ctx context.Context, req ctrl.Request) (res ctrl.Result, err error) {
	r.Logger.Debug("- In Reconcile", zap.String("es", req.NamespacedName.String()))
	mutex := r.getMutexForReconcile(req.NamespacedName.String())
	mutex.Lock()
	defer mutex.Unlock()
	
	es, esErr := r.getCRD(ctx, req.NamespacedName)
	if esErr != nil {
		return res, esErr
	}
	
	return res, nil
}

// getMutexForReconcile gets or creates a mutex for reconciliation
func (r *ElastiServiceReconciler) getMutexForReconcile(name string) *sync.Mutex {
	if mutex, ok := r.ReconcileLocks.Load(name); ok {
		return mutex.(*sync.Mutex)
	}
	newMutex := &sync.Mutex{}
	r.ReconcileLocks.Store(name, newMutex)
	return newMutex
}

// NewReconciler creates a new ElastiServiceReconciler
func NewReconciler(client client.Client, scheme *kRuntime.Scheme) *ElastiServiceReconciler {
	return &ElastiServiceReconciler{
		Client: client,
		Scheme: scheme,
	}
}
'''


class GoNode:
    """Represents a parsed Go node."""
    def __init__(self, id: str, name: str, node_type: str, start_line: int, end_line: int, source: str = ""):
        self.id = id
        self.name = name
        self.node_type = node_type
        self.start_line = start_line
        self.end_line = end_line
        self.source = source
    
    def __repr__(self):
        return f"GoNode({self.node_type}: {self.name}, lines {self.start_line}-{self.end_line})"


class GoRelationship:
    """Represents a relationship between Go nodes."""
    def __init__(self, caller: str, callee: str, call_line: int):
        self.caller = caller
        self.callee = callee
        self.call_line = call_line
    
    def __repr__(self):
        return f"GoRelationship({self.caller} -> {self.callee} at line {self.call_line})"


class TreeSitterGoAnalyzer:
    """Analyzer for Go files using tree-sitter."""
    
    def __init__(self, content: str, file_path: str = "test.go"):
        self.content = content
        self.file_path = file_path
        self.nodes: List[GoNode] = []
        self.relationships: List[GoRelationship] = []
        self._analyze()
    
    def _analyze(self):
        """Parse and analyze the Go code."""
        language_capsule = tree_sitter_go.language()
        go_language = Language(language_capsule)
        parser = Parser(go_language)
        tree = parser.parse(bytes(self.content, "utf8"))
        root = tree.root_node
        lines = self.content.splitlines()
        
        logger.info(f"Parsing Go file: {self.file_path}")
        logger.info(f"Root node type: {root.type}, children: {len(root.children)}")
        
        self._extract_nodes(root, lines)
        self._extract_relationships(root)
    
    def _extract_nodes(self, node, lines, depth=0):
        """Extract structs, interfaces, functions, and methods."""
        indent = "  " * depth
        
        # Type declarations (struct, interface)
        if node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = next((c for c in child.children if c.type == "type_identifier"), None)
                    type_node = next((c for c in child.children if c.type in ["struct_type", "interface_type"]), None)
                    
                    if name_node and type_node:
                        name = name_node.text.decode()
                        node_type = "struct" if type_node.type == "struct_type" else "interface"
                        
                        self.nodes.append(GoNode(
                            id=f"{self.file_path}.{name}",
                            name=name,
                            node_type=node_type,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            source="\n".join(lines[node.start_point[0]:node.end_point[0]+1])
                        ))
                        logger.info(f"{indent}Found {node_type}: {name}")
        
        # Function declarations
        elif node.type == "function_declaration":
            name_node = next((c for c in node.children if c.type == "identifier"), None)
            if name_node:
                name = name_node.text.decode()
                self.nodes.append(GoNode(
                    id=f"{self.file_path}.{name}",
                    name=name,
                    node_type="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    source="\n".join(lines[node.start_point[0]:node.end_point[0]+1])
                ))
                logger.info(f"{indent}Found function: {name}")
        
        # Method declarations
        elif node.type == "method_declaration":
            name_node = next((c for c in node.children if c.type == "field_identifier"), None)
            receiver_node = next((c for c in node.children if c.type == "parameter_list"), None)
            
            if name_node:
                method_name = name_node.text.decode()
                receiver_type = self._get_receiver_type(receiver_node) if receiver_node else None
                
                full_name = f"{receiver_type}.{method_name}" if receiver_type else method_name
                
                self.nodes.append(GoNode(
                    id=f"{self.file_path}.{full_name}",
                    name=full_name,
                    node_type="method",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    source="\n".join(lines[node.start_point[0]:node.end_point[0]+1])
                ))
                logger.info(f"{indent}Found method: {full_name}")
        
        # Recurse into children
        for child in node.children:
            self._extract_nodes(child, lines, depth + 1)
    
    def _get_receiver_type(self, param_list):
        """Extract receiver type from method receiver parameter list."""
        for child in param_list.children:
            if child.type == "parameter_declaration":
                type_node = next((c for c in child.children 
                    if c.type in ["type_identifier", "pointer_type"]), None)
                if type_node:
                    if type_node.type == "pointer_type":
                        inner = next((c for c in type_node.children 
                            if c.type == "type_identifier"), None)
                        return inner.text.decode() if inner else None
                    return type_node.text.decode()
        return None
    
    def _extract_relationships(self, node):
        """Extract call relationships."""
        if node.type == "call_expression":
            containing_func = self._find_containing_function(node)
            if containing_func:
                func_node = next((c for c in node.children 
                    if c.type in ["identifier", "selector_expression"]), None)
                
                if func_node:
                    if func_node.type == "selector_expression":
                        # Method call: obj.Method()
                        field = next((c for c in func_node.children if c.type == "field_identifier"), None)
                        if field:
                            method_name = field.text.decode()
                            self.relationships.append(GoRelationship(
                                caller=containing_func,
                                callee=method_name,
                                call_line=node.start_point[0] + 1
                            ))
                    else:
                        # Direct function call
                        func_name = func_node.text.decode()
                        self.relationships.append(GoRelationship(
                            caller=containing_func,
                            callee=func_name,
                            call_line=node.start_point[0] + 1
                        ))
        
        for child in node.children:
            self._extract_relationships(child)
    
    def _find_containing_function(self, node):
        """Find the containing function/method for a node."""
        current = node.parent
        while current:
            if current.type == "function_declaration":
                name_node = next((c for c in current.children if c.type == "identifier"), None)
                if name_node:
                    return name_node.text.decode()
            elif current.type == "method_declaration":
                name_node = next((c for c in current.children if c.type == "field_identifier"), None)
                receiver = next((c for c in current.children if c.type == "parameter_list"), None)
                if name_node:
                    receiver_type = self._get_receiver_type(receiver) if receiver else None
                    method_name = name_node.text.decode()
                    return f"{receiver_type}.{method_name}" if receiver_type else method_name
            current = current.parent
        return None


def test_go_parser():
    """Test the Go parser with sample code."""
    print("=" * 60)
    print("Testing Go Parser with KubeElasti-style code")
    print("=" * 60)
    
    analyzer = TreeSitterGoAnalyzer(SAMPLE_GO_CODE)
    
    print("\n" + "=" * 60)
    print("EXTRACTED NODES:")
    print("=" * 60)
    
    structs = [n for n in analyzer.nodes if n.node_type == "struct"]
    interfaces = [n for n in analyzer.nodes if n.node_type == "interface"]
    functions = [n for n in analyzer.nodes if n.node_type == "function"]
    methods = [n for n in analyzer.nodes if n.node_type == "method"]
    
    print(f"\nStructs ({len(structs)}):")
    for s in structs:
        print(f"  - {s.name} (lines {s.start_line}-{s.end_line})")
    
    print(f"\nInterfaces ({len(interfaces)}):")
    for i in interfaces:
        print(f"  - {i.name} (lines {i.start_line}-{i.end_line})")
    
    print(f"\nFunctions ({len(functions)}):")
    for f in functions:
        print(f"  - {f.name} (lines {f.start_line}-{f.end_line})")
    
    print(f"\nMethods ({len(methods)}):")
    for m in methods:
        print(f"  - {m.name} (lines {m.start_line}-{m.end_line})")
    
    print("\n" + "=" * 60)
    print("EXTRACTED RELATIONSHIPS:")
    print("=" * 60)
    
    for r in analyzer.relationships:
        print(f"  {r.caller} -> {r.callee} (line {r.call_line})")
    
    # Assertions
    print("\n" + "=" * 60)
    print("TESTS:")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    def assert_test(name, condition):
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✅ {name}")
            tests_passed += 1
        else:
            print(f"  ❌ {name}")
            tests_failed += 1
    
    # Test struct extraction
    assert_test("Found ElastiServiceReconciler struct", 
                any(n.name == "ElastiServiceReconciler" and n.node_type == "struct" for n in analyzer.nodes))
    
    # Test interface extraction
    assert_test("Found Manager interface",
                any(n.name == "Manager" and n.node_type == "interface" for n in analyzer.nodes))
    
    # Test function extraction
    assert_test("Found NewReconciler function",
                any(n.name == "NewReconciler" and n.node_type == "function" for n in analyzer.nodes))
    
    # Test method extraction with receiver
    assert_test("Found ElastiServiceReconciler.Reconcile method",
                any(n.name == "ElastiServiceReconciler.Reconcile" and n.node_type == "method" for n in analyzer.nodes))
    
    assert_test("Found ElastiServiceReconciler.getMutexForReconcile method",
                any(n.name == "ElastiServiceReconciler.getMutexForReconcile" and n.node_type == "method" for n in analyzer.nodes))
    
    # Test relationships
    assert_test("Found call relationships",
                len(analyzer.relationships) > 0)
    
    # Test method calls are captured
    assert_test("Captured method call to Debug",
                any(r.callee == "Debug" for r in analyzer.relationships))
    
    assert_test("Captured method call to Lock",
                any(r.callee == "Lock" for r in analyzer.relationships))
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)
    
    return tests_failed == 0


def test_real_kubeelasti_file():
    """Test with actual KubeElasti file if available."""
    kubeelasti_file = "/Users/shreyaspatel/CodeWiki/test_repos/KubeElasti/operator/internal/controller/elastiservice_controller.go"
    
    if not os.path.exists(kubeelasti_file):
        print(f"\nSkipping real file test - {kubeelasti_file} not found")
        return True
    
    print("\n" + "=" * 60)
    print("Testing with REAL KubeElasti file")
    print("=" * 60)
    
    with open(kubeelasti_file, 'r') as f:
        content = f.read()
    
    analyzer = TreeSitterGoAnalyzer(content, kubeelasti_file)
    
    print(f"\nTotal nodes extracted: {len(analyzer.nodes)}")
    print(f"  - Structs: {len([n for n in analyzer.nodes if n.node_type == 'struct'])}")
    print(f"  - Interfaces: {len([n for n in analyzer.nodes if n.node_type == 'interface'])}")
    print(f"  - Functions: {len([n for n in analyzer.nodes if n.node_type == 'function'])}")
    print(f"  - Methods: {len([n for n in analyzer.nodes if n.node_type == 'method'])}")
    print(f"\nTotal relationships: {len(analyzer.relationships)}")
    
    # Should find at least some nodes
    if len(analyzer.nodes) == 0:
        print("  ❌ No nodes found in real file!")
        return False
    else:
        print("  ✅ Successfully parsed real KubeElasti file!")
        return True


if __name__ == "__main__":
    success = test_go_parser()
    success = test_real_kubeelasti_file() and success
    
    if success:
        print("\n🎉 All tests passed! Go parser is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above.")
    
    exit(0 if success else 1)
