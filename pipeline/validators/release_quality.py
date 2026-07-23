"""End-to-end release quality checks for M23.

These helpers produce the duplicate and missing-release reports required by
the validation and maintenance guide. They operate on already parsed or
processed ``UnifiedObject`` instances and do not perform collection, parsing,
normalization, or storage-layer writes beyond optional report output.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pipeline.parsers.models import UnifiedObject


@dataclass(frozen=True)
class ReleaseKey:
    """Canonical API release identity: series_id + year + period."""

    series_id: str
    year: str
    period: str

    @classmethod
    def from_mapping(cls, data: Dict[str, Any]) -> "ReleaseKey":
        return cls(
            series_id=str(data.get("series_id", "")),
            year=str(data.get("year", "")),
            period=str(data.get("period", "")),
        )

    @classmethod
    def from_object(cls, obj: UnifiedObject) -> Optional["ReleaseKey"]:
        if obj.api is None:
            return None
        return cls(
            series_id=obj.api.series_id,
            year=obj.api.year,
            period=obj.api.period,
        )

    def to_token(self) -> str:
        return f"{self.series_id}::{self.year}::{self.period}"


def _coerce_release_key(value: ReleaseKey | Dict[str, Any] | Tuple[str, str, str]) -> ReleaseKey:
    if isinstance(value, ReleaseKey):
        return value
    if isinstance(value, dict):
        return ReleaseKey.from_mapping(value)
    series_id, year, period = value
    return ReleaseKey(str(series_id), str(year), str(period))


def detect_duplicate_records(objects: Iterable[UnifiedObject]) -> Dict[str, Any]:
    """Detect duplicate API primary keys and duplicate checksums."""

    seen_primary_keys: Dict[str, str] = {}
    seen_checksums: Dict[str, str] = {}
    duplicates: List[Dict[str, str]] = []

    for obj in objects:
        uuid = obj.metadata.uuid if obj.metadata else ""
        key = ReleaseKey.from_object(obj)
        if key is not None:
            token = key.to_token()
            if token in seen_primary_keys:
                duplicates.append(
                    {
                        "level": "primary_key",
                        "key": token,
                        "first_uuid": seen_primary_keys[token],
                        "duplicate_uuid": uuid,
                    }
                )
            else:
                seen_primary_keys[token] = uuid

        checksum = obj.metadata.checksum if obj.metadata else ""
        if checksum:
            token = f"checksum::{checksum}"
            if token in seen_checksums:
                duplicates.append(
                    {
                        "level": "checksum",
                        "key": token,
                        "first_uuid": seen_checksums[token],
                        "duplicate_uuid": uuid,
                    }
                )
            else:
                seen_checksums[token] = uuid

    return {
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
    }


def detect_missing_releases(
    expected_releases: Iterable[ReleaseKey | Dict[str, Any] | Tuple[str, str, str]],
    collected_objects: Iterable[UnifiedObject],
) -> Dict[str, Any]:
    """Compare expected release keys against collected API objects."""

    expected = [_coerce_release_key(item) for item in expected_releases]
    collected = {
        key.to_token()
        for key in (ReleaseKey.from_object(obj) for obj in collected_objects)
        if key is not None
    }
    missing = [key for key in expected if key.to_token() not in collected]

    return {
        "expected_count": len(expected),
        "collected_count": len(collected),
        "missing_count": len(missing),
        "missing_releases": [asdict(key) for key in missing],
    }


def write_release_quality_reports(
    *,
    expected_releases: Iterable[ReleaseKey | Dict[str, Any] | Tuple[str, str, str]],
    collected_objects: Iterable[UnifiedObject],
    output_dir: Path | str,
) -> Dict[str, Path]:
    """Write duplicate, completeness, and missing-release quality reports."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    objects = list(collected_objects)
    duplicate_report = detect_duplicate_records(objects)
    missing_report = detect_missing_releases(expected_releases, objects)
    completeness_report = {
        "expected_count": missing_report["expected_count"],
        "collected_count": missing_report["collected_count"],
        "missing_count": missing_report["missing_count"],
        "complete": missing_report["missing_count"] == 0,
    }

    reports = {
        "duplicate_report.json": duplicate_report,
        "missing_releases.json": missing_report,
        "completeness_report.json": completeness_report,
    }

    written: Dict[str, Path] = {}
    for filename, payload in reports.items():
        path = output / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written[filename] = path

    return written
