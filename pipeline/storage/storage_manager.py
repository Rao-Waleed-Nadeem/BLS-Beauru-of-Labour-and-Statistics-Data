"""
storage_manager.py — M18 Storage Manager

Pipeline Stage 8.

Persists validated UnifiedObjects and their ValidationReports to the
layered storage hierarchy defined in 03_STORAGE_SPECIFICATION.md.

Storage Layers (in pipeline order):
    raw/         ← Collectors write here (not this module)
    normalized/  ← written by save_normalized()
    validated/   ← written by save_validated()
    processed/   ← written by save_processed()
    metadata/    ← written alongside every save
    logs/        ← not managed here (Python logging handles logs)

Directory Structure (03_STORAGE_SPECIFICATION.md):
    storage/
    ├── normalized/bls/<dataset_id>/<year>/normalized.json
    ├── validated/bls/<dataset_id>/<year>/validated.json
    ├── processed/bls/<dataset_id>/dataset.json
    │                              dataset.csv
    │                              dataset.parquet   (optional)
    │                              metadata.json
    │                              validation.json
    │                              relationships.json
    └── metadata/bls/<dataset_id>/metadata.json

Rules (from spec):
    - Never modify raw files.
    - Write only validated data to the Processed layer.
    - Historical files must never be overwritten (append-or-skip).
    - Compute SHA256 for every stored file.
    - Generate metadata for every stored object.
    - CSV and Parquet generated only from validated JSON.
    - All timestamps in UTC.

This module does NOT:
    - Normalize objects  (M16 — UnifiedNormalizer)
    - Validate objects   (M17 — ValidationEngine)
    - Collect raw data   (Collector milestone)
"""

import csv
import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.parsers.models import UnifiedObject
from pipeline.validators.validation_result import ValidationReport, ValidationStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STORAGE_VERSION = "1.0"
_SOURCE_NAME = "bls"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of an on-disk file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, data: Any, *, overwrite: bool = False) -> bool:
    """
    Write *data* as pretty-printed JSON to *path*.

    Returns True on write, False if skipped (file exists and
    overwrite=False — immutability rule for historical files).
    """
    if path.exists() and not overwrite:
        logger.debug("Skip write (exists, immutable): %s", path)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    path.write_text(content, encoding="utf-8")
    return True


def _write_csv(path: Path, records: List[Dict[str, Any]], *, overwrite: bool = False) -> bool:
    """
    Write a list of flat dicts as CSV to *path*.

    Returns True on write, False if skipped.
    """
    if path.exists() and not overwrite:
        logger.debug("Skip CSV write (exists, immutable): %s", path)
        return False
    if not records:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return True


# ---------------------------------------------------------------------------
# StorageResult
# ---------------------------------------------------------------------------

class StorageResult:
    """
    Lightweight result object returned by every StorageManager write call.

    Attributes
    ----------
    success : bool
        True if all writes succeeded (or were skipped cleanly).
    skipped : bool
        True if the file was not written because it already existed
        (immutability rule).
    path : Path | None
        Primary file path written (or skipped).
    checksum : str
        SHA-256 of the written file, or empty if skipped.
    message : str
        Human-readable outcome.
    """

    def __init__(
        self,
        success: bool,
        path: Optional[Path] = None,
        skipped: bool = False,
        checksum: str = "",
        message: str = "",
    ) -> None:
        self.success = success
        self.path = path
        self.skipped = skipped
        self.checksum = checksum
        self.message = message

    def __repr__(self) -> str:
        status = "SKIPPED" if self.skipped else ("OK" if self.success else "ERROR")
        return f"StorageResult({status}, path={self.path})"


# ---------------------------------------------------------------------------
# StorageManager
# ---------------------------------------------------------------------------

class StorageManager:
    """
    M18 Storage Manager — Pipeline Stage 8.

    Manages all write operations for the normalized → validated →
    processed pipeline layers.

    Parameters
    ----------
    storage_root : Path | str
        Absolute path to the ``storage/`` root directory.
        Must exist or be creatable.

    Usage::

        sm = StorageManager(Path("storage"))

        # After normalization
        result = sm.save_normalized(obj, dataset_id="cpi", year="2026")

        # After validation
        result = sm.save_validated(obj, report, dataset_id="cpi", year="2026")

        # Build processed dataset from validated records
        result = sm.save_processed(objects, dataset_id="cpi")
    """

    def __init__(self, storage_root: Path | str) -> None:
        self.root = Path(storage_root).resolve()
        self._ensure_structure()

    # ------------------------------------------------------------------
    # Directory layout helpers
    # ------------------------------------------------------------------

    def _ensure_structure(self) -> None:
        """Create the canonical layer directories if absent."""
        for layer in ("raw", "normalized", "validated", "processed",
                      "features", "metadata", "logs", "backups"):
            (self.root / layer / _SOURCE_NAME).mkdir(parents=True, exist_ok=True)

    def _normalized_dir(self, dataset_id: str, year: str) -> Path:
        return self.root / "normalized" / _SOURCE_NAME / dataset_id / year

    def _validated_dir(self, dataset_id: str, year: str) -> Path:
        return self.root / "validated" / _SOURCE_NAME / dataset_id / year

    def _processed_dir(self, dataset_id: str) -> Path:
        return self.root / "processed" / _SOURCE_NAME / dataset_id

    def _features_dir(self, dataset_id: str) -> Path:
        return self.root / "features" / _SOURCE_NAME / dataset_id

    def _metadata_dir(self, dataset_id: str) -> Path:
        return self.root / "metadata" / _SOURCE_NAME / dataset_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_normalized(
        self,
        obj: UnifiedObject,
        dataset_id: str,
        year: str,
    ) -> StorageResult:
        """
        Write a normalized ``UnifiedObject`` to the normalized layer.

        Path: ``normalized/bls/<dataset_id>/<year>/normalized.json``

        Historical files are **never overwritten** (immutability rule).

        Parameters
        ----------
        obj : UnifiedObject
            A normalized object (output of UnifiedNormalizer).
        dataset_id : str
            Dataset identifier (e.g. ``"cpi"``).
        year : str
            Reference year (e.g. ``"2026"``).

        Returns
        -------
        StorageResult
        """
        dest = self._normalized_dir(dataset_id, year) / "normalized.json"
        data = self._obj_to_dict(obj)
        written = _write_json(dest, data, overwrite=False)

        if not written:
            return StorageResult(
                success=True,
                path=dest,
                skipped=True,
                message="Normalized file already exists — skipped (immutability).",
            )

        checksum = _sha256_file(dest)
        self._write_file_metadata(dest, obj, dataset_id)
        logger.info("Saved normalized: %s (sha256=%s…)", dest, checksum[:8])
        return StorageResult(success=True, path=dest, checksum=checksum)

    def save_normalized_batch(
        self,
        objects: List[UnifiedObject],
        dataset_id: str,
        year: str,
    ) -> StorageResult:
        """
        Write a batch of normalized objects as a JSON array.

        Path: ``normalized/bls/<dataset_id>/<year>/normalized.json``

        If the file already exists it is **skipped** (immutability).

        Parameters
        ----------
        objects : list[UnifiedObject]
        dataset_id : str
        year : str

        Returns
        -------
        StorageResult
        """
        dest = self._normalized_dir(dataset_id, year) / "normalized.json"
        data = [self._obj_to_dict(o) for o in objects]
        written = _write_json(dest, data, overwrite=False)

        if not written:
            return StorageResult(
                success=True,
                path=dest,
                skipped=True,
                message="Normalized batch file already exists — skipped.",
            )

        checksum = _sha256_file(dest)
        logger.info(
            "Saved normalized batch (%d objects): %s (sha256=%s…)",
            len(objects), dest, checksum[:8],
        )
        return StorageResult(success=True, path=dest, checksum=checksum)

    def save_validated(
        self,
        obj: UnifiedObject,
        report: ValidationReport,
        dataset_id: str,
        year: str,
    ) -> StorageResult:
        """
        Write a validated ``UnifiedObject`` + its ``ValidationReport``
        to the validated layer.

        Only objects whose report has ``overall_status == PASS`` are
        accepted.  Objects with FAIL status are rejected.

        Paths:
            ``validated/bls/<dataset_id>/<year>/validated.json``
            ``validated/bls/<dataset_id>/<year>/validation.json``

        Parameters
        ----------
        obj : UnifiedObject
        report : ValidationReport
        dataset_id : str
        year : str

        Returns
        -------
        StorageResult
            ``success=False`` if the report indicates a FAIL.
        """
        if report.overall_status == ValidationStatus.FAIL:
            msg = (
                f"Rejected — validation FAIL for uuid={report.uuid}: "
                f"{[c.message for c in report.failures]}"
            )
            logger.warning(msg)
            return StorageResult(success=False, message=msg)

        dest_obj = self._validated_dir(dataset_id, year) / "validated.json"
        dest_rep = self._validated_dir(dataset_id, year) / "validation.json"

        data = self._obj_to_dict(obj)
        written = _write_json(dest_obj, data, overwrite=False)

        if not written:
            return StorageResult(
                success=True,
                path=dest_obj,
                skipped=True,
                message="Validated file already exists — skipped.",
            )

        # Write the validation report alongside
        _write_json(dest_rep, report.to_dict(), overwrite=True)

        checksum = _sha256_file(dest_obj)
        self._write_file_metadata(dest_obj, obj, dataset_id)
        logger.info("Saved validated: %s (sha256=%s…)", dest_obj, checksum[:8])
        return StorageResult(success=True, path=dest_obj, checksum=checksum)

    def save_validated_batch(
        self,
        objects: List[UnifiedObject],
        reports: List[ValidationReport],
        dataset_id: str,
        year: str,
    ) -> StorageResult:
        """
        Write a batch of validated objects as a JSON array.

        Objects whose corresponding report has ``status == FAIL`` are
        filtered out before writing.  If all objects fail validation the
        write is rejected entirely.

        Paths:
            ``validated/bls/<dataset_id>/<year>/validated.json``
            ``validated/bls/<dataset_id>/<year>/validation.json``

        Parameters
        ----------
        objects : list[UnifiedObject]
        reports : list[ValidationReport]
            Parallel list — ``reports[i]`` corresponds to ``objects[i]``.
        dataset_id : str
        year : str

        Returns
        -------
        StorageResult
        """
        if len(objects) != len(reports):
            raise ValueError(
                f"objects ({len(objects)}) and reports ({len(reports)}) "
                "must have the same length."
            )

        # Filter to PASS-only
        passed_pairs = [
            (obj, rep)
            for obj, rep in zip(objects, reports)
            if rep.overall_status != ValidationStatus.FAIL
        ]

        if not passed_pairs:
            msg = f"All {len(objects)} object(s) failed validation — nothing written."
            logger.warning(msg)
            return StorageResult(success=False, message=msg)

        passed_objs, passed_reps = zip(*passed_pairs)
        dest_obj = self._validated_dir(dataset_id, year) / "validated.json"
        dest_rep = self._validated_dir(dataset_id, year) / "validation.json"

        data = [self._obj_to_dict(o) for o in passed_objs]
        written = _write_json(dest_obj, data, overwrite=False)

        if not written:
            return StorageResult(
                success=True,
                path=dest_obj,
                skipped=True,
                message="Validated batch already exists — skipped.",
            )

        rep_data = [r.to_dict() for r in passed_reps]
        _write_json(dest_rep, rep_data, overwrite=True)

        checksum = _sha256_file(dest_obj)
        logger.info(
            "Saved validated batch (%d/%d objects): %s (sha256=%s…)",
            len(passed_objs), len(objects), dest_obj, checksum[:8],
        )
        return StorageResult(success=True, path=dest_obj, checksum=checksum)

    def save_processed(
        self,
        objects: List[UnifiedObject],
        dataset_id: str,
        *,
        write_csv: bool = True,
        overwrite: bool = False,
    ) -> StorageResult:
        """
        Write the final processed dataset from a list of validated objects.

        Outputs (per 03_STORAGE_SPECIFICATION.md):
            ``processed/bls/<dataset_id>/dataset.json``
            ``processed/bls/<dataset_id>/dataset.csv``      (if write_csv=True)
            ``processed/bls/<dataset_id>/metadata.json``
            ``processed/bls/<dataset_id>/relationships.json``

        Parameters
        ----------
        objects : list[UnifiedObject]
            Validated, normalized objects for this dataset.
        dataset_id : str
        write_csv : bool, default True
            Also write a flat CSV from the API sub-schema.
        overwrite : bool, default False
            When True, overwrite existing processed files.
            Set to True for incremental update runs only.

        Returns
        -------
        StorageResult
            ``path`` points to ``dataset.json``.
        """
        if not objects:
            return StorageResult(success=False, message="No objects to process.")

        dest_dir = self._processed_dir(dataset_id)
        dest_json = dest_dir / "dataset.json"

        data = [self._obj_to_dict(o) for o in objects]
        written = _write_json(dest_json, data, overwrite=overwrite)

        if not written:
            return StorageResult(
                success=True,
                path=dest_json,
                skipped=True,
                message="Processed dataset already exists — skipped.",
            )

        # Write CSV from API sub-schema (flat records)
        if write_csv:
            csv_path = dest_dir / "dataset.csv"
            flat_records = [self._api_to_flat(o) for o in objects if o.api is not None]
            if flat_records:
                _write_csv(csv_path, flat_records, overwrite=overwrite)

        # Write metadata.json
        meta_path = dest_dir / "metadata.json"
        _write_json(meta_path, self._build_dataset_metadata(objects, dataset_id), overwrite=True)

        # Write relationships.json
        rel_path = dest_dir / "relationships.json"
        _write_json(rel_path, self._build_relationships(objects), overwrite=True)

        checksum = _sha256_file(dest_json)
        logger.info(
            "Saved processed dataset '%s' (%d records): %s (sha256=%s…)",
            dataset_id, len(objects), dest_json, checksum[:8],
        )
        return StorageResult(success=True, path=dest_json, checksum=checksum)

    def save_features(
        self,
        features: List[Dict[str, Any]],
        dataset_id: str,
        *,
        write_csv: bool = True,
        overwrite: bool = False,
    ) -> StorageResult:
        """
        Write the final engineered feature set.

        Outputs (per 03_STORAGE_SPECIFICATION.md equivalent):
            ``features/bls/<dataset_id>/feature_set.json``
            ``features/bls/<dataset_id>/feature_set.csv``      (if write_csv=True)

        Parameters
        ----------
        features : list[dict]
            Calculated feature dictionaries.
        dataset_id : str
        write_csv : bool, default True
            Also write a flat CSV.
        overwrite : bool, default False
            When True, overwrite existing feature files.

        Returns
        -------
        StorageResult
            ``path`` points to ``feature_set.json``.
        """
        if not features:
            return StorageResult(success=False, message="No features to save.")

        dest_dir = self._features_dir(dataset_id)
        dest_json = dest_dir / "feature_set.json"

        written = _write_json(dest_json, features, overwrite=overwrite)

        if not written:
            return StorageResult(
                success=True,
                path=dest_json,
                skipped=True,
                message="Feature set already exists — skipped.",
            )

        if write_csv:
            csv_path = dest_dir / "feature_set.csv"
            _write_csv(csv_path, features, overwrite=overwrite)

        # Write metadata.json
        meta_path = dest_dir / "metadata.json"
        meta_data = {
            "dataset_id": dataset_id,
            "record_count": len(features),
            "generated_at": _utc_now(),
            "schema_version": _STORAGE_VERSION,
            "source": _SOURCE_NAME,
        }
        _write_json(meta_path, meta_data, overwrite=True)

        checksum = _sha256_file(dest_json)
        logger.info(
            "Saved feature set '%s' (%d records): %s (sha256=%s…)",
            dataset_id, len(features), dest_json, checksum[:8],
        )
        return StorageResult(success=True, path=dest_json, checksum=checksum)

    def path_exists(self, layer: str, dataset_id: str, year: str = "") -> bool:
        """
        Check whether a canonical path for *layer* already exists.

        Parameters
        ----------
        layer : str
            One of ``"normalized"``, ``"validated"``, ``"processed"``.
        dataset_id : str
        year : str
            Required for normalized/validated layers.

        Returns
        -------
        bool
        """
        if layer == "normalized":
            return (self._normalized_dir(dataset_id, year) / "normalized.json").exists()
        if layer == "validated":
            return (self._validated_dir(dataset_id, year) / "validated.json").exists()
        if layer == "processed":
            return (self._processed_dir(dataset_id) / "dataset.json").exists()
        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _obj_to_dict(obj: UnifiedObject) -> Dict[str, Any]:
        """Serialise a UnifiedObject to a plain dict."""
        return asdict(obj)

    @staticmethod
    def _api_to_flat(obj: UnifiedObject) -> Dict[str, Any]:
        """Flatten an object's API sub-schema + key metadata into one dict."""
        api = obj.api
        meta = obj.metadata
        return {
            "uuid": meta.uuid,
            "series_id": api.series_id,
            "series_title": api.series_title,
            "frequency": api.frequency,
            "year": api.year,
            "period": api.period,
            "period_name": api.period_name,
            "value": api.value,
            "latest": api.latest,
            "footnotes": "; ".join(api.footnotes),
            "source_type": meta.source_type,
            "collection_timestamp": meta.collection_timestamp,
            "normalization_timestamp": meta.normalization_timestamp,
            "checksum": meta.checksum,
        }

    @staticmethod
    def _build_dataset_metadata(objects: List[UnifiedObject], dataset_id: str) -> Dict[str, Any]:
        """Build the metadata.json payload for a processed dataset."""
        uuids = [o.metadata.uuid for o in objects if o.metadata]
        return {
            "dataset_id": dataset_id,
            "record_count": len(objects),
            "uuids": uuids,
            "generated_at": _utc_now(),
            "schema_version": _STORAGE_VERSION,
            "source": _SOURCE_NAME,
        }

    @staticmethod
    def _build_relationships(objects: List[UnifiedObject]) -> List[Dict[str, Any]]:
        """Build the relationships.json payload (series → dataset links)."""
        seen: set = set()
        rels: List[Dict[str, Any]] = []
        for obj in objects:
            if obj.metadata and obj.metadata.series_id:
                key = (obj.metadata.program_id, obj.metadata.dataset_id, obj.metadata.series_id)
                if key not in seen:
                    seen.add(key)
                    rels.append({
                        "program_id": obj.metadata.program_id,
                        "dataset_id": obj.metadata.dataset_id,
                        "series_id": obj.metadata.series_id,
                    })
        return rels

    def _write_file_metadata(
        self,
        stored_path: Path,
        obj: UnifiedObject,
        dataset_id: str,
    ) -> None:
        """Write a metadata sidecar for a single stored file."""
        meta_dir = self._metadata_dir(dataset_id)
        # Use the stored file's stem as the metadata filename
        meta_file = meta_dir / f"{stored_path.stem}_metadata.json"
        checksum = _sha256_file(stored_path)
        data = {
            "uuid": obj.metadata.uuid if obj.metadata else "",
            "dataset_id": dataset_id,
            "program_id": obj.metadata.program_id if obj.metadata else "",
            "collector": obj.metadata.collector if obj.metadata else "",
            "source_url": "",
            "download_timestamp": obj.metadata.collection_timestamp if obj.metadata else "",
            "checksum": checksum,
            "schema_version": _STORAGE_VERSION,
            "stored_path": str(stored_path),
            "generated_at": _utc_now(),
        }
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
