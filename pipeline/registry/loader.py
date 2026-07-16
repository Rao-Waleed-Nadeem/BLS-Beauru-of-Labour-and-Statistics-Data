from pathlib import Path
from typing import Optional

from BLS.pipeline.registry.cache import RegistryCache
from BLS.pipeline.registry.parser import RegistryParser
from BLS.pipeline.registry.validator import RegistryValidator
from BLS.pipeline.utils.base_utils import get_project_root


class RegistryLoader:
    """Loads, validates, and caches BLS registry markdown files."""

    DEFAULT_DOCS_DIR = (
        "Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery"
    )
    REQUIRED_FILES = (
        "URL_REGISTRY.md",
        "PROGRAM_REGISTRY.md",
        "DATASET_REGISTRY.md",
    )

    def __init__(self, docs_dir: Optional[str] = None) -> None:
        self.root = get_project_root()
        self.docs_dir = (
            Path(docs_dir)
            if docs_dir
            else self.root / "Docs" / "BLS" / "02_Website_Architecture_and_URL_Inventory" / "Registery"
        )
        self.parser = RegistryParser()
        self.validator = RegistryValidator()
        self.cache = RegistryCache()
        self._loaded = False

    def _read_file(self, filename: str) -> str:
        filepath = self.docs_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Registry file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()

    def load(self) -> RegistryCache:
        if self._loaded:
            return self.cache

        for filename in self.REQUIRED_FILES:
            content = self._read_file(filename)

            if filename == "URL_REGISTRY.md":
                for entry in self.parser.parse_urls(content):
                    self.validator.validate_url(entry)
                    self.cache.add_url(entry)
            elif filename == "PROGRAM_REGISTRY.md":
                for entry in self.parser.parse_programs(content):
                    self.validator.validate_program(entry)
                    self.cache.add_program(entry)
            elif filename == "DATASET_REGISTRY.md":
                for entry in self.parser.parse_datasets(content):
                    self.validator.validate_dataset(entry)
                    self.cache.add_dataset(entry)

        self.validator.validate_relationships(self.cache)
        self._loaded = True
        return self.cache

    def reload(self) -> RegistryCache:
        self._loaded = False
        self.cache.clear()
        return self.load()

    def get_cache(self) -> RegistryCache:
        if not self._loaded:
            return self.load()
        return self.cache
