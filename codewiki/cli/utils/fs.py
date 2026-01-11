"""
File system utilities for CLI operations.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List

from codewiki.cli.utils.errors import FileSystemError


def ensure_directory(path: Path, mode: int = 0o700) -> Path:
    """
    Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path
        mode: Directory permissions (default: 0o700 - user only)
        
    Returns:
        Path to the directory
        
    Raises:
        FileSystemError: If directory cannot be created
    """
    try:
        path = Path(path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        return path
    except PermissionError:
        raise FileSystemError(
            f"Permission denied: Cannot create directory {path}\n"
            f"Try: chmod u+w {path.parent}"
        )
    except OSError as e:
        raise FileSystemError(f"Cannot create directory {path}: {e}")


def check_writable(path: Path) -> bool:
    """
    Check if a path is writable.
    
    Args:
        path: Path to check
        
    Returns:
        True if writable, False otherwise
    """
    path = Path(path).expanduser().resolve()
    
    if path.exists():
        return os.access(path, os.W_OK)
    else:
        # Check parent directory if path doesn't exist
        parent = path.parent
        return parent.exists() and os.access(parent, os.W_OK)


def safe_write(path: Path, content: str, encoding: str = "utf-8"):
    """
    Safely write content to a file using atomic write (temp file + rename).
    
    Args:
        path: File path
        content: Content to write
        encoding: File encoding
        
    Raises:
        FileSystemError: If write fails
    """
    # #region agent log
    import json
    import time as time_module
    path_str = str(path)
    resolved_path = str(Path(path).expanduser().resolve())
    with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"fs.py:60","message":"safe_write ENTRY","data":{"input_path":path_str,"resolved_path":resolved_path,"content_length":len(content),"encoding":encoding},"timestamp":int(time_module.time()*1000)})+"\n")
    # #endregion
    path = Path(path).expanduser().resolve()
    temp_path = path.with_suffix(path.suffix + ".tmp")
    # #region agent log
    with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"fs.py:73","message":"safe_write BEFORE temp write","data":{"final_path":str(path),"temp_path":str(temp_path),"parent_exists":path.parent.exists()},"timestamp":int(time_module.time()*1000)})+"\n")
    # #endregion
    
    try:
        # Write to temp file
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)
        # #region agent log
        temp_size_after = temp_path.stat().st_size if temp_path.exists() else 0
        with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"fs.py:77","message":"safe_write AFTER temp write","data":{"temp_path":str(temp_path),"temp_exists":temp_path.exists(),"temp_size":temp_size_after},"timestamp":int(time_module.time()*1000)})+"\n")
        # #endregion
        
        # Atomic rename
        target_exists_before = path.exists()
        temp_path.replace(path)
        # #region agent log
        target_exists_after = path.exists()
        target_size_after = path.stat().st_size if target_exists_after else 0
        temp_still_exists = temp_path.exists()
        with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"fs.py:81","message":"safe_write AFTER atomic rename","data":{"target_path":str(path),"target_existed_before":target_exists_before,"target_exists_after":target_exists_after,"target_size":target_size_after,"temp_still_exists":temp_still_exists},"timestamp":int(time_module.time()*1000)})+"\n")
        # #endregion
    except Exception as e:
        # #region agent log
        import traceback
        exc_traceback = traceback.format_exc()
        temp_exists_on_error = temp_path.exists() if 'temp_path' in locals() else False
        with open('/Users/shreyaspatel/CodeWiki/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"fs.py:82","message":"safe_write EXCEPTION","data":{"exception_type":type(e).__name__,"exception_msg":str(e),"target_path":str(path),"temp_exists":temp_exists_on_error,"traceback":exc_traceback[:500]},"timestamp":int(time_module.time()*1000)})+"\n")
        # #endregion
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise FileSystemError(f"Cannot write to {path}: {e}")


def safe_read(path: Path, encoding: str = "utf-8") -> str:
    """
    Safely read content from a file.
    
    Args:
        path: File path
        encoding: File encoding
        
    Returns:
        File content
        
    Raises:
        FileSystemError: If read fails
    """
    path = Path(path).expanduser().resolve()
    
    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise FileSystemError(f"File not found: {path}")
    except PermissionError:
        raise FileSystemError(f"Permission denied: Cannot read {path}")
    except Exception as e:
        raise FileSystemError(f"Cannot read {path}: {e}")


def get_file_size(path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes
    """
    return Path(path).stat().st_size


def find_files(
    directory: Path,
    extensions: Optional[List[str]] = None,
    recursive: bool = True
) -> List[Path]:
    """
    Find files in directory matching extensions.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions (e.g., ['.py', '.java'])
        recursive: Search recursively
        
    Returns:
        List of matching file paths
    """
    directory = Path(directory).expanduser().resolve()
    
    if not directory.exists():
        return []
    
    pattern = "**/*" if recursive else "*"
    files = []
    
    for path in directory.glob(pattern):
        if not path.is_file():
            continue
        
        if extensions is None or path.suffix in extensions:
            files.append(path)
    
    return files


def cleanup_directory(path: Path, keep_hidden: bool = True):
    """
    Clean up a directory by removing its contents.
    
    Args:
        path: Directory to clean
        keep_hidden: Keep hidden files/directories (starting with .)
        
    Raises:
        FileSystemError: If cleanup fails
    """
    path = Path(path).expanduser().resolve()
    
    if not path.exists():
        return
    
    try:
        for item in path.iterdir():
            if keep_hidden and item.name.startswith('.'):
                continue
            
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    except Exception as e:
        raise FileSystemError(f"Cannot clean directory {path}: {e}")

