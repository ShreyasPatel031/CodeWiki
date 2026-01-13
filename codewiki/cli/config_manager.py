"""
Configuration manager - stores all config including API key in config.json.
"""

import json
import os
from pathlib import Path
from typing import Optional

from codewiki.cli.models.config import Configuration
from codewiki.cli.utils.errors import ConfigurationError, FileSystemError
from codewiki.cli.utils.fs import ensure_directory, safe_write, safe_read


# Configuration file location
CONFIG_DIR = Path.home() / ".codewiki"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_VERSION = "1.0"


class ConfigManager:
    """
    Manages CodeWiki configuration.
    
    Storage:
        - All settings including API key: ~/.codewiki/config.json
        - Environment variable fallback: GEMINI_API_KEY or LLM_API_KEY
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._api_key: Optional[str] = None
        self._config: Optional[Configuration] = None
    
    def load(self) -> bool:
        """
        Load configuration from file.
        
        Returns:
            True if configuration exists, False otherwise
        """
        # Load from JSON file
        if not CONFIG_FILE.exists():
            return False
        
        try:
            content = safe_read(CONFIG_FILE)
            data = json.loads(content)
            
            # Validate version
            if data.get('version') != CONFIG_VERSION:
                # Could implement migration here
                pass
            
            self._config = Configuration.from_dict(data)
            
            # Load API key from config file or env var
            self._api_key = data.get('api_key') or os.getenv('GEMINI_API_KEY') or os.getenv('LLM_API_KEY')
            
            return True
        except (json.JSONDecodeError, FileSystemError) as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def save(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        main_model: Optional[str] = None,
        cluster_model: Optional[str] = None,
        default_output: Optional[str] = None
    ):
        """
        Save configuration to file.
        
        Args:
            api_key: API key (stored in config file)
            base_url: LLM API base URL
            main_model: Primary model
            cluster_model: Clustering model
            default_output: Default output directory
        """
        # Ensure config directory exists
        try:
            ensure_directory(CONFIG_DIR)
        except FileSystemError as e:
            raise ConfigurationError(f"Cannot create config directory: {e}")
        
        # Load existing config or create new
        if self._config is None:
            if CONFIG_FILE.exists():
                self.load()
            else:
                self._config = Configuration(
                    base_url="",
                    main_model="",
                    cluster_model="",
                    default_output="docs"
                )
        
        # Update fields if provided
        if base_url is not None:
            self._config.base_url = base_url
        if main_model is not None:
            self._config.main_model = main_model
        if cluster_model is not None:
            self._config.cluster_model = cluster_model
        if default_output is not None:
            self._config.default_output = default_output
        
        # Validate configuration
        self._config.validate()
        
        # Update API key
        if api_key is not None:
            self._api_key = api_key
        
        # Save everything to JSON (including API key)
        config_data = {
            "version": CONFIG_VERSION,
            "api_key": self._api_key,
            **self._config.to_dict()
        }
        
        try:
            safe_write(CONFIG_FILE, json.dumps(config_data, indent=2))
        except FileSystemError as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get_api_key(self) -> Optional[str]:
        """
        Get API key from config or environment.
        
        Returns:
            API key or None if not set
        """
        if self._api_key is None:
            # Try environment variables as fallback
            self._api_key = os.getenv('GEMINI_API_KEY') or os.getenv('LLM_API_KEY')
        
        return self._api_key
    
    def get_config(self) -> Optional[Configuration]:
        """
        Get current configuration.
        
        Returns:
            Configuration object or None if not loaded
        """
        return self._config
    
    def is_configured(self) -> bool:
        """
        Check if configuration is complete and valid.
        
        Returns:
            True if configured, False otherwise
        """
        if self._config is None:
            return False
        
        # Check if API key is set
        if self.get_api_key() is None:
            return False
        
        # Check if config is complete
        return self._config.is_complete()
    
    def delete_api_key(self):
        """Delete API key."""
        self._api_key = None
        # Re-save config without API key
        if self._config:
            self.save()
    
    def clear(self):
        """Clear all configuration."""
        # Delete config file
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        
        self._config = None
        self._api_key = None
    
    @property
    def keyring_available(self) -> bool:
        """Kept for compatibility - always returns False now."""
        return False
    
    @property
    def config_file_path(self) -> Path:
        """Get configuration file path."""
        return CONFIG_FILE
