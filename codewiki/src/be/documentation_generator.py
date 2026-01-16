import logging
import os
import json
import time
from typing import Dict, List, Any
from copy import deepcopy
import traceback

# Configure logging and monitoring
logger = logging.getLogger(__name__)

# Local imports
from codewiki.src.be.dependency_analyzer import DependencyGraphBuilder
from codewiki.src.be.llm_services import call_llm, get_token_tracker
from codewiki.src.be.prompt_template import (
    REPO_OVERVIEW_PROMPT,
    MODULE_OVERVIEW_PROMPT,
)
from codewiki.src.be.cluster_modules import cluster_modules
from codewiki.src.config import (
    Config,
    FIRST_MODULE_TREE_FILENAME,
    MODULE_TREE_FILENAME,
    OVERVIEW_FILENAME
)
from codewiki.src.file_manager import file_manager
from codewiki.src.be.agent_orchestrator import AgentOrchestrator


class DocumentationGenerator:
    """Main documentation generation orchestrator."""
    
    def __init__(self, config: Config, commit_id: str = None):
        self.config = config
        self.commit_id = commit_id
        self.graph_builder = DependencyGraphBuilder(config)
        self.agent_orchestrator = AgentOrchestrator(config)
    
    def create_documentation_metadata(self, working_dir: str, components: Dict[str, Any], num_leaf_nodes: int):
        """Create a metadata file with documentation generation information."""
        from datetime import datetime
        
        metadata = {
            "generation_info": {
                "timestamp": datetime.now().isoformat(),
                "main_model": self.config.main_model,
                "generator_version": "1.0.0",
                "repo_path": self.config.repo_path,
                "commit_id": self.commit_id
            },
            "statistics": {
                "total_components": len(components),
                "leaf_nodes": num_leaf_nodes,
                "max_depth": self.config.max_depth
            },
            "files_generated": [
                "overview.md",
                "module_tree.json",
                "first_module_tree.json"
            ]
        }
        
        # Add generated markdown files to the metadata
        try:
            for file_path in os.listdir(working_dir):
                if file_path.endswith('.md') and file_path not in metadata["files_generated"]:
                    metadata["files_generated"].append(file_path)
        except Exception as e:
            logger.warning(f"Could not list generated files: {e}")
        
        metadata_path = os.path.join(working_dir, "metadata.json")
        file_manager.save_json(metadata, metadata_path)

    
    def get_processing_order(self, module_tree: Dict[str, Any], parent_path: List[str] = []) -> List[tuple[List[str], str]]:
        """Get the processing order using topological sort (leaf modules first)."""
        processing_order = []
        
        def collect_modules(tree: Dict[str, Any], path: List[str]):
            for module_name, module_info in tree.items():
                current_path = path + [module_name]
                
                # If this module has children, process them first
                if module_info.get("children") and isinstance(module_info["children"], dict) and module_info["children"]:
                    collect_modules(module_info["children"], current_path)
                    # Add this parent module after its children
                    processing_order.append((current_path, module_name))
                else:
                    # This is a leaf module, add it immediately
                    processing_order.append((current_path, module_name))
        
        collect_modules(module_tree, parent_path)
        return processing_order

    def is_leaf_module(self, module_info: Dict[str, Any]) -> bool:
        """Check if a module is a leaf module (has no children or empty children)."""
        children = module_info.get("children", {})
        return not children or (isinstance(children, dict) and len(children) == 0)
    
    def _generate_quick_overview(self, module_tree: Dict[str, Any], components: Dict[str, Any]) -> str:
        """Generate a quick overview based on module tree structure only (low latency)."""
        repo_name = os.path.basename(os.path.normpath(self.config.repo_path))
        
        # Build module structure diagram
        def build_mermaid_diagram(tree: Dict[str, Any], indent: int = 0) -> str:
            lines = []
            for module_name, module_info in tree.items():
                component_count = len(module_info.get("components", []))
                lines.append(f"{'  ' * indent}{repo_name} --> {module_name}")
                if module_info.get("children"):
                    lines.extend(build_mermaid_diagram(module_info["children"], indent + 1).split("\n"))
            return "\n".join(filter(None, lines))
        
        mermaid_diagram = f"graph TD;\n{build_mermaid_diagram(module_tree)}"
        
        # Generate quick overview
        overview = f"""# {repo_name} - Repository Overview

## Introduction
This repository contains {len(module_tree)} main modules with a total of {len(components)} components.

## Architecture Overview

```mermaid
{mermaid_diagram}
```

## Modules

"""
        for module_name, module_info in module_tree.items():
            component_count = len(module_info.get("components", []))
            path = module_info.get("path", "")
            overview += f"### {module_name}\n"
            overview += f"- **Path**: `{path}`\n"
            overview += f"- **Components**: {component_count}\n"
            if module_info.get("children"):
                overview += f"- **Sub-modules**: {len(module_info['children'])}\n"
            overview += "\n"
        
        overview += """
## Note
This is a quick overview generated from the module structure. Detailed documentation for each module is being generated and will be available shortly.

"""
        return overview

    def build_overview_structure(self, module_tree: Dict[str, Any], module_path: List[str],
                                 working_dir: str) -> Dict[str, Any]:
        """Build structure for overview generation with 1-depth children docs and target indicator."""
        
        processed_module_tree = deepcopy(module_tree)
        module_info = processed_module_tree
        for path_part in module_path:
            module_info = module_info[path_part]
            if path_part != module_path[-1]:
                module_info = module_info.get("children", {})
            else:
                module_info["is_target_for_overview_generation"] = True

        if "children" in module_info:
            module_info = module_info["children"]

        for child_name, child_info in module_info.items():
            if os.path.exists(os.path.join(working_dir, f"{child_name}.md")):
                child_info["docs"] = file_manager.load_text(os.path.join(working_dir, f"{child_name}.md"))
            else:
                child_path = os.path.join(working_dir, f"{child_name}.md")
                logger.warning(f"Module docs not found at {child_path}")
                child_info["docs"] = ""

        return processed_module_tree

    async def generate_module_documentation(self, components: Dict[str, Any], leaf_nodes: List[str]) -> str:
        """Generate documentation for all modules using dynamic programming approach."""
        import time
        stage_start = time.time()
        logger.info(f"[STAGE 3: DOCUMENTATION GENERATION] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[STAGE 3] Input: {len(components)} components, {len(leaf_nodes)} leaf nodes")
        
        # Prepare output directory
        working_dir = os.path.abspath(self.config.docs_dir)
        logger.info(f"[STAGE 3] Working directory: {working_dir}")
        try:
            file_manager.ensure_directory(working_dir)
            logger.info(f"[STAGE 3] Created/verified working directory")
        except Exception as e:
            logger.error(f"[STAGE 3] Failed to create working directory: {e}")
            raise

        module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
        first_module_tree_path = os.path.join(working_dir, FIRST_MODULE_TREE_FILENAME)
        logger.info(f"[STAGE 3] Loading module trees...")
        logger.info(f"[STAGE 3]   - Module tree path: {module_tree_path}")
        logger.info(f"[STAGE 3]   - First module tree path: {first_module_tree_path}")
        
        try:
            module_tree = file_manager.load_json(module_tree_path)
            logger.info(f"[STAGE 3] Loaded module_tree.json: {len(module_tree)} modules")
        except Exception as e:
            logger.error(f"[STAGE 3] Failed to load module_tree.json: {e}")
            raise
        
        try:
            first_module_tree = file_manager.load_json(first_module_tree_path)
            logger.info(f"[STAGE 3] Loaded first_module_tree.json: {len(first_module_tree)} modules")
        except Exception as e:
            logger.error(f"[STAGE 3] Failed to load first_module_tree.json: {e}")
            raise
        
        # Get processing order (leaf modules first)
        logger.info(f"[STAGE 3] Determining processing order...")
        processing_order = self.get_processing_order(first_module_tree)
        logger.info(f"[STAGE 3] Processing order: {len(processing_order)} modules to process")
        logger.info(f"[STAGE 3] Processing order preview: {[name for _, name in processing_order[:5]]}{'...' if len(processing_order) > 5 else ''}")

        
        # Process modules in dependency order
        final_module_tree = module_tree
        processed_modules = set()
        failed_modules = []
        successful_modules = []

        if len(module_tree) > 0:
            logger.info(f"[STAGE 3] Starting module processing for {len(processing_order)} modules...")
            for idx, (module_path, module_name) in enumerate(processing_order, 1):
                module_key = "/".join(module_path)
                logger.info(f"[STAGE 3] [{idx}/{len(processing_order)}] Processing module: {module_key}")
                module_start = time.time()
                
                try:
                    # Get the module info from the tree
                    module_info = module_tree
                    for path_part in module_path:
                        if path_part not in module_info:
                            logger.error(f"[STAGE 3] Module path part '{path_part}' not found in module tree")
                            raise KeyError(f"Module path part '{path_part}' not found")
                        module_info = module_info[path_part]
                        if path_part != module_path[-1]:  # Not the last part
                            module_info = module_info.get("children", {})
                    
                    # Skip if already processed
                    if module_key in processed_modules:
                        logger.info(f"[STAGE 3] Module {module_key} already processed, skipping")
                        continue
                    
                    # Process the module
                    if self.is_leaf_module(module_info):
                        logger.info(f"[STAGE 3] 📄 Processing leaf module: {module_key}")
                        logger.info(f"[STAGE 3]   - Components: {len(module_info.get('components', []))}")
                        final_module_tree = await self.agent_orchestrator.process_module(
                            module_name, components, module_info["components"], module_path, working_dir
                        )
                    else:
                        logger.info(f"[STAGE 3] 📁 Processing parent module: {module_key}")
                        logger.info(f"[STAGE 3]   - Children: {len(module_info.get('children', {}))}")
                        final_module_tree = await self.generate_parent_module_docs(
                            module_path, working_dir
                        )
                    
                    processed_modules.add(module_key)
                    successful_modules.append(module_key)
                    module_duration = time.time() - module_start
                    logger.info(f"[STAGE 3] ✓ Module {module_key} processed successfully in {module_duration:.1f}s")
                    
                except Exception as e:
                    module_duration = time.time() - module_start
                    logger.error(f"[STAGE 3] ✗ Failed to process module {module_key} after {module_duration:.1f}s: {type(e).__name__}: {str(e)}")
                    failed_modules.append((module_key, str(e)))
                    import traceback
                    logger.error(f"[STAGE 3] Traceback: {traceback.format_exc()}")
                    continue
            
            logger.info(f"[STAGE 3] Module processing complete:")
            logger.info(f"[STAGE 3]   - Successful: {len(successful_modules)}")
            logger.info(f"[STAGE 3]   - Failed: {len(failed_modules)}")
            if failed_modules:
                logger.warning(f"[STAGE 3] Failed modules: {[name for name, _ in failed_modules]}")

            # Generate repo overview
            logger.info(f"📚 Generating repository overview")
            final_module_tree = await self.generate_parent_module_docs(
                [], working_dir
            )
        else:
            # No modules in tree - this should be rare after the clustering fixes
            # Create a fallback single-module structure to ensure downstream processing works
            logger.warning(f"[STAGE 3] No modules in tree - creating fallback single-module structure")
            
            repo_name = os.path.basename(os.path.normpath(self.config.repo_path))
            logger.info(f"[STAGE 3] Creating fallback module structure for {repo_name}")
            
            # Create minimal module tree with all leaf nodes as a single module
            fallback_module_tree = {
                repo_name: {
                    "path": "",
                    "components": leaf_nodes,
                    "children": {}
                }
            }
            
            # Save the fallback module tree so other parts of the system can use it
            file_manager.save_json(fallback_module_tree, os.path.join(working_dir, MODULE_TREE_FILENAME))
            logger.info(f"[STAGE 3] Saved fallback module tree with 1 module containing {len(leaf_nodes)} components")
            
            # Process the single module
            logger.info(f"[STAGE 3] Processing fallback single module: {repo_name}")
            try:
                final_module_tree = await self.agent_orchestrator.process_module(
                    repo_name, components, leaf_nodes, [], working_dir
                )
                logger.info(f"[STAGE 3] Fallback module processing complete")
            except Exception as e:
                logger.error(f"[STAGE 3] Failed to process fallback module: {type(e).__name__}: {str(e)}")
                # Even if processing fails, we have a valid module tree structure
                final_module_tree = fallback_module_tree
                logger.warning(f"[STAGE 3] Using fallback module tree without full documentation")

            # rename repo_name.md to overview.md if it exists
            repo_overview_path = os.path.join(working_dir, f"{repo_name}.md")
            if os.path.exists(repo_overview_path):
                os.rename(repo_overview_path, os.path.join(working_dir, OVERVIEW_FILENAME))
                logger.info(f"[STAGE 3] Renamed {repo_name}.md to overview.md")
        
        return working_dir

    async def generate_parent_module_docs(self, module_path: List[str], 
                                        working_dir: str) -> Dict[str, Any]:
        """Generate documentation for a parent module based on its children's documentation."""
        module_name = module_path[-1] if len(module_path) >= 1 else os.path.basename(os.path.normpath(self.config.repo_path))

        logger.info(f"Generating parent documentation for: {module_name}")
        
        # Load module tree
        module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
        module_tree = file_manager.load_json(module_tree_path)

        # check if overview docs already exists
        overview_docs_path = os.path.join(working_dir, OVERVIEW_FILENAME)
        if os.path.exists(overview_docs_path):
            logger.info(f"✓ Overview docs already exists at {overview_docs_path}")
            return module_tree

        # check if parent docs already exists
        parent_docs_path = os.path.join(working_dir, f"{module_name if len(module_path) >= 1 else OVERVIEW_FILENAME.replace('.md', '')}.md")
        if os.path.exists(parent_docs_path):
            logger.info(f"✓ Parent docs already exists at {parent_docs_path}")
            return module_tree

        # Create repo structure with 1-depth children docs and target indicator
        repo_structure = self.build_overview_structure(module_tree, module_path, working_dir)

        # Build list of available modules from the module tree
        # This prevents the LLM from creating links to non-existent modules
        def collect_module_keys(tree, prefix=""):
            keys = []
            for key, data in tree.items():
                full_key = f"{prefix}/{key}" if prefix else key
                keys.append(key)  # Just the key name (maps to key.md)
                if data.get("children"):
                    keys.extend(collect_module_keys(data["children"], full_key))
            return keys
        
        available_modules = collect_module_keys(module_tree)
        available_modules_str = ", ".join([f'"{m}.md"' for m in available_modules]) if available_modules else "(no sub-modules)"
        logger.info(f"[STAGE 3] Available modules for linking: {available_modules_str}")

        prompt = MODULE_OVERVIEW_PROMPT.format(
            module_name=module_name,
            repo_structure=json.dumps(repo_structure, indent=4)
        ) if len(module_path) >= 1 else REPO_OVERVIEW_PROMPT.format(
            repo_name=module_name,
            repo_structure=json.dumps(repo_structure, indent=4),
            available_modules=available_modules_str
        )
        
        try:
            logger.info(f"[STAGE 3] Generating parent documentation for '{module_name}'...")
            logger.info(f"[STAGE 3] Prompt size: {len(prompt)} chars")
            parent_docs_start = time.time()
            parent_docs = call_llm(prompt, self.config)
            parent_docs_duration = time.time() - parent_docs_start
            logger.info(f"[STAGE 3] LLM call completed in {parent_docs_duration:.1f}s, response length: {len(parent_docs)} chars")
            
            # Parse and save parent documentation
            # Handle cases where LLM doesn't include the <OVERVIEW> tags
            if "<OVERVIEW>" in parent_docs and "</OVERVIEW>" in parent_docs:
                parent_content = parent_docs.split("<OVERVIEW>")[1].split("</OVERVIEW>")[0].strip()
                logger.debug(f"[STAGE 3] Extracted content from <OVERVIEW> tags: {len(parent_content)} chars")
            else:
                logger.warning(f"[STAGE 3] LLM response missing <OVERVIEW> tags, using full response")
                # If no tags, use the entire response (LLM might have generated markdown directly)
                parent_content = parent_docs.strip()
                # Remove any XML-like tags if present but not properly formatted
                if parent_content.startswith("<OVERVIEW>"):
                    parent_content = parent_content.replace("<OVERVIEW>", "").replace("</OVERVIEW>", "").strip()
            
            # Remove markdown code block wrapper if present (e.g., ```markdown ... ```)
            if parent_content.startswith("```"):
                logger.debug(f"[STAGE 3] Removing markdown code block wrapper")
                # Find the closing ```
                lines = parent_content.split("\n")
                if len(lines) > 1 and lines[0].startswith("```"):
                    # Remove first line (```markdown or ```)
                    lines = lines[1:]
                    # Remove last line if it's just ```
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    parent_content = "\n".join(lines).strip()
            
            try:
                file_manager.save_text(parent_content, parent_docs_path)
                logger.info(f"[STAGE 3] Successfully saved parent documentation to {parent_docs_path}")
                logger.info(f"[STAGE 3] File size: {len(parent_content)} chars")
            except Exception as e:
                logger.error(f"[STAGE 3] Failed to save parent documentation: {e}")
                raise
            
            logger.info(f"[STAGE 3] Successfully generated parent documentation for: {module_name}")
            return module_tree
            
        except Exception as e:
            logger.error(f"[STAGE 3] Error generating parent documentation for {module_name}: {type(e).__name__}: {str(e)}")
            logger.error(f"[STAGE 3] Module path: {module_path}, Module name: {module_name}")
            import traceback
            logger.error(f"[STAGE 3] Traceback: {traceback.format_exc()}")
            raise
    
    async def run(self) -> None:
        """Run the complete documentation generation process using dynamic programming."""
        try:
            # Build dependency graph
            components, leaf_nodes = self.graph_builder.build_dependency_graph()

            logger.debug(f"Found {len(leaf_nodes)} leaf nodes")
            # logger.debug(f"Leaf nodes:\n{'\n'.join(sorted(leaf_nodes)[:200])}")
            # exit()
            
            # Cluster modules
            working_dir = os.path.abspath(self.config.docs_dir)
            file_manager.ensure_directory(working_dir)
            first_module_tree_path = os.path.join(working_dir, FIRST_MODULE_TREE_FILENAME)
            module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
            
            # Check if module tree exists
            # Set token tracker stage for cost tracking
            tracker = get_token_tracker()
            tracker.set_stage("Stage 2: Module Clustering")
            
            logger.info(f"[STAGE 2: MODULE CLUSTERING] Checking for cached module tree...")
            if os.path.exists(first_module_tree_path):
                logger.info(f"[STAGE 2] Module tree found at {first_module_tree_path}")
                try:
                    module_tree = file_manager.load_json(first_module_tree_path)
                    logger.info(f"[STAGE 2] Loaded cached module tree: {len(module_tree)} modules")
                except Exception as e:
                    logger.error(f"[STAGE 2] Failed to load cached module tree: {e}")
                    logger.info(f"[STAGE 2] Will regenerate...")
                    module_tree = None
            else:
                logger.info(f"[STAGE 2] Module tree not found at {first_module_tree_path}, clustering modules")
                module_tree = None
            
            if module_tree is None:
                logger.info(f"[STAGE 2] Starting module clustering...")
                try:
                    module_tree = cluster_modules(leaf_nodes, components, self.config)
                    logger.info(f"[STAGE 2] Clustering complete: {len(module_tree)} modules created")
                    
                    if len(module_tree) == 0:
                        logger.error(f"[STAGE 2] CRITICAL: Clustering returned 0 modules!")
                        logger.error(f"[STAGE 2] Input: {len(leaf_nodes)} leaf nodes, {len(components)} components")
                        logger.error(f"[STAGE 2] This will cause module viewer to fail")
                        logger.error(f"[STAGE 2] Module tree content: {module_tree}")
                        raise RuntimeError(f"Module clustering failed - 0 modules created from {len(leaf_nodes)} leaf nodes")
                    
                    try:
                        file_manager.save_json(module_tree, first_module_tree_path)
                        logger.info(f"[STAGE 2] Saved module tree to {first_module_tree_path}")
                    except Exception as e:
                        logger.error(f"[STAGE 2] Failed to save module tree: {e}")
                        raise
                except Exception as e:
                    logger.error(f"[STAGE 2] Clustering FAILED: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(f"[STAGE 2] Traceback: {traceback.format_exc()}")
                    raise
            
            try:
                file_manager.save_json(module_tree, module_tree_path)
                logger.info(f"[STAGE 2] Saved module tree to {module_tree_path}")
            except Exception as e:
                logger.error(f"[STAGE 2] Failed to save module tree to {module_tree_path}: {e}")
                raise
            
            logger.info(f"[STAGE 2: MODULE CLUSTERING] COMPLETE - Grouped components into {len(module_tree)} modules")
            if len(module_tree) > 0:
                logger.info(f"[STAGE 2] Module names: {list(module_tree.keys())[:10]}{'...' if len(module_tree) > 10 else ''}")
            
            # LOW-LATENCY: Generate initial overview immediately after clustering
            # This provides fast feedback while modules are still being processed
            working_dir = os.path.abspath(self.config.docs_dir)
            overview_path = os.path.join(working_dir, OVERVIEW_FILENAME)
            
            if not os.path.exists(overview_path) and len(module_tree) > 0:
                try:
                    logger.info("🚀 Generating low-latency overview (top-level structure only)...")
                    # Generate a quick overview based on module tree structure only
                    quick_overview = self._generate_quick_overview(module_tree, components)
                    file_manager.save_text(quick_overview, overview_path)
                    logger.info(f"✓ Quick overview generated at {overview_path}")
                    
                    # Track first overview for metrics
                    try:
                        from codewiki.src.utils.metrics import get_metrics_collector
                        metrics = get_metrics_collector().get_current()
                        if metrics:
                            metrics.record_first_overview(overview_path)
                    except:
                        pass
                except Exception as e:
                    logger.warning(f"Failed to generate quick overview: {e}")
            
            # Set stage for cost tracking
            tracker.set_stage("Stage 4: Module Documentation")
            
            # Generate module documentation using dynamic programming approach
            # This processes leaf modules first, then parent modules
            working_dir = await self.generate_module_documentation(components, leaf_nodes)
            
            # Create documentation metadata
            self.create_documentation_metadata(working_dir, components, len(leaf_nodes))
            
            logger.debug(f"Documentation generation completed successfully using dynamic programming!")
            logger.debug(f"Processing order: leaf modules → parent modules → repository overview")
            logger.debug(f"Documentation saved to: {working_dir}")
            
            # Print final token usage summary
            tracker.set_stage("Complete")
            logger.info("\n" + tracker.get_summary())
            
        except Exception as e:
            logger.error(f"Documentation generation failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise