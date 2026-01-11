from pydantic_ai import Agent
# import logfire
import logging
import os
import time
from typing import Dict, List, Any

# Configure logging and monitoring

logger = logging.getLogger(__name__)

# try:
#     # Configure logfire with environment variables for Docker compatibility
#     logfire_token = os.getenv('LOGFIRE_TOKEN')
#     logfire_project = os.getenv('LOGFIRE_PROJECT_NAME', 'default')
#     logfire_service = os.getenv('LOGFIRE_SERVICE_NAME', 'default')
    
#     if logfire_token:
#         # Configure with explicit token (for Docker)
#         logfire.configure(
#             token=logfire_token,
#             project_name=logfire_project,
#             service_name=logfire_service,
#         )
#     else:
#         # Use default configuration (for local development with logfire auth)
#         logfire.configure(
#             project_name=logfire_project,
#             service_name=logfire_service,
#         )
    
#     logfire.instrument_pydantic_ai()
#     logger.debug(f"Logfire configured successfully for project: {logfire_project}")
    
# except Exception as e:
#     logger.warning(f"Failed to configure logfire: {e}")

# Local imports
from codewiki.src.be.agent_tools.deps import CodeWikiDeps
from codewiki.src.be.agent_tools.read_code_components import read_code_components_tool
from codewiki.src.be.agent_tools.str_replace_editor import str_replace_editor_tool
from codewiki.src.be.agent_tools.generate_sub_module_documentations import generate_sub_module_documentation_tool
from codewiki.src.be.llm_services import create_fallback_models
from codewiki.src.be.prompt_template import (
    SYSTEM_PROMPT,
    LEAF_SYSTEM_PROMPT,
    format_user_prompt,
)
from codewiki.src.be.utils import is_complex_module
from codewiki.src.config import (
    Config,
    MODULE_TREE_FILENAME,
    OVERVIEW_FILENAME,
)
from codewiki.src.file_manager import file_manager
from codewiki.src.be.dependency_analyzer.models.core import Node


class AgentOrchestrator:
    """Orchestrates the AI agents for documentation generation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.fallback_models = create_fallback_models(config)
    
    def create_agent(self, module_name: str, components: Dict[str, Any], 
                    core_component_ids: List[str]) -> Agent:
        """Create an appropriate agent based on module complexity."""
        logger.debug(f"[STAGE 4.3] Creating agent for module: {module_name}")
        logger.debug(f"[STAGE 4.3] Core component IDs: {len(core_component_ids)}")
        logger.debug(f"[STAGE 4.3] Total components: {len(components)}")
        
        is_complex = is_complex_module(components, core_component_ids)
        
        if is_complex:
            logger.debug(f"[STAGE 4.3] Module is complex - creating complex agent with sub-module tool")
            agent = Agent(
                self.fallback_models,
                name=module_name,
                deps_type=CodeWikiDeps,
                tools=[
                    read_code_components_tool, 
                    str_replace_editor_tool, 
                    generate_sub_module_documentation_tool
                ],
                system_prompt=SYSTEM_PROMPT.format(module_name=module_name),
            )
            logger.debug(f"[STAGE 4.3] Complex agent created with 3 tools")
        else:
            logger.debug(f"[STAGE 4.3] Module is leaf - creating leaf agent without sub-module tool")
            agent = Agent(
                self.fallback_models,
                name=module_name,
                deps_type=CodeWikiDeps,
                tools=[read_code_components_tool, str_replace_editor_tool],
                system_prompt=LEAF_SYSTEM_PROMPT.format(module_name=module_name),
            )
            logger.debug(f"[STAGE 4.3] Leaf agent created with 2 tools")
        
        return agent
    
    async def process_module(self, module_name: str, components: Dict[str, Node], 
                           core_component_ids: List[str], module_path: List[str], working_dir: str) -> Dict[str, Any]:
        """Process a single module and generate its documentation."""
        module_start = time.time()
        logger.info(f"[STAGE 4: AGENT MODULE PROCESSING] Starting module: {module_name}")
        logger.info(f"[STAGE 4] Module path: {'.'.join(module_path) if module_path else 'root'}")
        logger.info(f"[STAGE 4] Core component IDs: {len(core_component_ids)}")
        logger.info(f"[STAGE 4] Total components: {len(components)}")
        logger.info(f"[STAGE 4] Working directory: {working_dir}")
        
        # STAGE 4.1: Load module tree
        module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
        logger.info(f"[STAGE 4.1: MODULE TREE LOAD] Loading module tree from {module_tree_path}")
        load_start = time.time()
        
        try:
            if not os.path.exists(module_tree_path):
                logger.warning(f"[STAGE 4.1] Module tree file does not exist: {module_tree_path}")
                logger.warning(f"[STAGE 4.1] Will create new module tree")
                module_tree = {}
            else:
                file_size = os.path.getsize(module_tree_path)
                logger.info(f"[STAGE 4.1] Module tree file exists: {file_size} bytes")
                module_tree = file_manager.load_json(module_tree_path)
                load_duration = time.time() - load_start
                
                if module_tree is None:
                    logger.warning(f"[STAGE 4.1] Module tree file loaded but returned None - using empty dict")
                    module_tree = {}
                else:
                    logger.info(f"[STAGE 4.1] Module tree loaded in {load_duration:.3f}s")
                    logger.info(f"[STAGE 4.1] Module tree type: {type(module_tree)}")
                    if isinstance(module_tree, dict):
                        logger.info(f"[STAGE 4.1] Module count: {len(module_tree)}")
                        logger.info(f"[STAGE 4.1] Module keys: {list(module_tree.keys())[:10]}")
                    else:
                        logger.warning(f"[STAGE 4.1] Module tree is not a dict: {type(module_tree)}")
                        module_tree = {}
        except Exception as e:
            load_duration = time.time() - load_start
            logger.error(f"[STAGE 4.1] Module tree load FAILED after {load_duration:.3f}s: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[STAGE 4.1] Traceback: {traceback.format_exc()}")
            logger.warning(f"[STAGE 4.1] Using empty module tree as fallback")
            module_tree = {}
        
        # STAGE 4.2: Check if docs already exist
        overview_docs_path = os.path.join(working_dir, OVERVIEW_FILENAME)
        docs_path = os.path.join(working_dir, f"{module_name}.md")
        
        logger.info(f"[STAGE 4.2: DOCS CHECK] Checking for existing documentation...")
        logger.info(f"[STAGE 4.2] Overview docs path: {overview_docs_path} (exists: {os.path.exists(overview_docs_path)})")
        logger.info(f"[STAGE 4.2] Module docs path: {docs_path} (exists: {os.path.exists(docs_path)})")
        
        if os.path.exists(overview_docs_path):
            file_size = os.path.getsize(overview_docs_path)
            logger.info(f"[STAGE 4.2] Overview docs already exists at {overview_docs_path} ({file_size} bytes)")
            logger.info(f"[STAGE 4.2] Skipping module processing")
            return module_tree

        if os.path.exists(docs_path):
            file_size = os.path.getsize(docs_path)
            logger.info(f"[STAGE 4.2] Module docs already exists at {docs_path} ({file_size} bytes)")
            logger.info(f"[STAGE 4.2] Skipping module processing")
            return module_tree
        
        # STAGE 4.3: Create agent
        logger.info(f"[STAGE 4.3: AGENT CREATION] Creating agent for module: {module_name}")
        agent_start = time.time()
        
        try:
            from codewiki.src.be.utils import is_complex_module
            is_complex = is_complex_module(components, core_component_ids)
            logger.info(f"[STAGE 4.3] Module complexity: {'complex' if is_complex else 'leaf'}")
            logger.info(f"[STAGE 4.3] Config summary:")
            logger.info(f"[STAGE 4.3]   - Main model: {self.config.main_model}")
            logger.info(f"[STAGE 4.3]   - Cluster model: {self.config.cluster_model}")
            logger.info(f"[STAGE 4.3]   - Fallback model: {self.config.fallback_model}")
            logger.info(f"[STAGE 4.3]   - LLM base URL: {self.config.llm_base_url}")
            logger.info(f"[STAGE 4.3]   - Max depth: {self.config.max_depth}")
            logger.info(f"[STAGE 4.3]   - Current depth: 1")
            
            agent = self.create_agent(module_name, components, core_component_ids)
            agent_duration = time.time() - agent_start
            
            agent_type = "complex" if is_complex else "leaf"
            tools_count = len(agent.tools) if hasattr(agent, 'tools') else 'unknown'
            logger.info(f"[STAGE 4.3] Agent created in {agent_duration:.3f}s")
            logger.info(f"[STAGE 4.3] Agent type: {agent_type}")
            logger.info(f"[STAGE 4.3] Tools count: {tools_count}")
        except Exception as e:
            agent_duration = time.time() - agent_start
            logger.error(f"[STAGE 4.3] Agent creation FAILED after {agent_duration:.3f}s: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[STAGE 4.3] Traceback: {traceback.format_exc()}")
            raise
        
        # STAGE 4.4: Create dependencies
        logger.info(f"[STAGE 4.4: DEPENDENCIES] Creating dependencies...")
        try:
            deps = CodeWikiDeps(
                absolute_docs_path=working_dir,
                absolute_repo_path=str(os.path.abspath(self.config.repo_path)),
                registry={},
                components=components,
                path_to_current_module=module_path,
                current_module_name=module_name,
                module_tree=module_tree,
                max_depth=self.config.max_depth,
                current_depth=1,
                config=self.config
            )
            logger.info(f"[STAGE 4.4] Dependencies created successfully")
            logger.info(f"[STAGE 4.4]   - Docs path: {deps.absolute_docs_path}")
            logger.info(f"[STAGE 4.4]   - Repo path: {deps.absolute_repo_path}")
            logger.info(f"[STAGE 4.4]   - Component count: {len(deps.components)}")
            logger.info(f"[STAGE 4.4]   - Module tree size: {len(deps.module_tree) if isinstance(deps.module_tree, dict) else 'N/A'}")
        except Exception as e:
            logger.error(f"[STAGE 4.4] Dependencies creation FAILED: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[STAGE 4.4] Traceback: {traceback.format_exc()}")
            raise
        
        # STAGE 4.5: Format user prompt
        logger.info(f"[STAGE 4.5: PROMPT FORMATTING] Formatting user prompt...")
        prompt_start = time.time()
        
        try:
            from codewiki.src.be.utils import count_module_tokens
            user_prompt = format_user_prompt(
                module_name=module_name,
                core_component_ids=core_component_ids,
                components=components,
                module_tree=deps.module_tree
            )
            prompt_tokens = count_module_tokens(core_component_ids, components)
            prompt_duration = time.time() - prompt_start
            
            logger.info(f"[STAGE 4.5] Prompt formatted in {prompt_duration:.3f}s")
            logger.info(f"[STAGE 4.5] Prompt size: {len(user_prompt)} chars")
            logger.info(f"[STAGE 4.5] Prompt tokens: {prompt_tokens}")
            logger.info(f"[STAGE 4.5] Core component IDs: {len(core_component_ids)}")
        except Exception as e:
            prompt_duration = time.time() - prompt_start
            logger.error(f"[STAGE 4.5] Prompt formatting FAILED after {prompt_duration:.3f}s: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[STAGE 4.5] Traceback: {traceback.format_exc()}")
            raise
        
        # STAGE 4.6: Run agent
        logger.info(f"[STAGE 4.6: AGENT EXECUTION] Running agent for module: {module_name}")
        logger.info(f"[STAGE 4.6] Model: {self.config.main_model}")
        logger.info(f"[STAGE 4.6] Prompt tokens: {prompt_tokens}")
        execution_start = time.time()
        
        try:
            result = await agent.run(
                user_prompt,
                deps=deps
            )
            execution_duration = time.time() - execution_start
            
            logger.info(f"[STAGE 4.6] Agent execution completed in {execution_duration:.1f}s")
            logger.info(f"[STAGE 4.6] Result type: {type(result)}")
            
            # Save updated module tree
            save_start = time.time()
            file_manager.save_json(deps.module_tree, module_tree_path)
            save_duration = time.time() - save_start
            
            module_duration = time.time() - module_start
            logger.info(f"[STAGE 4.6] Module tree saved in {save_duration:.3f}s")
            logger.info(f"[STAGE 4: AGENT MODULE PROCESSING] COMPLETE in {module_duration:.1f}s for module: {module_name}")
            
            return deps.module_tree
            
        except Exception as e:
            execution_duration = time.time() - execution_start
            module_duration = time.time() - module_start
            import sys
            import traceback
            
            logger.error(f"[STAGE 4.6] Agent execution FAILED after {execution_duration:.1f}s")
            logger.error(f"[STAGE 4.6] Module: {module_name}")
            logger.error(f"[STAGE 4.6] Component count: {len(core_component_ids)}")
            logger.error(f"[STAGE 4.6] Prompt tokens: {prompt_tokens}")
            logger.error(f"[STAGE 4.6] Error type: {type(e).__name__}")
            logger.error(f"[STAGE 4.6] Error message: {str(e)}")
            
            # Check for rate limiting
            error_str = str(e).lower()
            if "429" in str(e) or "rate limit" in error_str or "rate_limit" in error_str:
                logger.error(f"[STAGE 4.6] RATE LIMIT DETECTED")
                logger.error(f"[STAGE 4.6]   - Module: {module_name}")
                logger.error(f"[STAGE 4.6]   - Prompt tokens: {prompt_tokens}")
                logger.error(f"[STAGE 4.6]   - Model: {self.config.main_model}")
                logger.error(f"[STAGE 4.6]   - Duration before failure: {execution_duration:.1f}s")
            
            # Print detailed error info to stderr for debugging
            print(f"\n=== DETAILED ERROR INFO ===", file=sys.stderr)
            print(f"Exception type: {type(e)}", file=sys.stderr)
            print(f"Exception: {e}", file=sys.stderr)
            print(f"Exception args: {e.args}", file=sys.stderr)
            print(f"Exception attributes: {[x for x in dir(e) if not x.startswith('_')]}", file=sys.stderr)
            
            # Try to get sub-exceptions
            if hasattr(e, 'exceptions'):
                print(f"Found 'exceptions' attribute with {len(e.exceptions)} items", file=sys.stderr)
                for i, sub_exc in enumerate(e.exceptions):
                    print(f"\nSub-exception {i+1}:", file=sys.stderr)
                    print(f"  Type: {type(sub_exc)}", file=sys.stderr)
                    print(f"  Message: {sub_exc}", file=sys.stderr)
                    if hasattr(sub_exc, '__traceback__') and sub_exc.__traceback__:
                        print(f"  Traceback:", file=sys.stderr)
                        print(''.join(traceback.format_exception(type(sub_exc), sub_exc, sub_exc.__traceback__)), file=sys.stderr)
            
            full_tb = traceback.format_exc()
            logger.error(f"[STAGE 4.6] Full traceback:\n{full_tb}")
            logger.error(f"[STAGE 4: AGENT MODULE PROCESSING] FAILED in {module_duration:.1f}s for module: {module_name}")
            print(f"=== END ERROR INFO ===\n", file=sys.stderr)
            raise