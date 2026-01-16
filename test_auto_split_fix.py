#!/usr/bin/env python3
"""
Quick test to verify the auto-split module tree update logic is correct.
This simulates the conditions without actually running LLM calls.
"""

import json
import copy

def test_auto_split_module_tree_update():
    """
    Simulates the auto-split logic to verify module tree updates work correctly.
    """
    
    # Simulate a module tree like pytorch's - flat with empty children
    original_module_tree = {
        "aten": {
            "path": "aten",
            "components": ["comp1", "comp2", "comp3"],  # Normally 967 components
            "children": {}
        },
        "torch": {
            "path": "torch",
            "components": ["comp4", "comp5"],
            "children": {}
        },
        "c10": {
            "path": "c10",
            "components": ["comp6"],
            "children": {}
        }
    }
    
    # Simulate auto-split creating sub-modules for "aten"
    sub_modules = {
        "part_1": {"components": ["comp1"]},
        "part_2": {"components": ["comp2"]},
        "part_3": {"components": ["comp3"]}
    }
    
    module_name = "aten"
    module_path = ["aten"]  # Top-level module path
    
    # ========== OLD BUGGY CODE ==========
    buggy_tree = copy.deepcopy(original_module_tree)
    
    value = buggy_tree
    for key in module_path:
        if key in value:
            value = value[key].get("children", {})
    
    # This check fails because value is now {} (children of aten)
    if module_name in value:
        value[module_name]["children"] = {}
        for sub_name, sub_info in sub_modules.items():
            value[module_name]["children"][sub_name] = {
                "components": sub_info["components"],
                "children": {}
            }
        print("BUGGY CODE: Updated children (this should NOT happen)")
    else:
        print(f"BUGGY CODE: Module '{module_name}' NOT found in value: {list(value.keys())}")
    
    # ========== NEW FIXED CODE ==========
    fixed_tree = copy.deepcopy(original_module_tree)
    
    if len(module_path) == 0:
        target = fixed_tree
    elif len(module_path) == 1:
        # Top-level module - module is directly in module_tree
        target = fixed_tree
    else:
        # Nested module - navigate to parent's children
        target = fixed_tree
        for key in module_path[:-1]:
            if key in target:
                target = target[key].get("children", {})
    
    if module_name in target:
        target[module_name]["children"] = {}
        for sub_name, sub_info in sub_modules.items():
            target[module_name]["children"][sub_name] = {
                "components": sub_info["components"],
                "children": {}
            }
        print(f"FIXED CODE: Successfully updated '{module_name}' with {len(sub_modules)} children")
    else:
        print(f"FIXED CODE: BUG - Module '{module_name}' not found in target: {list(target.keys())}")
    
    # ========== VERIFY RESULTS ==========
    print("\n=== VERIFICATION ===")
    print(f"Buggy tree 'aten' children: {buggy_tree['aten']['children']}")
    print(f"Fixed tree 'aten' children: {json.dumps(fixed_tree['aten']['children'], indent=2)}")
    
    # Test nested module path
    print("\n=== TEST NESTED MODULE ===")
    # Simulate nested: module_path = ["aten", "part_1"], module_name = "sub_part"
    nested_tree = copy.deepcopy(fixed_tree)
    nested_module_path = ["aten", "part_1"]
    nested_module_name = "part_1"
    nested_sub_modules = {"sub_a": {"components": ["comp1a"]}, "sub_b": {"components": ["comp1b"]}}
    
    if len(nested_module_path) == 0:
        target = nested_tree
    elif len(nested_module_path) == 1:
        target = nested_tree
    else:
        target = nested_tree
        for key in nested_module_path[:-1]:
            if key in target:
                target = target[key].get("children", {})
    
    if nested_module_name in target:
        target[nested_module_name]["children"] = {}
        for sub_name, sub_info in nested_sub_modules.items():
            target[nested_module_name]["children"][sub_name] = {
                "components": sub_info["components"],
                "children": {}
            }
        print(f"NESTED: Successfully updated '{nested_module_name}' with {len(nested_sub_modules)} children")
    else:
        print(f"NESTED: BUG - Module '{nested_module_name}' not found in target: {list(target.keys())}")
    
    print(f"\nFinal nested tree structure:")
    print(json.dumps(nested_tree, indent=2))
    
    # Assertions
    assert buggy_tree["aten"]["children"] == {}, "Buggy code should have empty children"
    assert len(fixed_tree["aten"]["children"]) == 3, "Fixed code should have 3 children"
    assert "part_1" in fixed_tree["aten"]["children"], "Should have part_1"
    assert "part_2" in fixed_tree["aten"]["children"], "Should have part_2"
    assert "part_3" in fixed_tree["aten"]["children"], "Should have part_3"
    
    # Check nested
    assert len(nested_tree["aten"]["children"]["part_1"]["children"]) == 2, "Nested should have 2 children"
    
    print("\n✅ ALL TESTS PASSED - Fix is correct!")

if __name__ == "__main__":
    test_auto_split_module_tree_update()





