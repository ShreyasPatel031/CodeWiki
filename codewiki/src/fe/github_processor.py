#!/usr/bin/env python3
"""
GitHub repository processing utilities.
"""

import os
import subprocess
import logging
import time
from typing import Dict
from urllib.parse import urlparse

from .config import WebAppConfig

logger = logging.getLogger(__name__)


class GitHubRepoProcessor:
    """Handles GitHub repository processing."""
    
    @staticmethod
    def is_valid_github_url(url: str) -> bool:
        """Validate if the URL is a valid GitHub repository URL."""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() not in ['github.com', 'www.github.com']:
                return False
            
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) < 2:
                return False
            
            # Check if it's a valid repo path (owner/repo)
            return len(path_parts) >= 2 and all(part for part in path_parts[:2])
        except Exception:
            return False
    
    @staticmethod
    def get_repo_info(url: str) -> Dict[str, str]:
        """Extract repository information from GitHub URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        owner = path_parts[0]
        repo = path_parts[1]
        
        # Remove .git suffix if present
        if repo.endswith('.git'):
            repo = repo[:-4]
        
        return {
            'owner': owner,
            'repo': repo,
            'full_name': f"{owner}/{repo}",
            'clone_url': f"https://github.com/{owner}/{repo}.git"
        }
    
    @staticmethod
    def clone_repository(clone_url: str, target_dir: str, commit_id: str = None) -> bool:
        """Clone a GitHub repository to the target directory, optionally checking out a specific commit."""
        clone_start = time.time()
        logger.info(f"[STAGE 0.3] Starting git clone operation")
        logger.info(f"[STAGE 0.3] Clone URL: {clone_url}")
        logger.info(f"[STAGE 0.3] Target directory: {target_dir}")
        logger.info(f"[STAGE 0.3] Commit ID: {commit_id if commit_id else 'None (shallow clone)'}")
        
        try:
            # Ensure target directory parent exists
            target_parent = os.path.dirname(target_dir)
            if target_parent:
                os.makedirs(target_parent, exist_ok=True)
                logger.info(f"[STAGE 0.3] Created parent directory: {target_parent}")
            
            # If specific commit is requested, don't use shallow clone
            if commit_id:
                logger.info(f"[STAGE 0.3] Using full clone (no depth limit) for commit checkout")
                logger.info(f"[STAGE 0.3] Executing: git clone {clone_url} {target_dir}")
                
                clone_cmd_start = time.time()
                result = subprocess.run([
                    'git', 'clone', clone_url, target_dir
                ], capture_output=True, text=True, timeout=WebAppConfig.CLONE_TIMEOUT)
                clone_cmd_duration = time.time() - clone_cmd_start
                
                logger.info(f"[STAGE 0.3] Git clone command completed in {clone_cmd_duration:.1f}s")
                logger.info(f"[STAGE 0.3] Return code: {result.returncode}")
                
                if result.returncode != 0:
                    logger.error(f"[STAGE 0.3] Git clone FAILED with return code {result.returncode}")
                    logger.error(f"[STAGE 0.3] Stderr: {result.stderr}")
                    logger.error(f"[STAGE 0.3] Stdout: {result.stdout}")
                    return False
                
                logger.info(f"[STAGE 0.3] Git clone succeeded")
                logger.info(f"[STAGE 0.3] Clone output: {result.stdout[:500] if result.stdout else 'No output'}")
                
                # Checkout specific commit
                logger.info(f"[STAGE 0.3] Checking out commit: {commit_id}")
                logger.info(f"[STAGE 0.3] Executing: git checkout {commit_id} (in {target_dir})")
                
                checkout_start = time.time()
                result = subprocess.run([
                    'git', 'checkout', commit_id
                ], cwd=target_dir, capture_output=True, text=True, timeout=30)
                checkout_duration = time.time() - checkout_start
                
                logger.info(f"[STAGE 0.3] Git checkout command completed in {checkout_duration:.1f}s")
                logger.info(f"[STAGE 0.3] Return code: {result.returncode}")
                
                if result.returncode != 0:
                    logger.error(f"[STAGE 0.3] Git checkout FAILED with return code {result.returncode}")
                    logger.error(f"[STAGE 0.3] Commit ID: {commit_id}")
                    logger.error(f"[STAGE 0.3] Working directory: {target_dir}")
                    logger.error(f"[STAGE 0.3] Stderr: {result.stderr}")
                    logger.error(f"[STAGE 0.3] Stdout: {result.stdout}")
                    return False
                
                logger.info(f"[STAGE 0.3] Git checkout succeeded")
                logger.info(f"[STAGE 0.3] Checkout output: {result.stdout[:500] if result.stdout else 'No output'}")
            else:
                logger.info(f"[STAGE 0.3] Using shallow clone (depth={WebAppConfig.CLONE_DEPTH})")
                logger.info(f"[STAGE 0.3] Executing: git clone --depth {WebAppConfig.CLONE_DEPTH} {clone_url} {target_dir}")
                
                clone_cmd_start = time.time()
                result = subprocess.run([
                    'git', 'clone', '--depth', str(WebAppConfig.CLONE_DEPTH), clone_url, target_dir
                ], capture_output=True, text=True, timeout=WebAppConfig.CLONE_TIMEOUT)
                clone_cmd_duration = time.time() - clone_cmd_start
                
                logger.info(f"[STAGE 0.3] Git clone command completed in {clone_cmd_duration:.1f}s")
                logger.info(f"[STAGE 0.3] Return code: {result.returncode}")
                
                if result.returncode != 0:
                    logger.error(f"[STAGE 0.3] Git clone FAILED with return code {result.returncode}")
                    logger.error(f"[STAGE 0.3] Clone URL: {clone_url}")
                    logger.error(f"[STAGE 0.3] Target directory: {target_dir}")
                    logger.error(f"[STAGE 0.3] Depth: {WebAppConfig.CLONE_DEPTH}")
                    logger.error(f"[STAGE 0.3] Timeout: {WebAppConfig.CLONE_TIMEOUT}s")
                    logger.error(f"[STAGE 0.3] Stderr: {result.stderr}")
                    logger.error(f"[STAGE 0.3] Stdout: {result.stdout}")
                    return False
                
                logger.info(f"[STAGE 0.3] Git clone succeeded")
                logger.info(f"[STAGE 0.3] Clone output: {result.stdout[:500] if result.stdout else 'No output'}")
            
            # Verify clone succeeded
            if not os.path.exists(target_dir):
                logger.error(f"[STAGE 0.3] Clone reported success but target directory does not exist: {target_dir}")
                return False
            
            git_dir = os.path.join(target_dir, '.git')
            if not os.path.exists(git_dir):
                logger.error(f"[STAGE 0.3] Clone reported success but .git directory does not exist: {git_dir}")
                return False
            
            clone_duration = time.time() - clone_start
            logger.info(f"[STAGE 0.3] Clone operation COMPLETE in {clone_duration:.1f}s")
            logger.info(f"[STAGE 0.3] Repository verified at: {target_dir}")
            
            return True
        except subprocess.TimeoutExpired as e:
            clone_duration = time.time() - clone_start
            logger.error(f"[STAGE 0.3] Clone TIMEOUT after {clone_duration:.1f}s (timeout: {WebAppConfig.CLONE_TIMEOUT}s)")
            logger.error(f"[STAGE 0.3] Clone URL: {clone_url}")
            logger.error(f"[STAGE 0.3] Target directory: {target_dir}")
            logger.error(f"[STAGE 0.3] Exception: {type(e).__name__}: {str(e)}")
            return False
        except Exception as e:
            clone_duration = time.time() - clone_start
            logger.error(f"[STAGE 0.3] Clone FAILED after {clone_duration:.1f}s: {type(e).__name__}: {str(e)}")
            logger.error(f"[STAGE 0.3] Clone URL: {clone_url}")
            logger.error(f"[STAGE 0.3] Target directory: {target_dir}")
            import traceback
            logger.error(f"[STAGE 0.3] Traceback: {traceback.format_exc()}")
            return False