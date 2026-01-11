"""
HTML generator for GitHub Pages documentation viewer.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from codewiki.cli.utils.errors import FileSystemError
from codewiki.cli.utils.fs import safe_write, safe_read

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """
    Generates static HTML documentation viewer for GitHub Pages.
    
    Creates a self-contained index.html with embedded styles, scripts,
    and configuration for client-side markdown rendering.
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize HTML generator.
        
        Args:
            template_dir: Path to template directory (default: package templates)
        """
        if template_dir is None:
            # Use package templates
            template_dir = Path(__file__).parent.parent / "templates" / "github_pages"
        
        self.template_dir = Path(template_dir)
        
    
    def load_module_tree(self, docs_dir: Path) -> Dict[str, Any]:
        """
        Load module tree from documentation directory.
        
        Args:
            docs_dir: Documentation directory path
            
        Returns:
            Module tree structure
        """
        logger.info(f"[STAGE 5] Loading module tree...")
        logger.info(f"[STAGE 5] Docs directory: {docs_dir}")
        
        module_tree_path = docs_dir / "module_tree.json"
        logger.info(f"[STAGE 5] Module tree path: {module_tree_path}")
        logger.info(f"[STAGE 5] Module tree path exists: {module_tree_path.exists()}")
        
        if not module_tree_path.exists():
            logger.warning(f"[STAGE 5] CRITICAL: module_tree.json not found at {module_tree_path}")
            logger.warning(f"[STAGE 5] Using fallback structure - module viewer may not work correctly")
            # Fallback to a simple structure
            return {
                "Overview": {
                    "description": "Repository overview",
                    "components": [],
                    "children": {}
                }
            }
        
        try:
            load_start = time.time()
            logger.info(f"[STAGE 5] Reading module_tree.json...")
            content = safe_read(module_tree_path)
            file_size_bytes = module_tree_path.stat().st_size if module_tree_path.exists() else 0
            logger.info(f"[STAGE 5] File read: {len(content)} chars, {file_size_bytes} bytes")
            
            parse_start = time.time()
            module_tree = json.loads(content)
            parse_duration = time.time() - parse_start
            load_duration = time.time() - load_start
            
            logger.info(f"[STAGE 5] JSON parsing completed in {parse_duration:.3f}s")
            logger.info(f"[STAGE 5] Successfully loaded module tree: {len(module_tree)} modules")
            logger.info(f"[STAGE 5] Total load time: {load_duration:.3f}s")
            
            # Validate module tree structure
            if not isinstance(module_tree, dict):
                logger.error(f"[STAGE 5] CRITICAL: Module tree is not a dict, got {type(module_tree)}")
                raise ValueError(f"Invalid module tree format: expected dict, got {type(module_tree)}")
            
            if len(module_tree) == 0:
                logger.warning(f"[STAGE 5] WARNING: Module tree is empty - module viewer will fail")
                logger.warning(f"[STAGE 5] This indicates clustering failed or returned empty result")
            else:
                logger.info(f"[STAGE 5] Module tree keys: {list(module_tree.keys())[:10]}")
            
            return module_tree
        except json.JSONDecodeError as e:
            logger.error(f"[STAGE 5] CRITICAL: Failed to parse module_tree.json as JSON: {e}")
            logger.error(f"[STAGE 5] JSON error position: line {e.lineno}, column {e.colno}")
            logger.error(f"[STAGE 5] Error message: {e.msg}")
            if hasattr(e, 'pos') and module_tree_path.exists():
                content_preview = safe_read(module_tree_path)[max(0, e.pos-100):e.pos+100]
                logger.error(f"[STAGE 5] Content around error: ...{content_preview}...")
            logger.error(f"[STAGE 5] File may be corrupted")
            raise FileSystemError(f"Failed to parse module tree JSON: {e}")
        except Exception as e:
            logger.error(f"[STAGE 5] CRITICAL: Failed to load module tree: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[STAGE 5] Traceback: {traceback.format_exc()}")
            raise FileSystemError(f"Failed to load module tree: {e}")
    
    def load_metadata(self, docs_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Load metadata from documentation directory.
        
        Args:
            docs_dir: Documentation directory path
            
        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = docs_dir / "metadata.json"
        logger.info(f"[STAGE 5] Loading metadata from {metadata_path}...")
        logger.info(f"[STAGE 5] Metadata path exists: {metadata_path.exists()}")
        
        if not metadata_path.exists():
            logger.info(f"[STAGE 5] metadata.json not found at {metadata_path}. Returning None.")
            return None
        
        try:
            load_start = time.time()
            content = safe_read(metadata_path)
            file_size_bytes = metadata_path.stat().st_size if metadata_path.exists() else 0
            logger.info(f"[STAGE 5] Metadata file read: {len(content)} chars, {file_size_bytes} bytes")
            
            parse_start = time.time()
            metadata = json.loads(content)
            parse_duration = time.time() - parse_start
            load_duration = time.time() - load_start
            
            logger.info(f"[STAGE 5] Metadata JSON parsing completed in {parse_duration:.3f}s")
            logger.info(f"[STAGE 5] Successfully loaded metadata")
            logger.info(f"[STAGE 5] Metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")
            logger.info(f"[STAGE 5] Total load time: {load_duration:.3f}s")
            return metadata
        except json.JSONDecodeError as e:
            logger.warning(f"[STAGE 5] Failed to parse metadata.json as JSON: {e}")
            logger.warning(f"[STAGE 5] JSON error: line {e.lineno}, column {e.colno}, {e.msg}")
            logger.warning(f"[STAGE 5] Returning None (non-critical)")
            return None
        except Exception as e:
            logger.warning(f"[STAGE 5] Failed to load metadata: {type(e).__name__}: {str(e)}")
            logger.warning(f"[STAGE 5] Returning None (non-critical)")
            import traceback
            logger.debug(f"[STAGE 5] Traceback: {traceback.format_exc()}")
            return None
            
    def generate(
        self,
        output_path: Path,
        title: str,
        module_tree: Optional[Dict[str, Any]] = None,
        repository_url: Optional[str] = None,
        github_pages_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        docs_dir: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Generate HTML documentation viewer.
        
        Args:
            output_path: Output file path (index.html)
            title: Documentation title
            module_tree: Module tree structure (auto-loaded from docs_dir if not provided)
            repository_url: GitHub repository URL
            github_pages_url: Expected GitHub Pages URL
            config: Additional configuration
            docs_dir: Documentation directory (for auto-loading module_tree and metadata)
            metadata: Metadata dictionary (auto-loaded from docs_dir if not provided)
        """
        stage_start = time.time()
        logger.info(f"[STAGE 5: HTML GENERATION] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[STAGE 5] Output path: {output_path}")
        logger.info(f"[STAGE 5] Title: {title}")
        logger.info(f"[STAGE 5] Docs directory: {docs_dir}")
        logger.info(f"[STAGE 5] Template directory: {self.template_dir}")
        
        # Check expected files before generation
        if docs_dir:
            expected_files = ["module_tree.json", "metadata.json", "overview.md"]
            logger.info(f"[STAGE 5] Checking for expected files in {docs_dir}...")
            for expected_file in expected_files:
                file_path = docs_dir / expected_file
                exists = file_path.exists()
                size = file_path.stat().st_size if exists else 0
                logger.info(f"[STAGE 5]   - {expected_file}: {'exists' if exists else 'MISSING'} ({size} bytes)" )
        
        # Auto-load module_tree and metadata from docs_dir if not provided
        docs_content = {}  # Embedded markdown content
        if docs_dir:
            if module_tree is None:
                logger.info(f"[STAGE 5] Auto-loading module tree from docs_dir...")
                module_tree = self.load_module_tree(docs_dir)
            else:
                logger.info(f"[STAGE 5] Using provided module tree: {len(module_tree)} modules")
            
            if metadata is None:
                logger.info(f"[STAGE 5] Auto-loading metadata from docs_dir...")
                metadata = self.load_metadata(docs_dir)
            else:
                logger.info(f"[STAGE 5] Using provided metadata")
            
            # Load all markdown files and embed them
            logger.info(f"[STAGE 5] Loading markdown files for embedding...")
            try:
                for md_file in docs_dir.glob("*.md"):
                    try:
                        content = safe_read(md_file)
                        docs_content[md_file.name] = content
                        logger.info(f"[STAGE 5]   - Loaded {md_file.name}: {len(content)} chars")
                    except Exception as e:
                        logger.warning(f"[STAGE 5]   - Failed to load {md_file.name}: {e}")
                logger.info(f"[STAGE 5] Embedded {len(docs_content)} markdown files")
            except Exception as e:
                logger.warning(f"[STAGE 5] Failed to load markdown files: {e}")
        
        # Default values
        if module_tree is None:
            module_tree = {}
        if config is None:
            config = {}
        
        # Load template
        template_path = self.template_dir / "viewer_template.html"
        logger.info(f"[STAGE 5] Template path: {template_path}")
        if not template_path.exists():
            logger.error(f"[STAGE 5] CRITICAL: Template not found: {template_path}")
            raise FileSystemError(f"Template not found: {template_path}")
        
        try:
            logger.info(f"[STAGE 5] Reading template...")
            template_content = safe_read(template_path)
            logger.info(f"[STAGE 5] Template size: {len(template_content)} chars")
        except Exception as e:
            logger.error(f"[STAGE 5] Failed to read template: {e}")
            raise
        
        # Build info content HTML
        logger.info(f"[STAGE 5] Building info content...")
        info_content = self._build_info_content(metadata)
        show_info = "block" if info_content else "none"
        logger.info(f"[STAGE 5] Info content: {len(info_content)} chars, show_info: {show_info}")
        
        # Build repository link
        repo_link = ""
        if repository_url:
            repo_link = f'<a href="{repository_url}" class="repo-link" target="_blank">🔗 View Repository</a>'
            logger.info(f"[STAGE 5] Repository URL: {repository_url}")
        
        # Determine docs base path
        # For GitHub Pages: relative path to docs folder
        # For local: relative path to docs folder
        docs_base_path = ""
        if docs_dir and output_path.parent != docs_dir:
            # Calculate relative path from output to docs
            try:
                docs_base_path = Path(docs_dir.name).as_posix()
                logger.info(f"[STAGE 5] Docs base path: {docs_base_path}")
            except Exception as e:
                logger.warning(f"[STAGE 5] Failed to calculate docs base path: {e}, using '.'")
                docs_base_path = "."
        
        # Prepare JSON data for embedding
        logger.info(f"[STAGE 5] Preparing JSON data for embedding...")
        try:
            config_json = json.dumps(config, indent=2)
            logger.info(f"[STAGE 5] Config JSON: {len(config_json)} chars")
        except Exception as e:
            logger.error(f"[STAGE 5] Failed to serialize config: {e}")
            config_json = "{}"
        
        try:
            module_tree_json = json.dumps(module_tree, indent=2)
            logger.info(f"[STAGE 5] Module tree JSON: {len(module_tree_json)} chars")
        except Exception as e:
            logger.error(f"[STAGE 5] CRITICAL: Failed to serialize module tree: {e}")
            logger.error(f"[STAGE 5] Module tree type: {type(module_tree)}, content: {str(module_tree)[:200]}...")
            raise
        
        try:
            metadata_json = json.dumps(metadata, indent=2) if metadata else "null"
            logger.info(f"[STAGE 5] Metadata JSON: {len(metadata_json)} chars")
        except Exception as e:
            logger.warning(f"[STAGE 5] Failed to serialize metadata: {e}, using null")
            metadata_json = "null"
        
        try:
            docs_content_json = json.dumps(docs_content, indent=2) if docs_content else "{}"
            logger.info(f"[STAGE 5] Docs content JSON: {len(docs_content_json)} chars ({len(docs_content)} files)")
        except Exception as e:
            logger.warning(f"[STAGE 5] Failed to serialize docs content: {e}, using empty")
            docs_content_json = "{}"
        
        # Replace placeholders
        logger.info(f"[STAGE 5] Replacing placeholders in template...")
        html_content = template_content
        replacements = {
            "{{TITLE}}": self._escape_html(title),
            "{{REPO_LINK}}": repo_link,
            "{{SHOW_INFO}}": show_info,
            "{{INFO_CONTENT}}": info_content,
            "{{CONFIG_JSON}}": config_json,
            "{{MODULE_TREE_JSON}}": module_tree_json,
            "{{METADATA_JSON}}": metadata_json,
            "{{DOCS_BASE_PATH}}": docs_base_path,
            "{{DOCS_CONTENT_JSON}}": docs_content_json,
        }
        
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)
        
        logger.info(f"[STAGE 5] Template processing complete, HTML size: {len(html_content)} chars")
        
        # Write output
        output_path = Path(output_path)
        logger.info(f"[STAGE 5] Writing output to {output_path}...")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[STAGE 5] Created output directory: {output_path.parent}")
        except Exception as e:
            logger.error(f"[STAGE 5] Failed to create output directory: {e}")
            raise
        
        try:
            # #region agent log
            output_path_str = str(output_path.resolve())
            with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"html_generator.py:311","message":"BEFORE safe_write call","data":{"output_path":output_path_str,"html_content_length":len(html_content),"parent_dir":str(output_path.parent),"parent_exists":output_path.parent.exists()},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            safe_write(output_path, html_content)
            # #region agent log
            file_size_check = output_path.stat().st_size if output_path.exists() else 0
            with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"html_generator.py:312","message":"AFTER safe_write call","data":{"output_path":output_path_str,"file_exists":output_path.exists(),"file_size":file_size_check},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            file_size = output_path.stat().st_size
            logger.info(f"[STAGE 5] Successfully wrote HTML file: {file_size} bytes")
        except Exception as e:
            # #region agent log
            import traceback
            exc_traceback = traceback.format_exc()
            with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"html_generator.py:315","message":"safe_write EXCEPTION caught in generate","data":{"exception_type":type(e).__name__,"exception_msg":str(e),"output_path":output_path_str,"traceback":exc_traceback[:500]},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            logger.error(f"[STAGE 5] CRITICAL: Failed to write HTML file: {e}")
            raise
        
        stage_duration = time.time() - stage_start
        # #region agent log
        final_check_path = output_path.resolve()
        final_exists = final_check_path.exists()
        final_size = final_check_path.stat().st_size if final_exists else 0
        with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C,E,F","location":"html_generator.py:319","message":"generate EXIT - SUCCESS","data":{"duration":stage_duration,"final_path":str(final_check_path),"final_exists":final_exists,"final_size":final_size},"timestamp":int(time.time()*1000)})+"\n")
        # #endregion
        logger.info(f"[STAGE 5: HTML GENERATION] COMPLETE in {stage_duration:.1f}s")
    
    def _build_info_content(self, metadata: Optional[Dict[str, Any]]) -> str:
        """
        Build HTML content for repo info section.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            HTML string for info content
        """
        if not metadata or not metadata.get('generation_info'):
            return ""
        
        info = metadata.get('generation_info', {})
        stats = metadata.get('statistics', {})
        
        html_parts = []
        
        if info.get('main_model'):
            html_parts.append(f'<div class="info-row"><strong>Model:</strong> {self._escape_html(info["main_model"])}</div>')
        
        if info.get('timestamp'):
            try:
                from datetime import datetime
                timestamp = info['timestamp']
                # Parse ISO format timestamp
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d')
                    html_parts.append(f'<div class="info-row"><strong>Generated:</strong> {formatted_date}</div>')
            except Exception:
                pass
        
        if info.get('commit_id'):
            commit_short = info['commit_id'][:8]
            html_parts.append(f'<div class="info-row"><strong>Commit:</strong> {commit_short}</div>')
        
        if stats.get('total_components'):
            components_str = f"{stats['total_components']:,}"
            html_parts.append(f'<div class="info-row"><strong>Components:</strong> {components_str}</div>')
        
        if stats.get('max_depth'):
            html_parts.append(f'<div class="info-row"><strong>Max Depth:</strong> {stats["max_depth"]}</div>')
        
        return '\n                '.join(html_parts)
    
    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
       

    
    def detect_repository_info(self, repo_path: Path) -> Dict[str, Optional[str]]:
        """
        Detect repository information from git.
        
        Args:
            repo_path: Repository path
            
        Returns:
            Dictionary with 'name', 'url', 'github_pages_url'
        """
        info = {
            'name': repo_path.name,
            'url': None,
            'github_pages_url': None,
        }
        
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Get repository name
            info['name'] = repo_path.name
            
            # Get remote URL
            if repo.remotes:
                remote_url = repo.remotes.origin.url
                
                # Clean URL
                if remote_url.startswith('git@github.com:'):
                    remote_url = remote_url.replace('git@github.com:', 'https://github.com/')
                
                remote_url = remote_url.rstrip('/').replace('.git', '')
                info['url'] = remote_url
                
                # Compute GitHub Pages URL
                if 'github.com' in remote_url:
                    parts = remote_url.split('/')
                    if len(parts) >= 2:
                        owner = parts[-2]
                        repo = parts[-1]
                        info['github_pages_url'] = f"https://{owner}.github.io/{repo}/"
        
        except Exception:
            pass
        
        return info

