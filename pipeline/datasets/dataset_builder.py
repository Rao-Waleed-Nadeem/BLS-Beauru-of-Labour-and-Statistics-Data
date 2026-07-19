"""pipeline.datasets.dataset_builder — M19 Dataset Builder

M19 merges validated UnifiedObjects into final per-dataset processed
artifacts.

This module is intentionally small and deterministic:
- It never mutates stored raw/validated files.
- It only uses already-validated UnifiedObjects passed in by the caller.
- It groups objects by dataset_id derived from obj.metadata.dataset_id.
- It sorts chronologically (year asc, then period asc via period name).
- It merges by primary key (series_id + year + period for API objects).

Persistence is delegated to StorageManager.save_processed().
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pipeline.parsers.models import APISchema, MetadataSchema, UnifiedObject
from pipeline.storage import StorageManager


class DatasetBuilder:
    """M19 Dataset Builder."""

    def __init__(self, storage: Optional[StorageManager] = None) -> None:
        # StorageManager handles Processed-layer paths + immutability.
        self.storage = storage or StorageManager("storage")

    @staticmethod
    def _dataset_id(obj: UnifiedObject) -> str:
        if not obj.metadata or not obj.metadata.dataset_id:
            raise ValueError("UnifiedObject.metadata.dataset_id is required")
        return obj.metadata.dataset_id

    @staticmethod
    def _period_sort_key(period: str) -> str:
        """Provide a deterministic secondary ordering.

        BLS periods in this project are like:
          - M01..M13
          - Q01..Q05
          - S01..S02
          - A01

        Sorting lexicographically after removing the leading letter prefix
        works as numeric-like strings because they are zero-padded.
        """
        if not period:
            return ""
        # Example: M06 -> ("M", "06")
        prefix = period[0]
        suffix = period[1:]
        return f"{prefix}:{suffix}"

    @classmethod
    def _chrono_key(cls, obj: UnifiedObject) -> Tuple[int, str]:
        """Sort by year, then period."""
        year = int(obj.api.year) if obj.api and obj.api.year else -1
        period = obj.api.period if obj.api else ""
        return (year, cls._period_sort_key(period))

    @staticmethod
    def _primary_key(obj: UnifiedObject) -> str:
        """Primary key for dedupe.

        The dataset specs define uniqueness using registered primary keys.
        For the current codebase, validators enforce API uniqueness using:
          series_id + year + period
        """
        if not obj.metadata:
            raise ValueError("UnifiedObject.metadata is required")
        if not obj.api:
            # Non-API sources aren't fully specified in current code.
            # Still provide a deterministic key.
            return f"metadata::{obj.metadata.uuid}"
        return f"api::{obj.metadata.series_id}::{obj.api.year}::{obj.api.period}"

    @classmethod
    def group_by_dataset(cls, objects: Iterable[UnifiedObject]) -> Dict[str, List[UnifiedObject]]:
        grouped: Dict[str, List[UnifiedObject]] = {}
        for obj in objects:
            dsid = cls._dataset_id(obj)
            grouped.setdefault(dsid, []).append(obj)
        return grouped

    @classmethod
    def merge_dedupe_sort(cls, objects: List[UnifiedObject]) -> List[UnifiedObject]:
        """Dedupe by primary key, then sort chronologically."""
        by_pk: Dict[str, UnifiedObject] = {}
        for o in objects:
            pk = cls._primary_key(o)
            # Deterministic: keep the first occurrence.
            if pk not in by_pk:
                by_pk[pk] = o
        merged = list(by_pk.values())
        merged.sort(key=cls._chrono_key)
        return merged

    def build_processed_from_validated(
        self,
        validated_objects: Iterable[UnifiedObject],
        *,
        write_csv: bool = True,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Build processed datasets and persist them.

        Returns a small summary dict keyed by dataset_id.
        """
        grouped = self.group_by_dataset(validated_objects)
        results: Dict[str, Any] = {}

        for dataset_id, objs in grouped.items():
            merged_sorted = self.merge_dedupe_sort(objs)

            storage_result = self.storage.save_processed(
                merged_sorted,
                dataset_id,
                write_csv=write_csv,
                overwrite=overwrite,
            )

            results[dataset_id] = {
                "record_count": len(merged_sorted),
                "storage": {
                    "success": storage_result.success,
                    "skipped": storage_result.skipped,
                    "path": str(storage_result.path) if storage_result.path else None,
                    "checksum": storage_result.checksum,
                    "message": storage_result.message,
                },
            }

        return results

