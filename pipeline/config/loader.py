import yaml
from pathlib import Path
from typing import Dict, Any

from pipeline.utils.base_utils import get_project_root

class ConfigLoader:
    """
    Loads YAML configuration files from the config directory.
    No values are hardcoded; everything is read from configuration files.
    """
    def __init__(self, config_dir: str = None):
        self.root = get_project_root()
        self.config_dir = Path(config_dir) if config_dir else self.root / 'config'
        
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file {filepath} not found.")
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def load_settings(self) -> Dict[str, Any]:
        return self._load_yaml('settings.yaml')

    def load_pipeline(self) -> Dict[str, Any]:
        return self._load_yaml('pipeline.yaml')

    def load_storage(self) -> Dict[str, Any]:
        return self._load_yaml('storage.yaml')

    def load_scheduler(self) -> Dict[str, Any]:
        return self._load_yaml('scheduler.yaml')

    def load_logging(self) -> Dict[str, Any]:
        return self._load_yaml('logging.yaml')

    def load_all(self) -> Dict[str, Any]:
        return {
            'settings': self.load_settings(),
            'pipeline': self.load_pipeline(),
            'storage': self.load_storage(),
            'scheduler': self.load_scheduler(),
            'logging': self.load_logging()
        }
