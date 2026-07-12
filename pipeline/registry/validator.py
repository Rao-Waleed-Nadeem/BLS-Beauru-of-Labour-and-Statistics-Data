import re
from typing import Pattern

from pipeline.registry.cache import RegistryCache
from pipeline.registry.models import (
    DatasetRegistryEntry,
    ProgramRegistryEntry,
    UrlRegistryEntry,
)


class RegistryValidator:
    """Validates registry entries and cross-registry relationships."""

    URL_ID_PATTERN: Pattern[str] = re.compile(r"^BLS-URL-\d{3}$")
    PROGRAM_ID_PATTERN: Pattern[str] = re.compile(r"^BLS-PROGRAM-\d{3}$")
    DATASET_ID_PATTERN: Pattern[str] = re.compile(r"^BLS-DATASET-\d{3}$")

    VALID_URL_CATEGORIES = {
        "ROOT",
        "HUB",
        "PROGRAM",
        "RELEASE",
        "CALENDAR",
        "ARCHIVE",
        "API",
        "RSS",
        "PDF",
        "DATA",
        "DOC",
        "SUPPORT",
    }
    VALID_PRIORITIES = {"Critical", "High", "Medium", "Low"}

    def validate_url(self, entry: UrlRegistryEntry) -> None:
        if not entry.id or not entry.url:
            raise ValueError(f"URL entry missing ID or URL: {entry}")

        if not self.URL_ID_PATTERN.match(entry.id):
            raise ValueError(f"Invalid URL ID format: {entry.id}")

        if not entry.url.startswith(("http://", "https://")):
            raise ValueError(f"URL entry has invalid URL: {entry.id} -> {entry.url}")

        if entry.category and entry.category not in self.VALID_URL_CATEGORIES:
            raise ValueError(f"URL entry has unknown category: {entry.id} -> {entry.category}")

        if entry.priority and entry.priority not in self.VALID_PRIORITIES:
            raise ValueError(f"URL entry has unknown priority: {entry.id} -> {entry.priority}")

    def validate_program(self, entry: ProgramRegistryEntry) -> None:
        if not entry.program_id:
            raise ValueError(f"Program entry missing ID: {entry.name}")

        if not self.PROGRAM_ID_PATTERN.match(entry.program_id):
            raise ValueError(f"Invalid Program ID format: {entry.program_id}")

        if not entry.base_url:
            raise ValueError(f"Program entry missing Base URL: {entry.program_id}")

        if not entry.base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Program entry has invalid Base URL: {entry.program_id} -> {entry.base_url}"
            )

    def validate_dataset(self, entry: DatasetRegistryEntry) -> None:
        if not entry.dataset_id or not entry.program_id:
            raise ValueError(
                f"Dataset entry missing Dataset ID or Program ID: {entry.dataset_name}"
            )

        if not self.DATASET_ID_PATTERN.match(entry.dataset_id):
            raise ValueError(f"Invalid Dataset ID format: {entry.dataset_id}")

        if not self.PROGRAM_ID_PATTERN.match(entry.program_id):
            raise ValueError(
                f"Dataset references invalid Program ID format: "
                f"{entry.dataset_id} -> {entry.program_id}"
            )

        if not entry.dataset_name:
            raise ValueError(f"Dataset entry missing name: {entry.dataset_id}")

    def validate_relationships(self, cache: RegistryCache) -> None:
        for dataset_id, dataset in cache.datasets.items():
            if dataset.program_id not in cache.programs:
                raise ValueError(
                    f"Dataset {dataset_id} references unknown Program ID: "
                    f"{dataset.program_id}"
                )
