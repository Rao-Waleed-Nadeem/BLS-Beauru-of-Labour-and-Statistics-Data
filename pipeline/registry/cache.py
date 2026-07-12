from typing import Dict, Optional

from pipeline.registry.models import (
    DatasetRegistryEntry,
    ProgramRegistryEntry,
    UrlRegistryEntry,
)


class RegistryCache:
    """In-memory cache for all loaded registries."""

    def __init__(self) -> None:
        self.urls: Dict[str, UrlRegistryEntry] = {}
        self.programs: Dict[str, ProgramRegistryEntry] = {}
        self.datasets: Dict[str, DatasetRegistryEntry] = {}

    def add_url(self, entry: UrlRegistryEntry) -> None:
        if entry.id in self.urls:
            raise ValueError(f"Duplicate URL ID: {entry.id}")
        self.urls[entry.id] = entry

    def add_program(self, entry: ProgramRegistryEntry) -> None:
        if entry.program_id in self.programs:
            raise ValueError(f"Duplicate Program ID: {entry.program_id}")
        self.programs[entry.program_id] = entry

    def add_dataset(self, entry: DatasetRegistryEntry) -> None:
        if entry.dataset_id in self.datasets:
            raise ValueError(f"Duplicate Dataset ID: {entry.dataset_id}")
        self.datasets[entry.dataset_id] = entry

    def get_url(self, url_id: str) -> Optional[UrlRegistryEntry]:
        return self.urls.get(url_id)

    def get_program(self, program_id: str) -> Optional[ProgramRegistryEntry]:
        return self.programs.get(program_id)

    def get_dataset(self, dataset_id: str) -> Optional[DatasetRegistryEntry]:
        return self.datasets.get(dataset_id)

    def clear(self) -> None:
        self.urls.clear()
        self.programs.clear()
        self.datasets.clear()
