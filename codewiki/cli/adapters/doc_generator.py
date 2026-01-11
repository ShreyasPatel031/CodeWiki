"""
CLI adapter for documentation generator backend.

This adapter wraps the existing backend documentation_generator.py
and provides CLI-specific functionality like progress reporting.
"""

from pathlib import Path
from typing import Dict, Any
import time
import asyncio
import os
import logging
import sys
import json
import click

from codewiki.cli.utils.progress import ProgressTracker
from codewiki.cli.models.job import DocumentationJob, LLMConfig
from codewiki.cli.utils.errors import APIError

# Import backend modules
from codewiki.src.be.documentation_generator import DocumentationGenerator
from codewiki.src.config import Config as BackendConfig, set_cli_context


class CLIDocumentationGenerator:
    """
    CLI adapter for documentation generation with progress reporting.
    
    This class wraps the backend documentation generator and adds
    CLI-specific features like progress tracking and error handling.
    """
    
    def __init__(
        self,
        repo_path: Path,
        output_dir: Path,
        config: Dict[str, Any],
        verbose: bool = False,
        generate_html: bool = False
    ):
        """
        Initialize the CLI documentation generator.
        
        Args:
            repo_path: Repository path
            output_dir: Output directory
            config: LLM configuration
            verbose: Enable verbose output
            generate_html: Whether to generate HTML viewer
        """
        self.repo_path = repo_path
        self.output_dir = output_dir
        self.config = config
        self.verbose = verbose
        self.generate_html = generate_html
        self.progress_tracker = ProgressTracker(total_stages=5, verbose=verbose)
        self.job = DocumentationJob()
        
        # Setup job metadata
        self.job.repository_path = str(repo_path)
        self.job.repository_name = repo_path.name
        self.job.output_directory = str(output_dir)
        self.job.llm_config = LLMConfig(
            main_model=config.get('main_model', ''),
            cluster_model=config.get('cluster_model', ''),
            base_url=config.get('base_url', '')
        )
        
        # Configure backend logging
        self._configure_backend_logging()
    
    def _configure_backend_logging(self):
        """Configure backend logger for CLI use with colored output."""
        from codewiki.src.be.dependency_analyzer.utils.logging_config import ColoredFormatter
        
        # Get backend logger (parent of all backend modules)
        backend_logger = logging.getLogger('codewiki.src.be')
        
        # Get CLI logger (for html_generator and other CLI modules)
        cli_logger = logging.getLogger('codewiki.cli')
        
        # Remove existing handlers to avoid duplicates
        backend_logger.handlers.clear()
        cli_logger.handlers.clear()
        
        if self.verbose:
            # In verbose mode, show INFO and above
            backend_logger.setLevel(logging.INFO)
            cli_logger.setLevel(logging.INFO)
            
            # Create console handler with formatting
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Use colored formatter for better readability
            colored_formatter = ColoredFormatter()
            console_handler.setFormatter(colored_formatter)
            
            # Add handler to both loggers
            backend_logger.addHandler(console_handler)
            cli_logger.addHandler(console_handler)
        else:
            # In non-verbose mode, suppress backend logs (use WARNING level to hide INFO/DEBUG)
            backend_logger.setLevel(logging.WARNING)
            cli_logger.setLevel(logging.WARNING)
            
            # Create console handler for warnings and errors only
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.WARNING)
            
            # Use colored formatter even for warnings/errors
            colored_formatter = ColoredFormatter()
            console_handler.setFormatter(colored_formatter)
            
            backend_logger.addHandler(console_handler)
            cli_logger.addHandler(console_handler)
        
        # Prevent propagation to root logger to avoid duplicate messages
        backend_logger.propagate = False
        cli_logger.propagate = False
    
    def generate(self) -> DocumentationJob:
        """
        Generate documentation with progress tracking.
        
        Returns:
            Completed DocumentationJob
            
        Raises:
            APIError: If LLM API call fails
        """
        self.job.start()
        start_time = time.time()
        
        try:
            # Set CLI context for backend
            set_cli_context(True)
            
            # Create backend config with CLI settings
            # Use main_model as fallback_model for OpenAI compatibility
            main_model = self.config.get('main_model')
            backend_config = BackendConfig.from_cli(
                repo_path=str(self.repo_path),
                output_dir=str(self.output_dir),
                llm_base_url=self.config.get('base_url'),
                llm_api_key=self.config.get('api_key'),
                main_model=main_model,
                cluster_model=self.config.get('cluster_model'),
                fallback_model=main_model  # Use same model for fallback
            )
            
            # Run backend documentation generation
            asyncio.run(self._run_backend_generation(backend_config))
            
            # Stage 4: HTML Generation (optional)
            # #region agent log
            import json
            import os
            debug_log_path = '/Users/shreyaspatel/CodeWiki/.cursor/debug.log'
            click.echo(f"[DEBUG] [HYP-D] Checking HTML generation flag: generate_html={self.generate_html}, output_dir={self.output_dir}", err=True)
            try:
                os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"doc_generator.py:158","message":"Checking if HTML generation should run","data":{"generate_html":self.generate_html,"output_dir":str(self.output_dir)},"timestamp":int(time.time()*1000)})+"\n")
            except Exception as e:
                click.echo(f"[DEBUG] Failed to write debug log: {e}", err=True)
            # #endregion
            if self.generate_html:
                # #region agent log
                click.echo(f"[DEBUG] [HYP-D] HTML generation flag is True, calling _run_html_generation", err=True)
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"doc_generator.py:163","message":"HTML generation flag is True, calling _run_html_generation","data":{},"timestamp":int(time.time()*1000)})+"\n")
                except Exception as e:
                    click.echo(f"[DEBUG] Failed to log HTML gen call: {e}", err=True)
                # #endregion
                self._run_html_generation()
            else:
                # #region agent log
                click.echo(f"[DEBUG] [HYP-D] HTML generation flag is False, SKIPPING HTML generation", err=True)
                try:
                    with open(debug_log_path, 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"doc_generator.py:171","message":"HTML generation flag is False, skipping","data":{},"timestamp":int(time.time()*1000)})+"\n")
                except Exception:
                    pass
                # #endregion
            
            # Stage 5: Finalization (metadata already created by backend)
            self._finalize_job()
            
            # Complete job
            generation_time = time.time() - start_time
            self.job.complete()
            
            return self.job
            
        except APIError as e:
            self.job.fail(str(e))
            raise
        except Exception as e:
            self.job.fail(str(e))
            raise
    
    async def _run_backend_generation(self, backend_config: BackendConfig):
        """Run the backend documentation generation with progress tracking."""
        import time
        stage_start = time.time()
        
        # Initialize metrics tracking
        from codewiki.src.utils.metrics import get_metrics_collector
        metrics_collector = get_metrics_collector()
        repo_name = os.path.basename(os.path.normpath(self.repo_path))
        metrics = metrics_collector.start_repo(repo_name, str(self.repo_path))
        
        # Calculate repo size and file count
        try:
            import shutil
            total_size = shutil.disk_usage(str(self.repo_path)).used
            metrics.repo_size_mb = total_size / (1024 * 1024)
            # Count code files
            code_files = []
            for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h']:
                code_files.extend(list(Path(self.repo_path).rglob(f"*{ext}")))
            code_files = [f for f in code_files if 'node_modules' not in str(f) and '.git' not in str(f)]
            metrics.total_code_files = len(code_files)
            click.echo(f"[DEBUG] Repo: {repo_name}, {len(code_files)} code files, {metrics.repo_size_mb:.2f} MB", err=True)
        except Exception as e:
            click.echo(f"[DEBUG] Error calculating repo stats: {e}", err=True)
        
        # Stage 1: Dependency Analysis
        click.echo(f"[DEBUG] [{time.time() - stage_start:.1f}s] Starting Stage 1: Dependency Analysis", err=True)
        stage_metrics = metrics.start_stage("Dependency Analysis")
        stage_1_start = time.time()
        self.progress_tracker.start_stage(1, "Dependency Analysis")
        if self.verbose:
            self.progress_tracker.update_stage(0.2, "Initializing dependency analyzer...")
        
        # Create documentation generator
        doc_generator = DocumentationGenerator(backend_config)
        
        if self.verbose:
            self.progress_tracker.update_stage(0.5, "Parsing source files...")
        click.echo(f"[DEBUG] [{time.time() - stage_1_start:.1f}s] Parsing source files...", err=True)
        
        # Build dependency graph with HARD TIMEOUT
        # TODO: Make timeout dynamic based on repo size once we have benchmark data
        # for now using 300s (5 min) to support large repos like tensorflow/pytorch
        import signal
        STAGE_1_TIMEOUT = 300  # 5 minutes - adjust based on benchmark results
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Stage 1 (Dependency Analysis) timed out after {STAGE_1_TIMEOUT} seconds")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(STAGE_1_TIMEOUT)
        try:
            components, leaf_nodes = doc_generator.graph_builder.build_dependency_graph()
            signal.alarm(0)  # Cancel timeout
            stage_1_duration = time.time() - stage_1_start
            self.job.statistics.total_files_analyzed = len(components)
            self.job.statistics.leaf_nodes = len(leaf_nodes)
            
            click.echo(f"[DEBUG] [{stage_1_duration:.1f}s] Stage 1 complete: {len(components)} components, {len(leaf_nodes)} leaf nodes", err=True)
            if self.verbose:
                self.progress_tracker.update_stage(1.0, f"Found {len(leaf_nodes)} leaf nodes")
        except TimeoutError as e:
            signal.alarm(0)
            stage_1_duration = time.time() - stage_1_start
            click.echo(f"[DEBUG] [{stage_1_duration:.1f}s] Stage 1 TIMEOUT: {e}", err=True)
            raise APIError(f"Dependency analysis timed out after {STAGE_1_TIMEOUT}s: {e}")
        except Exception as e:
            signal.alarm(0)
            stage_1_duration = time.time() - stage_1_start
            click.echo(f"[DEBUG] [{stage_1_duration:.1f}s] Stage 1 FAILED: {e}", err=True)
            raise APIError(f"Dependency analysis failed: {e}")
        
        self.progress_tracker.complete_stage()
        metrics.complete_stage("Dependency Analysis")
        
        # Stage 2: Module Clustering
        click.echo(f"[DEBUG] [{time.time() - stage_start:.1f}s] Starting Stage 2: Module Clustering", err=True)
        stage_metrics = metrics.start_stage("Module Clustering")
        stage_2_start = time.time()
        self.progress_tracker.start_stage(2, "Module Clustering")
        if self.verbose:
            self.progress_tracker.update_stage(0.5, "Clustering modules with LLM...")
        click.echo(f"[DEBUG] [{time.time() - stage_2_start:.1f}s] Clustering {len(leaf_nodes)} leaf nodes...", err=True)
        
        # Import clustering function
        from codewiki.src.be.cluster_modules import cluster_modules
        from codewiki.src.file_manager import file_manager
        from codewiki.src.config import FIRST_MODULE_TREE_FILENAME, MODULE_TREE_FILENAME
        
        working_dir = str(self.output_dir.absolute())
        file_manager.ensure_directory(working_dir)
        first_module_tree_path = os.path.join(working_dir, FIRST_MODULE_TREE_FILENAME)
        module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
        
        try:
            if os.path.exists(first_module_tree_path):
                click.echo(f"[DEBUG] [{time.time() - stage_2_start:.1f}s] Using cached module tree", err=True)
                module_tree = file_manager.load_json(first_module_tree_path)
            else:
                click.echo(f"[DEBUG] [{time.time() - stage_2_start:.1f}s] Calling cluster_modules (this may take a while)...", err=True)
                click.echo(f"[DEBUG] Input: {len(leaf_nodes)} leaf nodes, {len(components)} total components", err=True)
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Module clustering timed out after 60 seconds")
                
                # Set 30 second timeout for clustering
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)  # 30 second hard timeout
                try:
                    module_tree = cluster_modules(leaf_nodes, components, backend_config)
                    signal.alarm(0)  # Cancel timeout
                except TimeoutError as e:
                    signal.alarm(0)
                    click.echo(f"[DEBUG] TIMEOUT: {e}", err=True)
                    raise APIError(f"Module clustering timed out after 30s: {e}")
                file_manager.save_json(module_tree, first_module_tree_path)
            
            stage_2_duration = time.time() - stage_2_start
            file_manager.save_json(module_tree, module_tree_path)
            self.job.module_count = len(module_tree)
            
            click.echo(f"[DEBUG] [{stage_2_duration:.1f}s] Stage 2 complete: {len(module_tree)} modules created", err=True)
            if self.verbose:
                self.progress_tracker.update_stage(1.0, f"Created {len(module_tree)} modules")
        except Exception as e:
            stage_2_duration = time.time() - stage_2_start
            click.echo(f"[DEBUG] [{stage_2_duration:.1f}s] Stage 2 FAILED: {e}", err=True)
            import traceback
            click.echo(f"[DEBUG] Traceback: {traceback.format_exc()}", err=True)
            raise APIError(f"Module clustering failed: {e}")
        
        self.progress_tracker.complete_stage()
        metrics.complete_stage("Module Clustering")
        
        # Track first overview generation (low latency)
        overview_path = os.path.join(working_dir, "overview.md")
        if os.path.exists(overview_path):
            metrics.record_first_overview(overview_path)
        
        # DEBUG: Show Stage 2 summary (but continue to Stage 3)
        click.echo(f"\n[DEBUG] ===== STAGE 2 COMPLETE =====", err=True)
        click.echo(f"[DEBUG] Module count: {len(module_tree)}", err=True)
        click.echo(f"[DEBUG] Total duration so far: {time.time() - stage_start:.1f}s", err=True)
        if len(module_tree) > 0:
            click.echo(f"[DEBUG] Module names: {list(module_tree.keys())[:10]}", err=True)
        click.echo(f"[DEBUG] Continuing to Stage 3: Documentation Generation...", err=True)
        
        # Stage 3: Documentation Generation
        click.echo(f"[DEBUG] [{time.time() - stage_start:.1f}s] Starting Stage 3: Documentation Generation", err=True)
        stage_metrics = metrics.start_stage("Documentation Generation")
        stage_3_start = time.time()
        self.progress_tracker.start_stage(3, "Documentation Generation")
        if self.verbose:
            self.progress_tracker.update_stage(0.1, "Generating module documentation...")
        click.echo(f"[DEBUG] [{time.time() - stage_3_start:.1f}s] Generating docs for {len(module_tree)} modules...", err=True)
        
        try:
            # Run the actual documentation generation
            click.echo(f"[DEBUG] [{time.time() - stage_3_start:.1f}s] Calling generate_module_documentation...", err=True)
            await doc_generator.generate_module_documentation(components, leaf_nodes)
            
            stage_3_duration = time.time() - stage_3_start
            click.echo(f"[DEBUG] [{stage_3_duration:.1f}s] Module documentation complete", err=True)
            
            if self.verbose:
                self.progress_tracker.update_stage(0.9, "Creating repository overview...")
            
            # Create metadata
            doc_generator.create_documentation_metadata(working_dir, components, len(leaf_nodes))
            
            # Collect generated files
            md_files = []
            for file_path in os.listdir(working_dir):
                if file_path.endswith('.md') or file_path.endswith('.json'):
                    self.job.files_generated.append(file_path)
                    if file_path.endswith('.md'):
                        stage_metrics.files_created += 1
                        stage_metrics.files_created_list.append(file_path)
                        md_files.append(file_path)
            
            click.echo(f"[DEBUG] [{time.time() - stage_3_start:.1f}s] Generated {len(md_files)} markdown files: {', '.join(md_files[:5])}{'...' if len(md_files) > 5 else ''}", err=True)
            
            # Track first overview if created
            overview_path = os.path.join(working_dir, "overview.md")
            if os.path.exists(overview_path) and metrics.time_to_first_overview is None:
                metrics.record_first_overview(overview_path)
                click.echo(f"[DEBUG] First overview created at {metrics.time_to_first_overview:.1f}s", err=True)
            
        except Exception as e:
            stage_3_duration = time.time() - stage_3_start
            click.echo(f"[DEBUG] [{stage_3_duration:.1f}s] Stage 3 FAILED: {e}", err=True)
            import traceback
            click.echo(f"[DEBUG] Traceback: {traceback.format_exc()}", err=True)
            raise APIError(f"Documentation generation failed: {e}")
        
        total_duration = time.time() - stage_start
        click.echo(f"[DEBUG] [{total_duration:.1f}s] ALL STAGES COMPLETE", err=True)
        self.progress_tracker.complete_stage()
        metrics.complete_stage("Documentation Generation")
        
        # Finalize metrics
        metrics.finalize()
        
        # Save metrics
        metrics_output = Path(working_dir) / "metrics.json"
        metrics.save(metrics_output)
    
    def _run_html_generation(self):
        """Run HTML generation stage."""
        # #region agent log
        import json
        import os
        debug_log_path = '/Users/shreyaspatel/CodeWiki/.cursor/debug.log'
        try:
            os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A,D","location":"doc_generator.py:396","message":"_run_html_generation ENTRY","data":{"output_dir":str(self.output_dir),"repo_path":str(self.repo_path)},"timestamp":int(time.time()*1000)})+"\n")
            click.echo(f"[DEBUG] [HYP-D] _run_html_generation ENTRY: output_dir={self.output_dir}", err=True)
        except Exception as e:
            click.echo(f"[DEBUG] Failed to write debug log at entry: {e}", err=True)
        # #endregion
        logger = logging.getLogger(__name__)
        # #region agent log
        try:
            logger_handlers = len(logger.handlers) if hasattr(logger, 'handlers') else 0
            logger_level = logger.level if hasattr(logger, 'level') else logging.NOTSET
            logger_effective = logger.getEffectiveLevel()
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"doc_generator.py:403","message":"Logger configuration check","data":{"logger_name":__name__,"handlers_count":logger_handlers,"logger_level":logger_level,"effective_level":logger_effective},"timestamp":int(time.time()*1000)})+"\n")
            click.echo(f"[DEBUG] [HYP-A] Logger config: name={__name__}, handlers={logger_handlers}, level={logger_level}, effective={logger_effective}", err=True)
        except Exception as e:
            click.echo(f"[DEBUG] Failed to log logger config: {e}", err=True)
        # #endregion
        stage_start = time.time()
        
        logger.info(f"[STAGE 5: HTML GENERATION] Starting HTML generation")
        logger.info(f"[STAGE 5] Output directory: {self.output_dir}")
        logger.info(f"[STAGE 5] Repository path: {self.repo_path}")
        
        self.progress_tracker.start_stage(4, "HTML Generation")
        
        try:
            from codewiki.cli.html_generator import HTMLGenerator
            
            logger.info(f"[STAGE 5] Creating HTMLGenerator...")
            html_generator_start = time.time()
            html_generator = HTMLGenerator()
            html_generator_duration = time.time() - html_generator_start
            logger.info(f"[STAGE 5] HTMLGenerator created in {html_generator_duration:.3f}s")
            logger.info(f"[STAGE 5] Template directory: {html_generator.template_dir}")
            
            if self.verbose:
                self.progress_tracker.update_stage(0.3, "Loading module tree and metadata...")
            
            logger.info(f"[STAGE 5] Detecting repository info...")
            repo_info_start = time.time()
            try:
                repo_info = html_generator.detect_repository_info(self.repo_path)
                repo_info_duration = time.time() - repo_info_start
                logger.info(f"[STAGE 5] Repository info detected in {repo_info_duration:.3f}s")
                logger.info(f"[STAGE 5]   - Name: {repo_info.get('name', 'N/A')}")
                logger.info(f"[STAGE 5]   - URL: {repo_info.get('url', 'N/A')}")
                logger.info(f"[STAGE 5]   - GitHub Pages URL: {repo_info.get('github_pages_url', 'N/A')}")
            except Exception as e:
                repo_info_duration = time.time() - repo_info_start
                logger.error(f"[STAGE 5] Repository info detection FAILED after {repo_info_duration:.3f}s: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[STAGE 5] Traceback: {traceback.format_exc()}")
                raise
            
            # Generate HTML with auto-loading of module_tree and metadata from docs_dir
            output_path = self.output_dir / "index.html"
            logger.info(f"[STAGE 5] Starting HTML generation...")
            logger.info(f"[STAGE 5]   - Output path: {output_path}")
            logger.info(f"[STAGE 5]   - Title: {repo_info.get('name', 'N/A')}")
            logger.info(f"[STAGE 5]   - Docs directory: {self.output_dir}")
            
            html_gen_start = time.time()
            # #region agent log
            output_path_str = str(output_path.resolve())
            with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"doc_generator.py:429","message":"BEFORE html_generator.generate call","data":{"output_path":output_path_str,"output_path_exists_before":output_path.exists(),"output_path_parent":str(output_path.parent),"parent_exists":output_path.parent.exists()},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            try:
                html_generator.generate(
                    output_path=output_path,
                    title=repo_info['name'],
                    repository_url=repo_info['url'],
                    github_pages_url=repo_info['github_pages_url'],
                    docs_dir=self.output_dir  # Auto-load module_tree and metadata from here
                )
                html_gen_duration = time.time() - html_gen_start
                # #region agent log
                output_exists_after = output_path.exists()
                file_size_after = output_path.stat().st_size if output_exists_after else 0
                with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C,E,F","location":"doc_generator.py:438","message":"AFTER html_generator.generate call","data":{"duration":html_gen_duration,"output_path":output_path_str,"output_path_exists_after":output_exists_after,"file_size":file_size_after},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                logger.info(f"[STAGE 5] HTML generation completed in {html_gen_duration:.1f}s")
                
                # Verify output file was created
                # #region agent log
                with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"doc_generator.py:442","message":"File verification check","data":{"output_path":output_path_str,"path_exists":output_path.exists(),"resolved_path":str(output_path.resolve())},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    logger.info(f"[STAGE 5] index.html created successfully: {file_size} bytes")
                    # #region agent log
                    with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C,E","location":"doc_generator.py:444","message":"File verification SUCCESS","data":{"file_size":file_size,"output_path":output_path_str},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                else:
                    # #region agent log
                    with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C,E","location":"doc_generator.py:446","message":"File verification FAILED - file does not exist","data":{"output_path":output_path_str,"parent_exists":output_path.parent.exists(),"parent_dir":str(output_path.parent)},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    logger.error(f"[STAGE 5] CRITICAL: index.html was not created at {output_path}")
                    raise FileNotFoundError(f"HTML file was not created: {output_path}")
                
            except Exception as e:
                html_gen_duration = time.time() - html_gen_start
                # #region agent log
                import traceback
                exc_traceback = traceback.format_exc()
                with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"doc_generator.py:449","message":"Exception caught in html_generator.generate","data":{"exception_type":type(e).__name__,"exception_msg":str(e),"output_path":output_path_str,"traceback":exc_traceback[:500]},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                logger.error(f"[STAGE 5] HTML generation FAILED after {html_gen_duration:.1f}s: {type(e).__name__}: {str(e)}")
                logger.error(f"[STAGE 5]   - Output path: {output_path}")
                logger.error(f"[STAGE 5]   - Docs directory: {self.output_dir}")
                logger.error(f"[STAGE 5] Traceback: {exc_traceback}")
                raise
            
            self.job.files_generated.append("index.html")
            
            if self.verbose:
                self.progress_tracker.update_stage(1.0, "Generated index.html")
            
            stage_duration = time.time() - stage_start
            # #region agent log
            final_output_path = self.output_dir / "index.html"
            final_check = final_output_path.exists()
            final_size = final_output_path.stat().st_size if final_check else 0
            with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C,E","location":"doc_generator.py:464","message":"_run_html_generation EXIT - SUCCESS","data":{"duration":stage_duration,"final_output_path":str(final_output_path),"final_file_exists":final_check,"final_file_size":final_size},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            logger.info(f"[STAGE 5: HTML GENERATION] COMPLETE in {stage_duration:.1f}s")
            self.progress_tracker.complete_stage()
            
        except Exception as e:
            stage_duration = time.time() - stage_start
            # #region agent log
            import traceback
            exc_traceback = traceback.format_exc()
            with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"doc_generator.py:467","message":"Exception caught in _run_html_generation outer handler","data":{"exception_type":type(e).__name__,"exception_msg":str(e),"duration":stage_duration,"traceback":exc_traceback[:500]},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            logger.error(f"[STAGE 5: HTML GENERATION] FAILED after {stage_duration:.1f}s: {type(e).__name__}: {str(e)}")
            logger.error(f"[STAGE 5] Output directory: {self.output_dir}")
            logger.error(f"[STAGE 5] Repository path: {self.repo_path}")
            logger.error(f"[STAGE 5] Full traceback:\n{exc_traceback}")
            click.echo(f"[ERROR] HTML generation failed: {e}", err=True)
            raise
    
    def _finalize_job(self):
        """Finalize the job (metadata already created by backend)."""
        # Just verify metadata exists
        metadata_path = self.output_dir / "metadata.json"
        if not metadata_path.exists():
            # Create our own if backend didn't
            with open(metadata_path, 'w') as f:
                f.write(self.job.to_json())

