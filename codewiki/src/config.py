from dataclasses import dataclass
import argparse
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Constants
OUTPUT_BASE_DIR = 'output'
DEPENDENCY_GRAPHS_DIR = 'dependency_graphs'
DOCS_DIR = 'docs'
FIRST_MODULE_TREE_FILENAME = 'first_module_tree.json'
MODULE_TREE_FILENAME = 'module_tree.json'
OVERVIEW_FILENAME = 'overview.md'

# =============================================================================
# CONSOLIDATED THRESHOLDS - All size/token limits in one place
# =============================================================================

# Clustering Thresholds (Stage 2)
MAX_DEPTH = 10                          # Maximum recursion depth for clustering
MAX_TOKEN_PER_MODULE = 32_768           # Paper: 32768 tokens per leaf module
MAX_TOKEN_PER_LEAF_MODULE = 16_000      # Threshold for sub-module delegation in Stage 4
MIN_COMPONENTS_FOR_CLUSTERING = 3       # Don't try to cluster fewer than this many components
                                        # Fixes infinite nesting bug when 2 components have large files

# LLM Context Thresholds
MAX_CLUSTERING_PROMPT_TOKENS = 100_000  # Max tokens for clustering prompt before chunking
MAX_LLM_CONTEXT = 128_000               # GPT-4o context window (use 200K for Claude/Kimi)
MAX_LLM_OUTPUT_TOKENS = 16_384          # GPT-4o max output tokens

# Module Tree Tiering Thresholds (for large repos)
LARGE_REPO_COMPONENT_THRESHOLD = 500    # Switch to tiered module tree above this
BEHEMOTH_REPO_COMPONENT_THRESHOLD = 2000 # Use on-demand loading above this
MAX_MODULE_TREE_TOKENS = 10_000         # Max tokens for module tree in prompt
                                        # If exceeded, switch to summaries + tools

# CLI context detection
_CLI_CONTEXT = False

def set_cli_context(enabled: bool = True):
    """Set whether we're running in CLI context (vs web app)."""
    global _CLI_CONTEXT
    _CLI_CONTEXT = enabled

def is_cli_context() -> bool:
    """Check if running in CLI context."""
    return _CLI_CONTEXT

# LLM services
# In CLI mode, these will be loaded from ~/.codewiki/config.json + keyring
# In web app mode, use environment variables
MAIN_MODEL = os.getenv('MAIN_MODEL', 'gemini-2.5-flash')
FALLBACK_MODEL_1 = os.getenv('FALLBACK_MODEL_1', 'glm-4p5')
CLUSTER_MODEL = os.getenv('CLUSTER_MODEL', MAIN_MODEL)
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'http://0.0.0.0:4000/')
LLM_API_KEY = os.getenv('LLM_API_KEY', 'sk-1234')

@dataclass
class Config:
    """Configuration class for CodeWiki."""
    repo_path: str
    output_dir: str
    dependency_graph_dir: str
    docs_dir: str
    max_depth: int
    # LLM configuration
    llm_base_url: str
    llm_api_key: str
    main_model: str
    cluster_model: str
    fallback_model: str = FALLBACK_MODEL_1
    
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> 'Config':
        """Create configuration from parsed arguments."""
        repo_name = os.path.basename(os.path.normpath(args.repo_path))
        sanitized_repo_name = ''.join(c if c.isalnum() else '_' for c in repo_name)
        
        return cls(
            repo_path=args.repo_path,
            output_dir=OUTPUT_BASE_DIR,
            dependency_graph_dir=os.path.join(OUTPUT_BASE_DIR, DEPENDENCY_GRAPHS_DIR),
            docs_dir=os.path.join(OUTPUT_BASE_DIR, DOCS_DIR, f"{sanitized_repo_name}-docs"),
            max_depth=MAX_DEPTH,
            llm_base_url=LLM_BASE_URL,
            llm_api_key=LLM_API_KEY,
            main_model=MAIN_MODEL,
            cluster_model=CLUSTER_MODEL,
            fallback_model=FALLBACK_MODEL_1
        )
    
    @classmethod
    def from_cli(
        cls,
        repo_path: str,
        output_dir: str,
        llm_base_url: str,
        llm_api_key: str,
        main_model: str,
        cluster_model: str,
        fallback_model: str = FALLBACK_MODEL_1
    ) -> 'Config':
        """
        Create configuration for CLI context.
        
        Args:
            repo_path: Repository path
            output_dir: Output directory for generated docs
            llm_base_url: LLM API base URL
            llm_api_key: LLM API key
            main_model: Primary model
            cluster_model: Clustering model
            fallback_model: Fallback model
            
        Returns:
            Config instance
        """
        repo_name = os.path.basename(os.path.normpath(repo_path))
        base_output_dir = os.path.join(output_dir, "temp")
        
        return cls(
            repo_path=repo_path,
            output_dir=base_output_dir,
            dependency_graph_dir=os.path.join(base_output_dir, DEPENDENCY_GRAPHS_DIR),
            docs_dir=output_dir,
            max_depth=MAX_DEPTH,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            main_model=main_model,
            cluster_model=cluster_model,
            fallback_model=fallback_model
        )