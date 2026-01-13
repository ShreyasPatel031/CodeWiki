"""
Tool for listing components in a module.
Used for large repos where the full component list is not included in the prompt.
"""
from pydantic_ai import RunContext, Tool
from codewiki.src.be.agent_tools.deps import CodeWikiDeps
import logging

logger = logging.getLogger(__name__)


def _find_module_in_tree(module_tree: dict, module_name: str) -> dict | None:
    """Recursively find a module in the module tree by name."""
    for key, value in module_tree.items():
        if key == module_name:
            return value
        if isinstance(value.get("children"), dict):
            result = _find_module_in_tree(value["children"], module_name)
            if result:
                return result
    return None


async def list_module_components(ctx: RunContext[CodeWikiDeps], module_name: str) -> str:
    """List all component IDs in a specific module.
    
    Use this when the module tree shows 'N items (use list_module_components to view)'
    for a module you need to understand.
    
    Args:
        module_name: The name of the module to list components for (e.g., 'torch_inductor')
    
    Returns:
        A formatted list of component IDs in that module, grouped by file path.
    """
    logger.info(f"[TOOL] list_module_components called for module: {module_name}")
    
    # Find the module in the tree
    module_info = _find_module_in_tree(ctx.deps.module_tree, module_name)
    
    if not module_info:
        return f"Module '{module_name}' not found in module tree. Available top-level modules: {list(ctx.deps.module_tree.keys())}"
    
    component_ids = module_info.get("components", [])
    
    if not component_ids:
        return f"Module '{module_name}' has no components."
    
    # Group by file path for better readability
    grouped = {}
    for comp_id in component_ids:
        if comp_id in ctx.deps.components:
            path = ctx.deps.components[comp_id].relative_path
            if path not in grouped:
                grouped[path] = []
            grouped[path].append(comp_id)
        else:
            if "_unknown_" not in grouped:
                grouped["_unknown_"] = []
            grouped["_unknown_"].append(comp_id)
    
    # Format output
    lines = [f"# Module: {module_name}"]
    lines.append(f"# Total components: {len(component_ids)}")
    lines.append(f"# Files: {len(grouped)}")
    lines.append("")
    
    for path in sorted(grouped.keys()):
        lines.append(f"## {path}")
        for comp_id in grouped[path]:
            lines.append(f"  - {comp_id}")
        lines.append("")
    
    # Also show children modules if any
    children = module_info.get("children", {})
    if children:
        lines.append("# Child modules:")
        for child_name, child_info in children.items():
            child_count = len(child_info.get("components", []))
            lines.append(f"  - {child_name} ({child_count} components)")
    
    result = "\n".join(lines)
    logger.info(f"[TOOL] list_module_components returning {len(component_ids)} components for {module_name}")
    return result


async def get_module_summary(ctx: RunContext[CodeWikiDeps], module_name: str) -> str:
    """Get a summary of a module including its purpose and structure.
    
    Use this to understand what a module does without reading all its components.
    
    Args:
        module_name: The name of the module to summarize
    
    Returns:
        A summary including component count, file paths, and child modules.
    """
    logger.info(f"[TOOL] get_module_summary called for module: {module_name}")
    
    # Find the module in the tree
    module_info = _find_module_in_tree(ctx.deps.module_tree, module_name)
    
    if not module_info:
        return f"Module '{module_name}' not found in module tree."
    
    component_ids = module_info.get("components", [])
    children = module_info.get("children", {})
    
    # Get unique file paths
    file_paths = set()
    for comp_id in component_ids:
        if comp_id in ctx.deps.components:
            file_paths.add(ctx.deps.components[comp_id].relative_path)
    
    # Build summary
    lines = [f"# Module Summary: {module_name}"]
    lines.append(f"")
    lines.append(f"## Statistics")
    lines.append(f"- Total components: {len(component_ids)}")
    lines.append(f"- Unique files: {len(file_paths)}")
    lines.append(f"- Child modules: {len(children)}")
    lines.append(f"")
    
    if file_paths:
        lines.append(f"## File Paths")
        for path in sorted(file_paths)[:20]:  # Show first 20
            lines.append(f"  - {path}")
        if len(file_paths) > 20:
            lines.append(f"  ... and {len(file_paths) - 20} more files")
        lines.append(f"")
    
    if children:
        lines.append(f"## Child Modules")
        for child_name, child_info in children.items():
            child_count = len(child_info.get("components", []))
            grandchildren = len(child_info.get("children", {}))
            lines.append(f"  - {child_name}: {child_count} components, {grandchildren} sub-modules")
        lines.append(f"")
    
    # Sample some component names to give sense of what's in the module
    if component_ids:
        lines.append(f"## Sample Components (first 10)")
        for comp_id in component_ids[:10]:
            lines.append(f"  - {comp_id}")
        if len(component_ids) > 10:
            lines.append(f"  ... and {len(component_ids) - 10} more")
    
    result = "\n".join(lines)
    logger.info(f"[TOOL] get_module_summary returning summary for {module_name}")
    return result


# Create tool instances
list_module_components_tool = Tool(
    function=list_module_components, 
    name="list_module_components", 
    description="List all component IDs in a specific module. Use when module tree shows 'N items (use list_module_components to view)'.",
    takes_ctx=True
)

get_module_summary_tool = Tool(
    function=get_module_summary,
    name="get_module_summary", 
    description="Get a summary of a module including component count, file paths, and child modules.",
    takes_ctx=True
)



