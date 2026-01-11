from typing import Dict, List, Any
import os
from codewiki.src.config import Config
from codewiki.src.be.dependency_analyzer.ast_parser import DependencyParser
from codewiki.src.be.dependency_analyzer.topo_sort import build_graph_from_components, get_leaf_nodes
from codewiki.src.file_manager import file_manager

import logging
logger = logging.getLogger(__name__)


class DependencyGraphBuilder:
    """Handles dependency analysis and graph building."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def build_dependency_graph(self) -> tuple[Dict[str, Any], List[str]]:
        """
        Build and save dependency graph, returning components and leaf nodes.
        
        Returns:
            Tuple of (components, leaf_nodes)
        """
        import time
        stage_start = time.time()
        logger.info(f"[STAGE 1: DEPENDENCY ANALYSIS] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[STAGE 1] Repo path: {self.config.repo_path}")
        
        # Ensure output directory exists
        try:
            file_manager.ensure_directory(self.config.dependency_graph_dir)
            logger.info(f"[STAGE 1] Created/verified output directory: {self.config.dependency_graph_dir}")
        except Exception as e:
            logger.error(f"[STAGE 1] Failed to create output directory: {e}")
            raise

        # Prepare dependency graph path
        repo_name = os.path.basename(os.path.normpath(self.config.repo_path))
        sanitized_repo_name = ''.join(c if c.isalnum() else '_' for c in repo_name)
        logger.info(f"[STAGE 1] Repo name: {repo_name}, sanitized: {sanitized_repo_name}")
        
        dependency_graph_path = os.path.join(
            self.config.dependency_graph_dir, 
            f"{sanitized_repo_name}_dependency_graph.json"
        )
        filtered_folders_path = os.path.join(
            self.config.dependency_graph_dir, 
            f"{sanitized_repo_name}_filtered_folders.json"
        )
        logger.info(f"[STAGE 1] Dependency graph path: {dependency_graph_path}")

        parser = DependencyParser(self.config.repo_path)

        filtered_folders = None
        # if os.path.exists(filtered_folders_path):
        #     logger.debug(f"Loading filtered folders from {filtered_folders_path}")
        #     filtered_folders = file_manager.load_json(filtered_folders_path)
        # else:
        #     # Parse repository
        #     filtered_folders = parser.filter_folders()
        #     # Save filtered folders
        #     file_manager.save_json(filtered_folders, filtered_folders_path)

        # Parse repository
        logger.info(f"[STAGE 1] Starting repository parsing...")
        parse_start = time.time()
        try:
            components = parser.parse_repository(filtered_folders)
            parse_duration = time.time() - parse_start
            logger.info(f"[STAGE 1] Repository parsing completed in {parse_duration:.1f}s")
            logger.info(f"[STAGE 1] Found {len(components)} components")
            
            if len(components) == 0:
                logger.error(f"[STAGE 1] CRITICAL: No components found in repository!")
                logger.error(f"[STAGE 1] This usually means:")
                logger.error(f"[STAGE 1]   1. Repository has no code files")
                logger.error(f"[STAGE 1]   2. Repository is too small")
                logger.error(f"[STAGE 1]   3. All files were filtered out")
                logger.error(f"[STAGE 1]   4. AST parsing failed for all files")
                logger.error(f"[STAGE 1] Repo path: {self.config.repo_path}")
                raise RuntimeError(f"Repository analysis found 0 components - cannot proceed")
        except Exception as e:
            parse_duration = time.time() - parse_start
            logger.error(f"[STAGE 1] Repository parsing FAILED after {parse_duration:.1f}s: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[STAGE 1] Traceback: {traceback.format_exc()}")
            raise
        
        # Save dependency graph
        try:
            logger.info(f"[STAGE 1] Saving dependency graph to {dependency_graph_path}...")
            parser.save_dependency_graph(dependency_graph_path)
            logger.info(f"[STAGE 1] Dependency graph saved successfully")
        except Exception as e:
            logger.error(f"[STAGE 1] Failed to save dependency graph: {e}")
            raise
        
        # Build graph for traversal
        logger.info(f"[STAGE 1] Building graph from components...")
        try:
            graph = build_graph_from_components(components)
            logger.info(f"[STAGE 1] Graph built successfully, nodes: {len(graph)}")
        except Exception as e:
            logger.error(f"[STAGE 1] Failed to build graph: {e}")
            raise
        
        # Get leaf nodes
        logger.info(f"[STAGE 1] Extracting leaf nodes...")
        try:
            leaf_nodes = get_leaf_nodes(graph, components)
            logger.info(f"[STAGE 1] Found {len(leaf_nodes)} leaf nodes (before filtering)")
        except Exception as e:
            logger.error(f"[STAGE 1] Failed to get leaf nodes: {e}")
            raise

        # check if leaf_nodes are in components, only keep the ones that are in components
        # and type is one of the following: class, interface, struct (or function for C-based projects)
        
        # Determine if we should include functions based on available component types
        available_types = set()
        for comp in components.values():
            available_types.add(comp.component_type)
        logger.info(f"[STAGE 1] Available component types: {sorted(available_types)}")
        
        # Valid types for leaf nodes - include functions for C-based codebases
        valid_types = {"class", "interface", "struct"}
        # If no classes/interfaces/structs are found, include functions
        if not available_types.intersection(valid_types):
            valid_types.add("function")
            logger.info(f"[STAGE 1] No classes/interfaces/structs found, including functions in valid types")
        logger.info(f"[STAGE 1] Valid types for leaf nodes: {sorted(valid_types)}")
        
        keep_leaf_nodes = []
        skipped_invalid = 0
        skipped_type = 0
        skipped_missing = 0
        for leaf_node in leaf_nodes:
            # Skip any leaf nodes that are clearly error strings or invalid identifiers
            if not isinstance(leaf_node, str) or leaf_node.strip() == "" or any(err_keyword in leaf_node.lower() for err_keyword in ['error', 'exception', 'failed', 'invalid']):
                logger.warning(f"[STAGE 1] Skipping invalid leaf node identifier: '{leaf_node}'")
                skipped_invalid += 1
                continue
                
            if leaf_node in components:
                if components[leaf_node].component_type in valid_types:
                    keep_leaf_nodes.append(leaf_node)
                else:
                    skipped_type += 1
                    # logger.debug(f"Leaf node {leaf_node} is a {components[leaf_node].component_type}, removing it")
                    pass
            else:
                logger.warning(f"[STAGE 1] Leaf node {leaf_node} not found in components, removing it")
                skipped_missing += 1
        
        logger.info(f"[STAGE 1] Leaf node filtering complete:")
        logger.info(f"[STAGE 1]   - Kept: {len(keep_leaf_nodes)}")
        logger.info(f"[STAGE 1]   - Skipped (invalid): {skipped_invalid}")
        logger.info(f"[STAGE 1]   - Skipped (wrong type): {skipped_type}")
        logger.info(f"[STAGE 1]   - Skipped (missing): {skipped_missing}")
        
        if len(keep_leaf_nodes) == 0:
            logger.error(f"[STAGE 1] CRITICAL: No valid leaf nodes after filtering!")
            logger.error(f"[STAGE 1] Total leaf nodes before filtering: {len(leaf_nodes)}")
            logger.error(f"[STAGE 1] This will cause module clustering to fail")
        
        stage_duration = time.time() - stage_start
        logger.info(f"[STAGE 1: DEPENDENCY ANALYSIS] COMPLETE in {stage_duration:.1f}s")
        logger.info(f"[STAGE 1] Final result: {len(components)} components, {len(keep_leaf_nodes)} leaf nodes")
        
        return components, keep_leaf_nodes