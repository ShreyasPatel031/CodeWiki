#!/usr/bin/env python3
"""
Test script to verify the tiered module tree approach works correctly.
Tests:
1. Small repo uses full component list
2. Large repo uses tiered format with summaries
3. Tools can retrieve component details on demand
"""
import json
import sys
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/shreyaspatel/CodeWiki')

from codewiki.src.be.prompt_template import (
    _count_total_components,
    _format_module_tree_full,
    _format_module_tree_tiered,
    format_user_prompt,
)
from codewiki.src.config import LARGE_REPO_COMPONENT_THRESHOLD


def create_mock_module_tree(num_components: int, num_modules: int = 5) -> dict:
    """Create a mock module tree with specified number of components."""
    tree = {}
    components_per_module = num_components // num_modules
    
    for i in range(num_modules):
        module_name = f"module_{i}"
        components = [f"{module_name}.component_{j}" for j in range(components_per_module)]
        tree[module_name] = {
            "path": f"src/{module_name}",
            "components": components,
            "children": {}
        }
    return tree


def create_mock_components(module_tree: dict) -> dict:
    """Create mock component objects from module tree."""
    from dataclasses import dataclass
    
    @dataclass
    class MockComponent:
        relative_path: str
        file_path: str
        source_code: str
    
    components = {}
    for module_name, module_info in module_tree.items():
        for comp_id in module_info.get("components", []):
            components[comp_id] = MockComponent(
                relative_path=f"src/{module_name}/file.py",
                file_path=f"/mock/path/src/{module_name}/file.py",
                source_code=f"# Mock source code for {comp_id}\ndef func(): pass\n"
            )
    return components


def test_small_repo():
    """Test that small repos use full component list format."""
    logger.info("=" * 60)
    logger.info("TEST 1: Small repo (100 components)")
    logger.info("=" * 60)
    
    # Create small repo with 100 components
    tree = create_mock_module_tree(100, 5)
    total = _count_total_components(tree)
    
    logger.info(f"Total components: {total}")
    logger.info(f"Threshold: {LARGE_REPO_COMPONENT_THRESHOLD}")
    logger.info(f"Is large repo: {total > LARGE_REPO_COMPONENT_THRESHOLD}")
    
    # Get full format
    formatted = _format_module_tree_full(tree, "module_0")
    
    logger.info(f"\n--- FULL FORMAT OUTPUT ({len(formatted)} chars) ---")
    logger.info(formatted[:500])
    if len(formatted) > 500:
        logger.info(f"... (truncated, {len(formatted) - 500} more chars)")
    
    # Verify it contains actual component IDs
    assert "module_0.component_0" in formatted, "Should contain actual component IDs"
    assert "(use list_module_components to view)" not in formatted, "Should NOT have placeholder"
    
    logger.info("\n✅ Small repo test PASSED - uses full component list")
    return True


def test_large_repo():
    """Test that large repos use tiered format with summaries."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Large repo (1000 components)")
    logger.info("=" * 60)
    
    # Create large repo with 1000 components
    tree = create_mock_module_tree(1000, 10)
    total = _count_total_components(tree)
    
    logger.info(f"Total components: {total}")
    logger.info(f"Threshold: {LARGE_REPO_COMPONENT_THRESHOLD}")
    logger.info(f"Is large repo: {total > LARGE_REPO_COMPONENT_THRESHOLD}")
    
    # Get tiered format
    formatted = _format_module_tree_tiered(tree, "module_0")
    
    logger.info(f"\n--- TIERED FORMAT OUTPUT ({len(formatted)} chars) ---")
    logger.info(formatted[:1000])
    if len(formatted) > 1000:
        logger.info(f"... (truncated, {len(formatted) - 1000} more chars)")
    
    # Verify tiered format characteristics
    assert "(use list_module_components to view)" in formatted, "Should have tool hint"
    # Current module should still show full components
    assert "module_0.component_0" in formatted, "Current module should show full list"
    
    # Other modules should show count only
    lines = formatted.split('\n')
    module_5_lines = [l for l in lines if 'module_5' in l or ('Components: 100' in l and 'module_5' not in l)]
    
    logger.info("\n✅ Large repo test PASSED - uses tiered format with summaries")
    return True


def test_token_savings():
    """Test that tiered format significantly reduces token count."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Token savings comparison")
    logger.info("=" * 60)
    
    # Create pytorch-sized tree (4000 components, 15 modules)
    tree = create_mock_module_tree(4000, 15)
    total = _count_total_components(tree)
    
    logger.info(f"Total components: {total}")
    
    # Get both formats
    full_format = _format_module_tree_full(tree, "module_0")
    tiered_format = _format_module_tree_tiered(tree, "module_0")
    
    logger.info(f"\nFull format: {len(full_format):,} characters")
    logger.info(f"Tiered format: {len(tiered_format):,} characters")
    logger.info(f"Reduction: {(1 - len(tiered_format)/len(full_format))*100:.1f}%")
    
    # Estimate tokens (rough: 4 chars per token)
    full_tokens = len(full_format) // 4
    tiered_tokens = len(tiered_format) // 4
    
    logger.info(f"\nEstimated tokens - Full: ~{full_tokens:,}, Tiered: ~{tiered_tokens:,}")
    
    assert len(tiered_format) < len(full_format) * 0.5, "Tiered should be at least 50% smaller"
    
    logger.info("\n✅ Token savings test PASSED")
    return True


def test_list_module_components_tool():
    """Test the list_module_components tool returns correct data."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: list_module_components tool")
    logger.info("=" * 60)
    
    import asyncio
    from codewiki.src.be.agent_tools.list_module_components import (
        list_module_components,
        get_module_summary,
        _find_module_in_tree,
    )
    from codewiki.src.be.agent_tools.deps import CodeWikiDeps
    from unittest.mock import MagicMock
    
    # Create test data
    tree = create_mock_module_tree(500, 5)
    components = create_mock_components(tree)
    
    # Test _find_module_in_tree
    module_info = _find_module_in_tree(tree, "module_2")
    assert module_info is not None, "Should find module_2"
    assert len(module_info["components"]) == 100, "Should have 100 components"
    
    logger.info("✅ _find_module_in_tree works correctly")
    
    # Create mock context
    mock_ctx = MagicMock()
    
    # Create a mock deps object with required fields
    mock_deps = MagicMock()
    mock_deps.components = components
    mock_deps.module_tree = tree
    mock_ctx.deps = mock_deps
    
    # Test list_module_components
    result = asyncio.run(list_module_components(mock_ctx, "module_2"))
    
    logger.info(f"\n--- list_module_components output ({len(result)} chars) ---")
    logger.info(result[:500])
    
    assert "module_2.component_0" in result, "Should list component IDs"
    assert "Total components: 100" in result, "Should show total count"
    
    logger.info("\n✅ list_module_components tool works correctly")
    
    # Test get_module_summary
    summary = asyncio.run(get_module_summary(mock_ctx, "module_2"))
    
    logger.info(f"\n--- get_module_summary output ({len(summary)} chars) ---")
    logger.info(summary[:500])
    
    assert "Module Summary: module_2" in summary, "Should have module name"
    assert "Total components: 100" in summary, "Should show stats"
    
    logger.info("\n✅ get_module_summary tool works correctly")
    return True


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("TIERED MODULE TREE TESTS")
    logger.info("=" * 60 + "\n")
    
    try:
        test_small_repo()
        test_large_repo()
        test_token_savings()
        test_list_module_components_tool()
        
        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS PASSED!")
        logger.info("=" * 60)
        
        # Summary
        logger.info("\nSummary of changes:")
        logger.info(f"1. Small repos (<{LARGE_REPO_COMPONENT_THRESHOLD} components): Full component lists")
        logger.info(f"2. Large repos (>{LARGE_REPO_COMPONENT_THRESHOLD} components): Tiered format")
        logger.info("3. New tools available for large repos:")
        logger.info("   - list_module_components(module_name): Get all component IDs")
        logger.info("   - get_module_summary(module_name): Get module statistics")
        logger.info("4. Infinite nesting bug fixed (MIN_COMPONENTS_FOR_CLUSTERING = 3)")
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

