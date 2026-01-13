from typing import List, Dict, Any
from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

from codewiki.src.be.dependency_analyzer.models.core import Node
from codewiki.src.be.llm_services import call_llm
from codewiki.src.be.utils import count_tokens, count_module_tokens
from codewiki.src.config import (
    MAX_TOKEN_PER_MODULE, 
    MIN_COMPONENTS_FOR_CLUSTERING,
    MAX_CLUSTERING_PROMPT_TOKENS,
    Config
)
from codewiki.src.be.prompt_template import format_cluster_prompt


def _create_directory_based_modules(
    leaf_nodes: List[str],
    components: Dict[str, Node],
    current_module_name: str = None
) -> Dict[str, Any]:
    """
    Create modules based on directory structure when LLM clustering fails.
    This is a deterministic fallback that doesn't require LLM calls.
    
    Groups components by their top-level directory, creating manageable modules.
    """
    from collections import defaultdict
    import os
    
    logger.info(f"[STAGE 2 FALLBACK] Creating directory-based modules for {len(leaf_nodes)} leaf nodes")
    
    # Group leaf nodes by their top-level directory
    dir_groups = defaultdict(list)
    
    for leaf_node in leaf_nodes:
        if leaf_node not in components:
            continue
        
        component = components[leaf_node]
        path = component.relative_path
        
        # Get top-level directory (or file name if no directory)
        parts = path.split(os.sep)
        if len(parts) > 1:
            # Use first directory level
            top_dir = parts[0]
        else:
            # Single file, use filename without extension
            top_dir = os.path.splitext(parts[0])[0] if parts else "root"
        
        dir_groups[top_dir].append(leaf_node)
    
    # If we have too few groups, try second-level directories
    if len(dir_groups) <= 2 and any(len(v) > 500 for v in dir_groups.values()):
        logger.info(f"[STAGE 2 FALLBACK] Too few groups ({len(dir_groups)}), trying second-level directories")
        dir_groups = defaultdict(list)
        
        for leaf_node in leaf_nodes:
            if leaf_node not in components:
                continue
            
            component = components[leaf_node]
            path = component.relative_path
            parts = path.split(os.sep)
            
            if len(parts) > 2:
                # Use first two directory levels
                key = f"{parts[0]}_{parts[1]}"
            elif len(parts) > 1:
                key = parts[0]
            else:
                key = os.path.splitext(parts[0])[0] if parts else "root"
            
            dir_groups[key].append(leaf_node)
    
    # Convert to module tree format
    module_tree = {}
    for dir_name, node_list in dir_groups.items():
        # Create clean module name
        module_name = dir_name.lower().replace("-", "_").replace(".", "_").replace(" ", "_")
        if not module_name:
            module_name = "other"
        
        # Skip empty modules
        if not node_list:
            continue
        
        module_tree[module_name] = {
            "path": dir_name,
            "components": node_list,
            "children": {}
        }
    
    logger.info(f"[STAGE 2 FALLBACK] Created {len(module_tree)} directory-based modules:")
    for name, info in module_tree.items():
        logger.info(f"[STAGE 2 FALLBACK]   - {name}: {len(info['components'])} components")
    
    # If still no modules, create a single fallback module
    if not module_tree:
        fallback_name = current_module_name or "main"
        module_tree = {
            fallback_name: {
                "path": "",
                "components": leaf_nodes,
                "children": {}
            }
        }
        logger.warning(f"[STAGE 2 FALLBACK] No directory structure found, created single module '{fallback_name}'")
    
    return module_tree


def format_potential_core_components(leaf_nodes: List[str], components: Dict[str, Node]) -> tuple[str, str]:
    """
    Format the potential core components into a string that can be used in the prompt.
    """
    # Filter out any invalid leaf nodes that don't exist in components
    valid_leaf_nodes = []
    for leaf_node in leaf_nodes:
        if leaf_node in components:
            valid_leaf_nodes.append(leaf_node)
        else:
            logger.warning(f"Skipping invalid leaf node '{leaf_node}' - not found in components")
    
    #group leaf nodes by file
    leaf_nodes_by_file = defaultdict(list)
    for leaf_node in valid_leaf_nodes:
        leaf_nodes_by_file[components[leaf_node].relative_path].append(leaf_node)

    potential_core_components = ""
    potential_core_components_with_code = ""
    for file, leaf_nodes in dict(sorted(leaf_nodes_by_file.items())).items():
        potential_core_components += f"# {file}\n"
        potential_core_components_with_code += f"# {file}\n"
        for leaf_node in leaf_nodes:
            potential_core_components += f"\t{leaf_node}\n"
            potential_core_components_with_code += f"\t{leaf_node}\n"
            potential_core_components_with_code += f"{components[leaf_node].source_code}\n"

    return potential_core_components, potential_core_components_with_code


def cluster_modules(
    leaf_nodes: List[str],
    components: Dict[str, Node],
    config: Config,
    current_module_tree: dict[str, Any] = {},
    current_module_name: str = None,
    current_module_path: List[str] = []
) -> Dict[str, Any]:
    """
    Cluster the potential core components into modules.
    """
    import time
    cluster_start = time.time()
    depth = len(current_module_path)
    module_path_str = ".".join(current_module_path) if current_module_path else "root"
    
    logger.info(f"[STAGE 2: MODULE CLUSTERING] Starting clustering (depth={depth}, path={module_path_str})")
    logger.info(f"[STAGE 2] Input: {len(leaf_nodes)} leaf nodes, {len(components)} components")
    if current_module_name:
        logger.info(f"[STAGE 2] Current module: {current_module_name}")
    
    potential_core_components, potential_core_components_with_code = format_potential_core_components(leaf_nodes, components)
    
    # Use centralized token counting that matches the actual LLM prompt format (full file contents)
    # This ensures consistent threshold checking with what actually gets sent to the LLM
    token_count = count_module_tokens(leaf_nodes, components)
    logger.info(f"[STAGE 2] Module token count (full files): {token_count}, MAX_TOKEN_PER_MODULE: {MAX_TOKEN_PER_MODULE}")

    # FIX: Don't try to cluster too few components (prevents infinite nesting bug)
    # Even if files are large, 2 components can't be meaningfully clustered further
    if len(leaf_nodes) < MIN_COMPONENTS_FOR_CLUSTERING:
        logger.info(f"[STAGE 2] Too few components to cluster ({len(leaf_nodes)} < {MIN_COMPONENTS_FOR_CLUSTERING})")
        cluster_duration = time.time() - cluster_start
        
        if current_module_name is not None:
            logger.info(f"[STAGE 2] Recursive call - returning empty children (too few components)")
            logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (leaf module)")
            return {}
        
        # Root level with very few components
        repo_name = "main"
        single_module = {
            repo_name: {
                "path": "",
                "components": leaf_nodes,
                "children": {}
            }
        }
        logger.info(f"[STAGE 2] Root level - created single module '{repo_name}' with {len(leaf_nodes)} components")
        logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (too few to cluster)")
        return single_module

    if token_count <= MAX_TOKEN_PER_MODULE:
        # Module fits in single module - no further clustering needed
        logger.info(f"[STAGE 2] Module fits in single module ({token_count} <= {MAX_TOKEN_PER_MODULE})")
        logger.info(f"[STAGE 2]   - Token count: {token_count}")
        logger.info(f"[STAGE 2]   - Threshold: {MAX_TOKEN_PER_MODULE}")
        logger.info(f"[STAGE 2]   - Leaf nodes: {len(leaf_nodes)}")
        logger.info(f"[STAGE 2]   - Module: {current_module_name or 'root'}")
        
        cluster_duration = time.time() - cluster_start
        
        # If this is a recursive call (not root level), return empty dict
        # The parent module already exists in the tree with its components
        # We don't need to create a nested child - just signal no further clustering needed
        if current_module_name is not None:
            logger.info(f"[STAGE 2] Recursive call - returning empty children (no further clustering)")
            logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (leaf module, no children)")
            return {}
        
        # Root level: create single module structure
        repo_name = "main"
        single_module = {
            repo_name: {
                "path": "",
                "components": leaf_nodes,
                "children": {}
            }
        }
        logger.info(f"[STAGE 2] Root level - created single module '{repo_name}' with {len(leaf_nodes)} components")
        logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (single module, no LLM needed)")
        return single_module

    # Use only component names (not full code) for clustering to avoid context length issues
    # The LLM only needs names to group them, not full source code
    logger.info(f"[STAGE 2] Formatting cluster prompt...")
    prompt = format_cluster_prompt(potential_core_components, current_module_tree, current_module_name)
    
    # Check prompt size and chunk if needed
    prompt_tokens = count_tokens(prompt)
    
    logger.info(f"[STAGE 2] Prompt size: {prompt_tokens} tokens, {len(leaf_nodes)} leaf nodes, threshold: {MAX_CLUSTERING_PROMPT_TOKENS}")
    
    if prompt_tokens > MAX_CLUSTERING_PROMPT_TOKENS:
        logger.warning(f"[STAGE 2] Prompt too large ({prompt_tokens} tokens), truncating component list to fit context window")
        original_line_count = len(potential_core_components.split('\n'))
        # Truncate potential_core_components to fit
        lines = potential_core_components.split('\n')
        truncated = []
        current_tokens = count_tokens('\n'.join(truncated))
        for line in lines:
            line_tokens = count_tokens(line)
            if current_tokens + line_tokens > MAX_CLUSTERING_PROMPT_TOKENS - 5000:  # Safety margin
                break
            truncated.append(line)
            current_tokens += line_tokens
        potential_core_components = '\n'.join(truncated)
        prompt = format_cluster_prompt(potential_core_components, current_module_tree, current_module_name)
        new_token_count = count_tokens(prompt)
        logger.info(f"[STAGE 2] Truncated from {original_line_count} to {len(truncated)} lines, {new_token_count} tokens")
    
    prompt_tokens = count_tokens(prompt)
    logger.info(f"[STAGE 2] Calling LLM for clustering")
    logger.info(f"[STAGE 2]   - Model: {config.cluster_model}")
    logger.info(f"[STAGE 2]   - Prompt tokens: {prompt_tokens}")
    logger.info(f"[STAGE 2]   - Leaf nodes: {len(leaf_nodes)}")
    logger.info(f"[STAGE 2]   - Components: {len(components)}")
    logger.info(f"[STAGE 2]   - Module: {current_module_name or 'root'}")
    
    llm_start = time.time()
    try:
        response = call_llm(prompt, config, model=config.cluster_model)
        llm_duration = time.time() - llm_start
        response_tokens = count_tokens(response)
        logger.info(f"[STAGE 2] LLM call completed in {llm_duration:.1f}s")
        logger.info(f"[STAGE 2] Response length: {len(response)} chars")
        logger.info(f"[STAGE 2] Response tokens: {response_tokens}")
        
        # CRITICAL: Detect if response was truncated (hit max_tokens limit)
        # GPT-4o max_tokens is 16384, if we're within 100 tokens of that, likely truncated
        MAX_OUTPUT_TOKENS = 16384
        if response_tokens >= MAX_OUTPUT_TOKENS - 100:
            logger.warning(f"[STAGE 2] RESPONSE LIKELY TRUNCATED! Response tokens ({response_tokens}) near max ({MAX_OUTPUT_TOKENS})")
            logger.warning(f"[STAGE 2] Truncation detected - checking if <GROUPED_COMPONENTS> tags are present")
            if "<GROUPED_COMPONENTS>" not in response or "</GROUPED_COMPONENTS>" not in response:
                logger.error(f"[STAGE 2] CONFIRMED TRUNCATION - missing required tags")
                logger.error(f"[STAGE 2] This repo has too many components ({len(leaf_nodes)}) for a single clustering call")
                logger.error(f"[STAGE 2] FALLING BACK TO DIRECTORY-BASED CLUSTERING")
                module_tree = _create_directory_based_modules(leaf_nodes, components, current_module_name)
                logger.info(f"[STAGE 2] Directory-based fallback created {len(module_tree)} modules")
                
                # Continue with tree merge logic after fallback
                if current_module_tree == {}:
                    current_module_tree = module_tree
                else:
                    value = current_module_tree
                    for key in current_module_path:
                        value = value[key]["children"]
                    for module_name, module_info in module_tree.items():
                        del module_info["path"]
                        value[module_name] = module_info
                
                cluster_duration = time.time() - cluster_start
                logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (directory-based fallback)")
                return module_tree
                
    except Exception as e:
        llm_duration = time.time() - llm_start
        error_msg = str(e)
        error_type = type(e).__name__
        
        logger.error(f"[STAGE 2] LLM call FAILED after {llm_duration:.1f}s")
        logger.error(f"[STAGE 2] Error type: {error_type}")
        logger.error(f"[STAGE 2] Error message: {error_msg}")
        logger.error(f"[STAGE 2] Clustering context:")
        logger.error(f"[STAGE 2]   - Leaf nodes: {len(leaf_nodes)}")
        logger.error(f"[STAGE 2]   - Components: {len(components)}")
        logger.error(f"[STAGE 2]   - Module: {current_module_name or 'root'}")
        logger.error(f"[STAGE 2]   - Prompt tokens: {prompt_tokens}")
        logger.error(f"[STAGE 2]   - Model: {config.cluster_model}")
        
        # Check for rate limiting
        if "429" in error_msg or "rate limit" in error_msg.lower() or "rate_limit" in error_msg.lower() or "RateLimitError" in error_type:
            logger.error(f"[STAGE 2] RATE LIMIT DETECTED!")
            logger.error(f"[STAGE 2]   - Model: {config.cluster_model}")
            logger.error(f"[STAGE 2]   - Prompt tokens: {prompt_tokens}")
            logger.error(f"[STAGE 2]   - Duration before failure: {llm_duration:.1f}s")
            logger.error(f"[STAGE 2]   - Leaf nodes: {len(leaf_nodes)}")
            logger.error(f"[STAGE 2]   - Module: {current_module_name or 'root'}")
            
            # Try to get retry-after header if available
            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                retry_after = e.response.headers.get('Retry-After', 'unknown')
                logger.error(f"[STAGE 2]   - Retry-After header: {retry_after}")
        
        # Check for timeout
        if "timeout" in error_msg.lower() or "TimeoutError" in error_type:
            logger.error(f"[STAGE 2] TIMEOUT DETECTED!")
            logger.error(f"[STAGE 2]   - Duration: {llm_duration:.1f}s")
            logger.error(f"[STAGE 2]   - Prompt tokens: {prompt_tokens}")
        
        # Check for network errors
        if "network" in error_msg.lower() or "connection" in error_msg.lower() or "ConnectionError" in error_type:
            logger.error(f"[STAGE 2] NETWORK ERROR DETECTED!")
            logger.error(f"[STAGE 2]   - LLM base URL: {config.llm_base_url}")
        
        import traceback
        logger.error(f"[STAGE 2] Full traceback: {traceback.format_exc()}")
        
        # FALLBACK: Instead of re-raising, use directory-based clustering
        logger.warning(f"[STAGE 2] FALLING BACK TO DIRECTORY-BASED CLUSTERING due to LLM failure")
        module_tree = _create_directory_based_modules(leaf_nodes, components, current_module_name)
        logger.info(f"[STAGE 2] Directory-based fallback created {len(module_tree)} modules")
        
        # Merge into current tree
        if current_module_tree == {}:
            current_module_tree = module_tree
        else:
            value = current_module_tree
            for key in current_module_path:
                value = value[key]["children"]
            for mod_name, mod_info in module_tree.items():
                if "path" in mod_info:
                    del mod_info["path"]
                value[mod_name] = mod_info
        
        cluster_duration = time.time() - cluster_start
        logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (LLM-failure fallback)")
        return module_tree

    #parse the response
    logger.info(f"[STAGE 2] Parsing LLM response...")
    try:
        if "<GROUPED_COMPONENTS>" not in response or "</GROUPED_COMPONENTS>" not in response:
            logger.error(f"[STAGE 2] CRITICAL: Invalid LLM response format - missing component tags")
            logger.error(f"[STAGE 2] Response preview (first 500 chars): {response[:500]}...")
            logger.error(f"[STAGE 2] Response length: {len(response)} chars")
            logger.error(f"[STAGE 2] Looking for <GROUPED_COMPONENTS> and </GROUPED_COMPONENTS> tags")
            logger.error(f"[STAGE 2] FALLING BACK TO DIRECTORY-BASED CLUSTERING")
            module_tree = _create_directory_based_modules(leaf_nodes, components, current_module_name)
            
            # Continue with tree merge logic 
            if current_module_tree == {}:
                current_module_tree = module_tree
            else:
                value = current_module_tree
                for key in current_module_path:
                    value = value[key]["children"]
                for mod_name, mod_info in module_tree.items():
                    if "path" in mod_info:
                        del mod_info["path"]
                    value[mod_name] = mod_info
            
            cluster_duration = time.time() - cluster_start
            logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (parse-failed fallback)")
            return module_tree
        
        response_content = response.split("<GROUPED_COMPONENTS>")[1].split("</GROUPED_COMPONENTS>")[0]
        logger.info(f"[STAGE 2] Extracted response content: {len(response_content)} chars")
        logger.debug(f"[STAGE 2] Response content preview: {response_content[:200]}...")
        
        module_tree = eval(response_content)
        logger.info(f"[STAGE 2] Parsed module tree type: {type(module_tree)}, length: {len(module_tree) if isinstance(module_tree, dict) else 'N/A'}")
        
        if not isinstance(module_tree, dict):
            logger.error(f"[STAGE 2] CRITICAL: Invalid module tree format - expected dict, got {type(module_tree)}")
            logger.error(f"[STAGE 2] Value: {str(module_tree)[:200]}...")
            return {}
            
    except SyntaxError as e:
        logger.error(f"[STAGE 2] CRITICAL: Syntax error parsing LLM response: {e}")
        logger.error(f"[STAGE 2] Response content that failed to parse: {response_content[:500] if 'response_content' in locals() else 'N/A'}...")
        logger.error(f"[STAGE 2] Full response length: {len(response)} chars")
        logger.error(f"[STAGE 2] FALLING BACK TO DIRECTORY-BASED CLUSTERING")
        module_tree = _create_directory_based_modules(leaf_nodes, components, current_module_name)
        
        if current_module_tree == {}:
            current_module_tree = module_tree
        else:
            value = current_module_tree
            for key in current_module_path:
                value = value[key]["children"]
            for mod_name, mod_info in module_tree.items():
                if "path" in mod_info:
                    del mod_info["path"]
                value[mod_name] = mod_info
        
        cluster_duration = time.time() - cluster_start
        logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (syntax-error fallback)")
        return module_tree
    except Exception as e:
        logger.error(f"[STAGE 2] CRITICAL: Failed to parse LLM response: {type(e).__name__}: {str(e)}")
        logger.error(f"[STAGE 2] Response preview: {response[:500]}...")
        logger.error(f"[STAGE 2] Full response length: {len(response)} chars")
        import traceback
        logger.error(f"[STAGE 2] Traceback: {traceback.format_exc()}")
        logger.error(f"[STAGE 2] FALLING BACK TO DIRECTORY-BASED CLUSTERING")
        module_tree = _create_directory_based_modules(leaf_nodes, components, current_module_name)
        
        if current_module_tree == {}:
            current_module_tree = module_tree
        else:
            value = current_module_tree
            for key in current_module_path:
                value = value[key]["children"]
            for mod_name, mod_info in module_tree.items():
                if "path" in mod_info:
                    del mod_info["path"]
                value[mod_name] = mod_info
        
        cluster_duration = time.time() - cluster_start
        logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (parse-exception fallback)")
        return module_tree

    # check if the module tree is valid - only reject if truly empty
    # Single module results (len=1) are valid and should be accepted
    if len(module_tree) == 0:
        logger.warning(f"[STAGE 2] CRITICAL: LLM returned empty module tree")
        logger.warning(f"[STAGE 2]   - Module count: 0")
        logger.warning(f"[STAGE 2]   - Input: {len(leaf_nodes)} leaf nodes, {len(components)} components")
        logger.warning(f"[STAGE 2]   - Token count: {token_count}")
        logger.warning(f"[STAGE 2]   - LLM response length: {len(response)} chars")
        if len(response) > 500:
            logger.warning(f"[STAGE 2]   - LLM response preview: {response[:500]}...")
        logger.warning(f"[STAGE 2] FALLING BACK TO DIRECTORY-BASED CLUSTERING")
        
        # Use directory-based fallback instead of single giant module
        module_tree = _create_directory_based_modules(leaf_nodes, components, current_module_name)
        logger.info(f"[STAGE 2] Directory-based fallback created {len(module_tree)} modules")
    elif len(module_tree) == 1:
        # Single module is valid - log it but don't reject
        logger.info(f"[STAGE 2] LLM returned single module: {list(module_tree.keys())}")
        logger.info(f"[STAGE 2] Single module is valid - proceeding with it")

    if current_module_tree == {}:
        current_module_tree = module_tree
    else:
        value = current_module_tree
        for key in current_module_path:
            value = value[key]["children"]
        for module_name, module_info in module_tree.items():
            del module_info["path"]
            value[module_name] = module_info

    logger.info(f"[STAGE 2] Module tree validated: {len(module_tree)} modules created")
    logger.info(f"[STAGE 2] Module names: {list(module_tree.keys())}")
    
    # Recursively cluster sub-modules
    for module_name, module_info in module_tree.items():
        sub_leaf_nodes = module_info.get("components", [])
        logger.info(f"[STAGE 2] Processing sub-modules for '{module_name}' with {len(sub_leaf_nodes)} components")
        
        # Filter sub_leaf_nodes to ensure they exist in components
        valid_sub_leaf_nodes = []
        invalid_count = 0
        for node in sub_leaf_nodes:
            if node in components:
                valid_sub_leaf_nodes.append(node)
            else:
                logger.warning(f"[STAGE 2] Skipping invalid sub leaf node '{node}' in module '{module_name}' - not found in components")
                invalid_count += 1
        
        if invalid_count > 0:
            logger.warning(f"[STAGE 2] Module '{module_name}': {invalid_count} invalid sub leaf nodes filtered out, {len(valid_sub_leaf_nodes)} valid")
        
        current_module_path.append(module_name)
        try:
            module_info["children"] = {}
            module_info["children"] = cluster_modules(valid_sub_leaf_nodes, components, config, current_module_tree, module_name, current_module_path)
            logger.info(f"[STAGE 2] Sub-modules for '{module_name}': {len(module_info['children'])} children created")
        except Exception as e:
            logger.error(f"[STAGE 2] Failed to cluster sub-modules for '{module_name}': {type(e).__name__}: {str(e)}")
            module_info["children"] = {}
        finally:
            current_module_path.pop()

    cluster_duration = time.time() - cluster_start
    logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE in {cluster_duration:.1f}s (depth={depth}, path={module_path_str})")
    logger.info(f"[STAGE 2] Result: {len(module_tree)} modules at this level")
    return module_tree