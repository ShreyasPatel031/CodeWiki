#!/usr/bin/env python3
"""
Background worker for processing documentation generation jobs.
"""

import os
import json
import time
import threading
import subprocess
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Dict
from dataclasses import asdict

from codewiki.src.be.documentation_generator import DocumentationGenerator
from codewiki.src.config import Config, MAIN_MODEL
from .models import JobStatus
from .cache_manager import CacheManager
from .github_processor import GitHubRepoProcessor
from .config import WebAppConfig
from codewiki.src.file_manager import file_manager

logger = logging.getLogger(__name__)

class BackgroundWorker:
    """Background worker for processing documentation generation jobs."""
    
    def __init__(self, cache_manager: CacheManager, temp_dir: str = None):
        self.cache_manager = cache_manager
        self.temp_dir = temp_dir or WebAppConfig.TEMP_DIR
        self.running = False
        self.processing_queue = Queue(maxsize=WebAppConfig.QUEUE_SIZE)
        self.job_status: Dict[str, JobStatus] = {}
        self.jobs_file = Path(WebAppConfig.CACHE_DIR) / "jobs.json"
        self.load_job_statuses()
    
    def start(self):
        """Start the background worker thread."""
        if not self.running:
            self.running = True
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
            print("Background worker started")
    
    def stop(self):
        """Stop the background worker."""
        self.running = False
    
    def add_job(self, job_id: str, job: JobStatus):
        """Add a job to the processing queue."""
        self.job_status[job_id] = job
        self.processing_queue.put(job_id)
    
    def get_job_status(self, job_id: str) -> JobStatus:
        """Get job status by ID."""
        return self.job_status.get(job_id)
    
    def get_all_jobs(self) -> Dict[str, JobStatus]:
        """Get all job statuses."""
        return self.job_status
    
    def load_job_statuses(self):
        """Load job statuses from disk."""
        if not self.jobs_file.exists():
            # Try to reconstruct from cache if no job file exists
            self._reconstruct_jobs_from_cache()
            return
        
        try:
            data = file_manager.load_json(self.jobs_file)
                
            for job_id, job_data in data.items():
                # Only load completed jobs to avoid inconsistent state
                if job_data.get('status') == 'completed':
                    self.job_status[job_id] = JobStatus(
                        job_id=job_data['job_id'],
                        repo_url=job_data['repo_url'],
                        status=job_data['status'],
                        created_at=datetime.fromisoformat(job_data['created_at']),
                        started_at=datetime.fromisoformat(job_data['started_at']) if job_data.get('started_at') else None,
                        completed_at=datetime.fromisoformat(job_data['completed_at']) if job_data.get('completed_at') else None,
                        error_message=job_data.get('error_message'),
                        progress=job_data.get('progress', ''),
                        docs_path=job_data.get('docs_path')
                    )
            print(f"Loaded {len([j for j in self.job_status.values() if j.status == 'completed'])} completed jobs from disk")
        except Exception as e:
            print(f"Error loading job statuses: {e}")
    
    def _reconstruct_jobs_from_cache(self):
        """Reconstruct job statuses from cache entries for backward compatibility."""
        try:
            cache_entries = self.cache_manager.cache_index
            reconstructed_count = 0
            
            for repo_hash, cache_entry in cache_entries.items():
                # Extract repo info to create job_id
                from .github_processor import GitHubRepoProcessor
                try:
                    repo_info = GitHubRepoProcessor.get_repo_info(cache_entry.repo_url)
                    job_id = repo_info['full_name'].replace('/', '--')
                    
                    # Only add if job doesn't already exist
                    if job_id not in self.job_status:
                        self.job_status[job_id] = JobStatus(
                            job_id=job_id,
                            repo_url=cache_entry.repo_url,
                            status='completed',
                            created_at=cache_entry.created_at,
                            completed_at=cache_entry.created_at,
                            docs_path=cache_entry.docs_path,
                            progress="Reconstructed from cache"
                        )
                        reconstructed_count += 1
                except Exception as e:
                    print(f"Failed to reconstruct job for {cache_entry.repo_url}: {e}")
            
            if reconstructed_count > 0:
                print(f"Reconstructed {reconstructed_count} job statuses from cache")
                self.save_job_statuses()
                
        except Exception as e:
            print(f"Error reconstructing jobs from cache: {e}")
    
    def save_job_statuses(self):
        """Save job statuses to disk."""
        try:
            # Ensure cache directory exists
            self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for job_id, job in self.job_status.items():
                data[job_id] = {
                    'job_id': job.job_id,
                    'repo_url': job.repo_url,
                    'status': job.status,
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'error_message': job.error_message,
                    'progress': job.progress,
                    'docs_path': job.docs_path
                }
            
            file_manager.save_json(data, self.jobs_file)
        except Exception as e:
            print(f"Error saving job statuses: {e}")
    
    def _worker_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                if not self.processing_queue.empty():
                    job_id = self.processing_queue.get(timeout=1)
                    self._process_job(job_id)
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"Worker error: {e}")
                time.sleep(1)
    
    def _process_job(self, job_id: str):
        """Process a single documentation generation job."""
        if job_id not in self.job_status:
            logger.warning(f"[STAGE 0] Job {job_id} not found in job_status")
            return
        
        job = self.job_status[job_id]
        stage_start = time.time()
        
        logger.info(f"[STAGE 0: REPOSITORY SETUP] Starting job {job_id}")
        logger.info(f"[STAGE 0] Job details: repo_url={job.repo_url}, commit_id={job.commit_id}")
        
        try:
            # Update job status
            job.status = 'processing'
            job.started_at = datetime.now()
            job.progress = "Starting repository clone..."
            job.main_model = MAIN_MODEL
            
            # STAGE 0.1: Check cache first
            logger.info(f"[STAGE 0.1: CACHE CHECK] Checking cache for {job.repo_url}")
            cache_check_start = time.time()
            try:
                cached_docs = self.cache_manager.get_cached_docs(job.repo_url)
                cache_check_duration = time.time() - cache_check_start
                
                if cached_docs:
                    cache_path = Path(cached_docs)
                    logger.info(f"[STAGE 0.1] Cache lookup completed in {cache_check_duration:.1f}s")
                    logger.info(f"[STAGE 0.1] Cache path: {cached_docs}")
                    logger.info(f"[STAGE 0.1] Cache path exists: {cache_path.exists()}")
                    
                    if cache_path.exists():
                        cache_size = sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file()) if cache_path.is_dir() else cache_path.stat().st_size if cache_path.is_file() else 0
                        logger.info(f"[STAGE 0.1] Cache size: {cache_size} bytes")
                        logger.info(f"[STAGE 0.1] Cache hit - using cached documentation")
                        
                        job.status = 'completed'
                        job.completed_at = datetime.now()
                        job.docs_path = cached_docs
                        job.progress = "Documentation retrieved from cache"
                        if not job.main_model:
                            job.main_model = MAIN_MODEL
                        
                        self.save_job_statuses()
                        logger.info(f"[STAGE 0.1] Job {job_id} completed from cache")
                        return
                    else:
                        logger.warning(f"[STAGE 0.1] Cache path exists but file/directory not found: {cached_docs}")
                else:
                    logger.info(f"[STAGE 0.1] Cache lookup completed in {cache_check_duration:.1f}s")
                    logger.info(f"[STAGE 0.1] Cache miss - no cached documentation found")
            except Exception as e:
                cache_check_duration = time.time() - cache_check_start
                logger.error(f"[STAGE 0.1] Cache check FAILED after {cache_check_duration:.1f}s: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[STAGE 0.1] Traceback: {traceback.format_exc()}")
                raise
            
            # STAGE 0.2: Get repo info and parse URL
            logger.info(f"[STAGE 0.2: REPO INFO] Parsing repository URL: {job.repo_url}")
            repo_info_start = time.time()
            try:
                if not GitHubRepoProcessor.is_valid_github_url(job.repo_url):
                    logger.error(f"[STAGE 0.2] Invalid GitHub URL: {job.repo_url}")
                    raise ValueError(f"Invalid GitHub URL: {job.repo_url}")
                
                repo_info = GitHubRepoProcessor.get_repo_info(job.repo_url)
                repo_info_duration = time.time() - repo_info_start
                
                logger.info(f"[STAGE 0.2] Repo info parsed in {repo_info_duration:.1f}s")
                logger.info(f"[STAGE 0.2] Parsed URL components:")
                logger.info(f"[STAGE 0.2]   - Owner: {repo_info.get('owner', 'N/A')}")
                logger.info(f"[STAGE 0.2]   - Repo: {repo_info.get('repo', 'N/A')}")
                logger.info(f"[STAGE 0.2]   - Full name: {repo_info.get('full_name', 'N/A')}")
                logger.info(f"[STAGE 0.2]   - Clone URL: {repo_info.get('clone_url', 'N/A')}")
            except Exception as e:
                repo_info_duration = time.time() - repo_info_start
                logger.error(f"[STAGE 0.2] Repo info parsing FAILED after {repo_info_duration:.1f}s: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[STAGE 0.2] Traceback: {traceback.format_exc()}")
                raise
            
            # STAGE 0.3: Clone repository
            temp_repo_dir = os.path.join(self.temp_dir, job_id)
            logger.info(f"[STAGE 0.3: CLONE REPOSITORY] Cloning {repo_info['clone_url']}")
            logger.info(f"[STAGE 0.3] Target directory: {temp_repo_dir}")
            logger.info(f"[STAGE 0.3] Commit ID: {job.commit_id if job.commit_id else 'HEAD (shallow clone)'}")
            logger.info(f"[STAGE 0.3] Clone timeout: {WebAppConfig.CLONE_TIMEOUT}s")
            logger.info(f"[STAGE 0.3] Clone depth: {WebAppConfig.CLONE_DEPTH if not job.commit_id else 'full'}")
            
            clone_start = time.time()
            job.progress = f"Cloning repository {repo_info['full_name']}..."
            
            try:
                clone_success = GitHubRepoProcessor.clone_repository(repo_info['clone_url'], temp_repo_dir, job.commit_id)
                clone_duration = time.time() - clone_start
                
                if clone_success:
                    # Verify clone succeeded
                    if os.path.exists(temp_repo_dir):
                        repo_size = sum(f.stat().st_size for f in Path(temp_repo_dir).rglob('*') if f.is_file())
                        file_count = len(list(Path(temp_repo_dir).rglob('*')))
                        logger.info(f"[STAGE 0.3] Clone completed in {clone_duration:.1f}s")
                        logger.info(f"[STAGE 0.3] Repository size: {repo_size} bytes")
                        logger.info(f"[STAGE 0.3] File count: {file_count}")
                        logger.info(f"[STAGE 0.3] Target directory exists: {os.path.exists(temp_repo_dir)}")
                    else:
                        logger.error(f"[STAGE 0.3] Clone reported success but target directory does not exist: {temp_repo_dir}")
                        raise Exception("Clone succeeded but target directory not found")
                else:
                    clone_duration = time.time() - clone_start
                    logger.error(f"[STAGE 0.3] Clone FAILED after {clone_duration:.1f}s")
                    logger.error(f"[STAGE 0.3] Clone URL: {repo_info['clone_url']}")
                    logger.error(f"[STAGE 0.3] Target directory: {temp_repo_dir}")
                    logger.error(f"[STAGE 0.3] Commit ID: {job.commit_id}")
                    raise Exception("Failed to clone repository")
            except subprocess.TimeoutExpired:
                clone_duration = time.time() - clone_start
                logger.error(f"[STAGE 0.3] Clone TIMEOUT after {clone_duration:.1f}s (timeout: {WebAppConfig.CLONE_TIMEOUT}s)")
                logger.error(f"[STAGE 0.3] Clone URL: {repo_info['clone_url']}")
                raise
            except Exception as e:
                clone_duration = time.time() - clone_start
                logger.error(f"[STAGE 0.3] Clone FAILED after {clone_duration:.1f}s: {type(e).__name__}: {str(e)}")
                logger.error(f"[STAGE 0.3] Clone URL: {repo_info['clone_url']}")
                logger.error(f"[STAGE 0.3] Target directory: {temp_repo_dir}")
                import traceback
                logger.error(f"[STAGE 0.3] Traceback: {traceback.format_exc()}")
                raise
            
            # STAGE 0.4: Create config
            logger.info(f"[STAGE 0.4: CONFIG CREATION] Creating configuration")
            logger.info(f"[STAGE 0.4] Repo path: {temp_repo_dir}")
            config_start = time.time()
            
            try:
                import argparse
                args = argparse.Namespace(repo_path=temp_repo_dir)
                config = Config.from_args(args)
                config.docs_dir = os.path.join("output", "docs", f"{job_id}-docs")
                config_duration = time.time() - config_start
                
                logger.info(f"[STAGE 0.4] Config created in {config_duration:.1f}s")
                logger.info(f"[STAGE 0.4] Config values:")
                logger.info(f"[STAGE 0.4]   - Repo path: {config.repo_path}")
                logger.info(f"[STAGE 0.4]   - Output dir: {config.output_dir}")
                logger.info(f"[STAGE 0.4]   - Docs dir: {config.docs_dir}")
                logger.info(f"[STAGE 0.4]   - Dependency graph dir: {config.dependency_graph_dir}")
                logger.info(f"[STAGE 0.4]   - Max depth: {config.max_depth}")
                logger.info(f"[STAGE 0.4]   - Main model: {config.main_model}")
                logger.info(f"[STAGE 0.4]   - Cluster model: {config.cluster_model}")
                logger.info(f"[STAGE 0.4]   - LLM base URL: {config.llm_base_url}")
                logger.info(f"[STAGE 0.4]   - LLM API key: {'*' * 8 if config.llm_api_key else 'NOT SET'}")
                
                # Validate config paths
                if not os.path.exists(config.repo_path):
                    logger.error(f"[STAGE 0.4] Config validation FAILED: repo_path does not exist: {config.repo_path}")
                    raise ValueError(f"Repository path does not exist: {config.repo_path}")
                
                logger.info(f"[STAGE 0.4] Config validation passed")
            except Exception as e:
                config_duration = time.time() - config_start
                logger.error(f"[STAGE 0.4] Config creation FAILED after {config_duration:.1f}s: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[STAGE 0.4] Traceback: {traceback.format_exc()}")
                raise
            
            stage_duration = time.time() - stage_start
            logger.info(f"[STAGE 0: REPOSITORY SETUP] COMPLETE in {stage_duration:.1f}s")
            
            # Generate documentation
            job.progress = "Analyzing repository structure..."
            logger.info(f"[STAGE 0] Starting documentation generation...")
            logger.info(f"[STAGE 0] Commit ID: {job.commit_id}")
            
            doc_gen_start = time.time()
            job.progress = "Generating documentation..."
            
            # Generate documentation
            doc_generator = DocumentationGenerator(config, job.commit_id)
            
            # Run the async documentation generation in a new event loop
            logger.info(f"[STAGE 0] Creating async event loop for documentation generation...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logger.info(f"[STAGE 0] Running documentation generator...")
                loop.run_until_complete(doc_generator.run())
                doc_gen_duration = time.time() - doc_gen_start
                logger.info(f"[STAGE 0] Documentation generation completed in {doc_gen_duration:.1f}s")
            except Exception as e:
                doc_gen_duration = time.time() - doc_gen_start
                logger.error(f"[STAGE 0] Documentation generation FAILED after {doc_gen_duration:.1f}s: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[STAGE 0] Traceback: {traceback.format_exc()}")
                raise
            finally:
                loop.close()
                logger.info(f"[STAGE 0] Event loop closed")
            
            # Cache the results
            logger.info(f"[STAGE 0] Caching documentation results...")
            docs_path = os.path.abspath(config.docs_dir)
            
            try:
                cache_start = time.time()
                self.cache_manager.add_to_cache(job.repo_url, docs_path)
                cache_duration = time.time() - cache_start
                logger.info(f"[STAGE 0] Results cached in {cache_duration:.3f}s")
                logger.info(f"[STAGE 0] Cache path: {docs_path}")
            except Exception as e:
                logger.error(f"[STAGE 0] Failed to cache results: {type(e).__name__}: {str(e)}")
                # Non-critical, continue
            
            # Update job status
            job.status = 'completed'
            job.completed_at = datetime.now()
            job.docs_path = docs_path
            job.progress = "Documentation generation completed"
            
            # Save job status to disk
            try:
                self.save_job_statuses()
                logger.info(f"[STAGE 0] Job status saved to disk")
            except Exception as e:
                logger.error(f"[STAGE 0] Failed to save job status: {type(e).__name__}: {str(e)}")
                # Non-critical, continue
            
            total_duration = time.time() - stage_start
            logger.info(f"[STAGE 0] Job {job_id} COMPLETED successfully in {total_duration:.1f}s")
            print(f"Job {job_id}: Documentation generated successfully")
            
        except Exception as e:
            total_duration = time.time() - stage_start if 'stage_start' in locals() else 0
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Update job status with error
            job.status = 'failed'
            job.completed_at = datetime.now()
            job.error_message = error_msg
            job.progress = f"Failed: {error_msg}"
            
            logger.error(f"[STAGE 0] Job {job_id} FAILED after {total_duration:.1f}s")
            logger.error(f"[STAGE 0] Error type: {error_type}")
            logger.error(f"[STAGE 0] Error message: {error_msg}")
            logger.error(f"[STAGE 0] Job status updated to 'failed'")
            
            # Try to save job status even on failure
            try:
                self.save_job_statuses()
                logger.info(f"[STAGE 0] Failed job status saved to disk")
            except Exception as save_error:
                logger.error(f"[STAGE 0] Failed to save failed job status: {type(save_error).__name__}: {str(save_error)}")
            
            import traceback
            logger.error(f"[STAGE 0] Full traceback:\n{traceback.format_exc()}")
            print(f"Job {job_id}: Failed with error: {e}")
        
        finally:
            # Cleanup temporary repository
            cleanup_start = time.time()
            if 'temp_repo_dir' in locals() and os.path.exists(temp_repo_dir):
                try:
                    logger.info(f"[STAGE 0] Cleaning up temporary repository: {temp_repo_dir}")
                    subprocess.run(['rm', '-rf', temp_repo_dir], check=True, timeout=30)
                    cleanup_duration = time.time() - cleanup_start
                    logger.info(f"[STAGE 0] Cleanup completed in {cleanup_duration:.3f}s")
                except subprocess.TimeoutExpired:
                    cleanup_duration = time.time() - cleanup_start
                    logger.warning(f"[STAGE 0] Cleanup TIMEOUT after {cleanup_duration:.1f}s (timeout: 30s)")
                    logger.warning(f"[STAGE 0] Temporary directory may not be fully removed: {temp_repo_dir}")
                except Exception as e:
                    cleanup_duration = time.time() - cleanup_start
                    logger.error(f"[STAGE 0] Cleanup FAILED after {cleanup_duration:.3f}s: {type(e).__name__}: {str(e)}")
                    logger.error(f"[STAGE 0] Temporary directory not removed: {temp_repo_dir}")
                    print(f"Failed to cleanup temp directory: {e}")
            else:
                if 'temp_repo_dir' not in locals():
                    logger.info(f"[STAGE 0] No temporary directory to cleanup (not created)")
                else:
                    logger.info(f"[STAGE 0] No temporary directory to cleanup (does not exist): {temp_repo_dir if 'temp_repo_dir' in locals() else 'N/A'}")