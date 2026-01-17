from pydantic_ai import RunContext, Tool, Agent

from codewiki.src.be.agent_tools.deps import CodeWikiDeps
from codewiki.src.be.agent_tools.read_code_components import read_code_components_tool
from codewiki.src.be.agent_tools.str_replace_editor import str_replace_editor_tool
from codewiki.src.be.llm_services import create_fallback_models
from codewiki.src.be.prompt_template import SYSTEM_PROMPT, LEAF_SYSTEM_PROMPT, format_user_prompt
from codewiki.src.be.utils import is_complex_module, count_module_tokens
from codewiki.src.config import MAX_TOKEN_PER_LEAF_MODULE, MIN_DEPTH

import logging
import os
from collections import defaultdict
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def _auto_split_by_directory(
    component_ids: List[str],
    components: Dict[str, Any],
    current_depth: int
) -> Dict[str, List[str]]:
    """
    Auto-split components by directory path at the appropriate depth level.
    Returns a dict mapping sub-module names to their component IDs.
    """
    # Group by directory component at current_depth level
    groups = defaultdict(list)
    
    for comp_id in component_ids:
        if comp_id not in components:
            continue
        
        component = components[comp_id]
        path = component.relative_path
        parts = path.split(os.sep)
        
        # Use directory at current_depth + 1 level (since we're creating children)
        depth_for_split = current_depth
        if len(parts) > depth_for_split:
            key = parts[depth_for_split]
            # Clean the key for module naming
            key = key.lower().replace("-", "_").replace(".", "_").replace(" ", "_")
            if not key:
                key = "other"
        else:
            key = "other"
        
        groups[key].append(comp_id)
    
    # Filter out groups with only 1 component (not worth splitting)
    result = {k: v for k, v in groups.items() if len(v) >= 1}
    
    # Only return if we have more than 1 group (actual split happened)
    if len(result) <= 1:
        return {}
    
    return result



async def generate_sub_module_documentation(
    ctx: RunContext[CodeWikiDeps],
    sub_module_specs: dict[str, list[str]]
) -> str:
    """Generate detailed description of a given sub-module specs to the sub-agents

    Args:
        sub_module_specs: The specs of the sub-modules to generate documentation for. E.g. {"sub_module_1": ["core_component_1.1", "core_component_1.2"], "sub_module_2": ["core_component_2.1", "core_component_2.2"], ...}
    """

    deps = ctx.deps
    previous_module_name = deps.current_module_name
    
    # Create fallback models from config
    fallback_models = create_fallback_models(deps.config)

    # add the sub-module to the module tree
    value = deps.module_tree
    for key in deps.path_to_current_module:
        value = value[key]["children"]
    for sub_module_name, core_component_ids in sub_module_specs.items():
        value[sub_module_name] = {"components": core_component_ids, "children": {}}
    
    for sub_module_name, core_component_ids in sub_module_specs.items():

        # Create visual indentation for nested modules
        indent = "  " * deps.current_depth
        arrow = "└─" if deps.current_depth > 0 else "→"

        logger.info(f"{indent}{arrow} Generating documentation for sub-module: {sub_module_name}")

        # Use centralized token counting that matches the actual LLM prompt format
        num_tokens = count_module_tokens(core_component_ids, ctx.deps.components)
        
        # Force sub-agent creation until MIN_DEPTH is reached
        # After MIN_DEPTH, apply normal criteria (complex module, token threshold)
        force_subagent = ctx.deps.current_depth < MIN_DEPTH and len(core_component_ids) >= 2
        normal_criteria = (
            is_complex_module(ctx.deps.components, core_component_ids) and 
            ctx.deps.current_depth < ctx.deps.max_depth and 
            num_tokens >= MAX_TOKEN_PER_LEAF_MODULE
        )
        
        if force_subagent or normal_criteria:
            logger.info(f"{indent}  Using complex agent (force={force_subagent}, normal={normal_criteria}, depth={ctx.deps.current_depth}, min_depth={MIN_DEPTH})")
            sub_agent = Agent(
                model=fallback_models,
                name=sub_module_name,
                deps_type=CodeWikiDeps,
                system_prompt=SYSTEM_PROMPT.format(module_name=sub_module_name),
                tools=[read_code_components_tool, str_replace_editor_tool, generate_sub_module_documentation_tool],
            )
        else:
            logger.info(f"{indent}  Using leaf agent (depth={ctx.deps.current_depth}, tokens={num_tokens})")
            sub_agent = Agent(
                model=fallback_models,
                name=sub_module_name,
                deps_type=CodeWikiDeps,
                system_prompt=LEAF_SYSTEM_PROMPT.format(module_name=sub_module_name),
                tools=[read_code_components_tool, str_replace_editor_tool],
            )

        deps.current_module_name = sub_module_name
        deps.path_to_current_module.append(sub_module_name)
        deps.current_depth += 1
        # log the current module tree
        # print(f"Current module tree: {json.dumps(deps.module_tree, indent=4)}")

        result = await sub_agent.run(
            format_user_prompt(
                module_name=deps.current_module_name,
                core_component_ids=core_component_ids,
                components=ctx.deps.components,
                module_tree=ctx.deps.module_tree,
            ),
            deps=ctx.deps
        )
        
        # FORCE sub-module creation if depth < MIN_DEPTH and agent didn't create any
        # This ensures we always reach MIN_DEPTH levels
        current_module_children = value[sub_module_name].get("children", {})
        if force_subagent and len(current_module_children) == 0 and len(core_component_ids) >= 2:
            logger.info(f"{indent}  Agent did not create sub-modules, forcing directory-based split at depth {deps.current_depth}")
            # Auto-split by directory path component at this depth
            auto_split = _auto_split_by_directory(core_component_ids, ctx.deps.components, deps.current_depth)
            if auto_split and len(auto_split) > 1:
                logger.info(f"{indent}  Auto-split created {len(auto_split)} sub-modules: {list(auto_split.keys())}")
                # Recursively process auto-split modules
                await generate_sub_module_documentation(ctx, auto_split)

        # remove the sub-module name from the path to current module and the module tree
        deps.path_to_current_module.pop()
        deps.current_depth -= 1

    # restore the previous module name
    deps.current_module_name = previous_module_name

    return f"Generate successfully. Documentations: {', '.join([key + '.md' for key in sub_module_specs.keys()])} are saved in the working directory."


generate_sub_module_documentation_tool = Tool(function=generate_sub_module_documentation, name="generate_sub_module_documentation", description="Generate detailed description of a given sub-module specs to the sub-agents", takes_ctx=True)