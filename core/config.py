"""
Configuration handling for ImCull
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional
import xdg.BaseDirectory

logger = logging.getLogger('imcull.core.config')

DEFAULT_CONFIG = {
    'import': {
        'default_source_dir': '',
        'default_destination_dir': os.path.expanduser('~/Pictures'),
        'backup_locations': [],
    },
    'culling': {
        'blur_detection_threshold': 100,  # Higher values are more lenient
        'auto_advance': True,
        'show_histograms': True,
        'show_metadata': True,
    },
    'rating': {
        'default_rating': 0,  # 0 = unrated
    },
    'darktable': {
        'enabled': True,
        'executable': 'darktable',
        'auto_import': False,  # Whether to automatically import after culling
    },
    'keyboard': {
        'next_image': 'Space',
        'prev_image': 'Backspace',
        'rate_1': '1',
        'rate_2': '2',
        'rate_3': '3',
        'remove_rating': '0',
        'reject': 'X',
        'confirm': 'Return',
        'send_to_darktable': 'Ctrl+D',
        'backup': 'Ctrl+B',
    },
    'ui': {
        'theme': 'dark',
        'thumbnail_size': 200,
        'zoom_level': 1.0,
    }
}


class Config:
    """Configuration manager for ImCull"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager

        Args:
            config_path: Path to config file, defaults to XDG config directory/imcull/config.yaml
        """
        if config_path is None:
            self.config_dir = os.path.join(xdg.BaseDirectory.xdg_config_home, 'imcull')
            self.config_path = os.path.join(self.config_dir, 'config.yaml')
        else:
            self.config_path = config_path
            self.config_dir = os.path.dirname(config_path)

        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        # Load or create config
        self.config = self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from file or create default if not exists"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded configuration from {self.config_path}")

                    # Merge with defaults to ensure all keys exist
                    merged_config = DEFAULT_CONFIG.copy()
                    self._deep_update(merged_config, config)
                    return merged_config
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                logger.info("Using default configuration")
                return DEFAULT_CONFIG
        else:
            # Create default config
            self.save(DEFAULT_CONFIG)
            logger.info(f"Created default configuration at {self.config_path}")
            return DEFAULT_CONFIG

    def save(self, config: Dict[str, Any] = None) -> None:
        """Save configuration to file"""
        if config is None:
            config = self.config

        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get(self, key: str, default=None):
        """Get a configuration value"""
        # Support nested keys with dot notation (e.g., 'ui.theme')
        if '.' in key:
            parts = key.split('.')
            current = self.config
            for part in parts:
                if part not in current:
                    return default
                current = current[part]
            return current
        return self.config.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value"""
        # Support nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            current = self.config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self.config[key] = value

    def update(self, config: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        self._deep_update(self.config, config)

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration"""
        return self.config

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self.config = DEFAULT_CONFIG.copy()
        self.save()

    def _deep_update(self, target, source):
        """Recursively update a dict."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value


def _deep_update(target, source):
    """Recursively update a dict."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
