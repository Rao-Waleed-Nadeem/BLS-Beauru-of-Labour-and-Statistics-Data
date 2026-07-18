"""
validation_engine.py — M17 Validation Engine

Pipeline Stage 7.

Receives a normalized UnifiedObject (from M16 UnifiedNormalizer) and
runs all required validation checks defined in:

  - 05_Validation_And_Maintenance.md
  - 01_UNIFIED_SCHEMA.md
  - 02_DATASET_SPECIFICATIONS.md

Validation Workflow (from 05_Validation_And_Maintenance.md):

    Schema Validation
    ↓
    Required Field Validation
    ↓
    Data Type Validation
    ↓
    Relationship Validation
    ↓
    Duplicate Detection
    ↓
    Timestamp Verification
    ↓
    Checksum Verification

Each step is a dedicated private method returning a CheckResult.
Failure at any step is recorded but all steps are always executed so
the caller receives a complete report.

This module does NOT:
  - Persist anything (Storage responsibility — M18)
  - Normalize objects (Normalizer responsibility — M16)
  - Download data (Collector responsibility)

Duplicate detection is stateless by default: the caller supplies an
optional ``seen_keys`` set to enable cross-object deduplication.

Rules (from 05_Validation_And_Maintenance.md):
  - Reject invalid objects before storage.
  - Detect duplicates before persistence.
  - Verify every timestamp.
  - Never bypass validation.
  - Automatic type conversion is prohibited.
"""

import hashlib
import json
import logging
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Set

from pipeline.parsers.models import (
    APISchema,
    MetadataSchema,
    UnifiedObject,
)
from pipeline.validators.validation_result import (
    CheckResult,
    ValidationReport,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SOURCE_TYPES: frozenset = frozenset({"API", "HTML", "PDF", "RSS", "ARCHIVE"})
VALID_VALIDATION_STATUSES: frozenset = frozenset({"PASS", "FAIL"})

# ISO-8601 UTC timestamp pattern: YYYY-MM-DDTHH:MM:SSZ
_ISO8601_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)

# BLS period formats:  M01–M13 (monthly) or Q01–Q05 (quarterly) or S01–S02
_PERIOD_RE = re.compile(r"^(M(0[1-9]|1[0-3])|Q0[1-5]|S0[12]|A01)$")

# Year must be a 4-digit string
_YEAR_RE = re.compile(r"^\d{4}$")

# SHA-256 hex digest — exactly 64 lowercase hex chars
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# ValidationEngine
# ---------------------------------------------------------------------------

class ValidationEngine:
    """
    M17 Validation Engine — Pipeline Stage 7.

    Validates a normalized ``UnifiedObject`` against the complete
    validation workflow defined in ``05_Validation_And_Maintenance.md``.

    Usage::

        engine = ValidationEngine()

        # Single object
        report = engine.validate(obj)
        if report.failed:
            for check in report.failures:
                print(check.check_name, check.message)

        # Batch with cross-object duplicate detection
        seen: set = set()
        reports = engine.validate_all(objects, seen_keys=seen)

    Parameters
    ----------
    strict : bool, default True
        When ``True`` (default), a WARN-level finding is escalated to
        FAIL for the overall status.  Set to ``False`` to allow objects
        with warnings to be accepted downstream.
    """

    def __init__(self, strict: bool = True) -> None:
        self.strict = strict

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        obj: UnifiedObject,
        seen_keys: Optional[Set[str]] = None,
    ) -> ValidationReport:
        """
        Run all validation checks on *obj* and return a
        :class:`ValidationReport`.

        Parameters
        ----------
        obj : UnifiedObject
            A normalized object (must have passed through
            ``UnifiedNormalizer.normalize()``).
        seen_keys : set[str] | None
            Optional shared set for cross-object duplicate detection.
            Pass the *same* set across multiple calls to detect
            duplicates within a batch.  The set is updated in-place
            with the primary key of each VALID object.

        Returns
        -------
        ValidationReport
            Always returned — never raises.  Inspect
            ``report.failed`` or ``report.overall_status``.
        """
        if not isinstance(obj, UnifiedObject) or obj is None:
            return ValidationReport(
                uuid="",
                series_id="",
                source_type="",
                checks=[
                    CheckResult(
                        "schema_validation",
                        ValidationStatus.FAIL,
                        f"Expected UnifiedObject, got {type(obj).__name__}.",
                    )
                ],
            )

        if obj.metadata is None:
            return ValidationReport(
                uuid="",
                series_id="",
                source_type="",
                checks=[
                    CheckResult(
                        "schema_validation",
                        ValidationStatus.FAIL,
                        "UnifiedObject or its metadata is None.",
                    )
                ],
            )

        meta = obj.metadata
        report = ValidationReport(
            uuid=meta.uuid,
            series_id=meta.series_id or "",
            source_type=meta.source_type or "",
        )

        # Execute each check in the documented order
        report.checks.append(self._check_schema_validation(obj))
        report.checks.append(self._check_required_fields(obj))
        report.checks.append(self._check_data_types(obj))
        report.checks.append(self._check_relationships(obj))
        report.checks.append(self._check_duplicate(obj, seen_keys))
        report.checks.append(self._check_timestamps(obj))
        report.checks.append(self._check_checksum(obj))

        if self.strict:
            # Escalate WARNs to FAILs when strict=True
            for check in report.checks:
                if check.status == ValidationStatus.WARN:
                    check.status = ValidationStatus.FAIL

        self._log_report(report)
        return report

    def validate_all(
        self,
        objects: List[UnifiedObject],
        seen_keys: Optional[Set[str]] = None,
    ) -> List[ValidationReport]:
        """
        Validate a list of ``UnifiedObject``s.

        Parameters
        ----------
        objects : list[UnifiedObject]
            Normalized objects to validate.
        seen_keys : set[str] | None
            Shared duplicate-detection state.  If *None*, a fresh set
            is created for this batch only.

        Returns
        -------
        list[ValidationReport]
            One report per input object, in order.
        """
        if seen_keys is None:
            seen_keys = set()
        return [self.validate(obj, seen_keys) for obj in objects]

    # ------------------------------------------------------------------
    # Check 1 — Schema Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _check_schema_validation(obj: UnifiedObject) -> CheckResult:
        """
        Verify that the object is a proper UnifiedObject instance and
        the metadata sub-object is present and typed correctly.
        """
        name = "schema_validation"
        if not isinstance(obj, UnifiedObject):
            return CheckResult(
                name,
                ValidationStatus.FAIL,
                f"Expected UnifiedObject, got {type(obj).__name__}.",
            )
        if not isinstance(obj.metadata, MetadataSchema):
            return CheckResult(
                name,
                ValidationStatus.FAIL,
                "UnifiedObject.metadata must be a MetadataSchema instance.",
            )
        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Check 2 — Required Fields
    # ------------------------------------------------------------------

    @staticmethod
    def _check_required_fields(obj: UnifiedObject) -> CheckResult:
        """
        Verify that every required metadata field is non-empty, and that
        source-type-specific required fields are populated.

        Required metadata fields (01_UNIFIED_SCHEMA.md):
          uuid, source_type, validation_status, schema_version, collector,
          collection_timestamp, checksum

        API-specific required fields (02_DATASET_SPECIFICATIONS.md):
          series_id, year, period, value
        """
        name = "required_fields"
        missing: List[str] = []

        meta = obj.metadata

        # Metadata required fields
        if not meta.uuid:
            missing.append("metadata.uuid")
        if not meta.source_type:
            missing.append("metadata.source_type")
        if not meta.validation_status:
            missing.append("metadata.validation_status")
        if not meta.schema_version:
            missing.append("metadata.schema_version")
        if not meta.collector:
            missing.append("metadata.collector")
        if not meta.collection_timestamp:
            missing.append("metadata.collection_timestamp")
        if not meta.checksum:
            missing.append("metadata.checksum")

        # Source-type-specific required fields
        if meta.source_type == "API":
            if obj.api is None:
                missing.append("api (required for source_type=API)")
            else:
                api = obj.api
                if not api.series_id:
                    missing.append("api.series_id")
                if not api.year:
                    missing.append("api.year")
                if not api.period:
                    missing.append("api.period")
                if not api.value:
                    missing.append("api.value")

        if missing:
            return CheckResult(
                name,
                ValidationStatus.FAIL,
                f"Missing required fields: {missing}.",
            )
        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Check 3 — Data Type Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _check_data_types(obj: UnifiedObject) -> CheckResult:
        """
        Validate field types for populated sub-schemas.

        Rules:
          - source_type must be in VALID_SOURCE_TYPES.
          - validation_status must be in VALID_VALIDATION_STATUSES.
          - api.latest must be a bool.
          - api.footnotes must be a list of strings.
          - api.year must match \\d{4}.
          - api.period must match BLS period pattern.
          - api.value must be parseable as a float or be empty/null indicator.
        """
        name = "data_types"
        errors: List[str] = []

        meta = obj.metadata

        if meta.source_type and meta.source_type not in VALID_SOURCE_TYPES:
            errors.append(
                f"metadata.source_type '{meta.source_type}' invalid; "
                f"must be one of {sorted(VALID_SOURCE_TYPES)}."
            )

        if meta.validation_status and meta.validation_status not in VALID_VALIDATION_STATUSES:
            errors.append(
                f"metadata.validation_status '{meta.validation_status}' invalid; "
                "must be PASS or FAIL."
            )

        if obj.api is not None:
            api = obj.api

            if not isinstance(api.latest, bool):
                errors.append(
                    f"api.latest must be bool, got {type(api.latest).__name__}."
                )

            if not isinstance(api.footnotes, list):
                errors.append(
                    f"api.footnotes must be list, got {type(api.footnotes).__name__}."
                )
            else:
                for i, fn in enumerate(api.footnotes):
                    if not isinstance(fn, str):
                        errors.append(
                            f"api.footnotes[{i}] must be str, got {type(fn).__name__}."
                        )

            if api.year and not _YEAR_RE.match(api.year):
                errors.append(
                    f"api.year '{api.year}' must be a 4-digit string."
                )

            if api.period and not _PERIOD_RE.match(api.period):
                errors.append(
                    f"api.period '{api.period}' does not match expected BLS period format."
                )

            if api.value:
                try:
                    float(api.value)
                except (ValueError, TypeError):
                    errors.append(
                        f"api.value '{api.value}' is not a valid numeric string."
                    )

        if errors:
            return CheckResult(name, ValidationStatus.FAIL, "; ".join(errors))
        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Check 4 — Relationship Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _check_relationships(obj: UnifiedObject) -> CheckResult:
        """
        Verify that series_id in metadata matches api.series_id when
        both are present.

        From 01_UNIFIED_SCHEMA.md — relationships must be traceable.
        """
        name = "relationship_validation"
        meta = obj.metadata

        if obj.api is not None and meta.series_id and obj.api.series_id:
            if meta.series_id != obj.api.series_id:
                return CheckResult(
                    name,
                    ValidationStatus.FAIL,
                    f"metadata.series_id '{meta.series_id}' does not match "
                    f"api.series_id '{obj.api.series_id}'.",
                )

        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Check 5 — Duplicate Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _check_duplicate(
        obj: UnifiedObject,
        seen_keys: Optional[Set[str]],
    ) -> CheckResult:
        """
        Stateless within-object duplicate detection using a caller-supplied
        ``seen_keys`` set.

        Duplicate detection levels (05_Validation_And_Maintenance.md):
          Level 1: URL (via source_url if available)
          Level 3: series_id + year + period  (API objects)
          Level 4: SHA-256 checksum

        If ``seen_keys`` is None, duplicate detection is skipped.
        """
        name = "duplicate_detection"

        if seen_keys is None:
            return CheckResult(name, ValidationStatus.PASS, "Duplicate detection skipped (no seen_keys).")

        meta = obj.metadata
        keys_to_check: List[str] = []

        # Level 3 — API primary key
        if obj.api is not None and obj.api.series_id and obj.api.year and obj.api.period:
            pk = f"api::{obj.api.series_id}::{obj.api.year}::{obj.api.period}"
            keys_to_check.append(pk)

        # Level 4 — checksum
        if meta.checksum:
            keys_to_check.append(f"checksum::{meta.checksum}")

        for key in keys_to_check:
            if key in seen_keys:
                return CheckResult(
                    name,
                    ValidationStatus.FAIL,
                    f"Duplicate detected — key already seen: '{key}'.",
                )

        # Register all keys for this object
        seen_keys.update(keys_to_check)
        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Check 6 — Timestamp Verification
    # ------------------------------------------------------------------

    @staticmethod
    def _check_timestamps(obj: UnifiedObject) -> CheckResult:
        """
        Verify that all required timestamps are present and ISO-8601 UTC.

        From 05_Validation_And_Maintenance.md:
          - Publication timestamp exists.
          - Timestamp format is ISO-8601.
          - UTC conversion is correct (Z suffix).
        """
        name = "timestamp_verification"
        errors: List[str] = []

        meta = obj.metadata

        for field_name, value in [
            ("collection_timestamp", meta.collection_timestamp),
            ("normalization_timestamp", meta.normalization_timestamp),
        ]:
            if value and not _ISO8601_UTC_RE.match(value):
                errors.append(
                    f"metadata.{field_name} '{value}' is not a valid "
                    "ISO-8601 UTC timestamp (expected YYYY-MM-DDTHH:MM:SSZ)."
                )

        if errors:
            return CheckResult(name, ValidationStatus.FAIL, "; ".join(errors))
        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Check 7 — Checksum Verification
    # ------------------------------------------------------------------

    @staticmethod
    def _check_checksum(obj: UnifiedObject) -> CheckResult:
        """
        Verify that the stored checksum is present and well-formed.

        A deep re-computation of the checksum is intentionally NOT
        performed here (that would couple this module to the normalizer).
        We verify format only; full re-computation is a storage-layer
        concern (M18).
        """
        name = "checksum_verification"
        meta = obj.metadata

        if not meta.checksum:
            return CheckResult(
                name,
                ValidationStatus.FAIL,
                "metadata.checksum is missing.  Run UnifiedNormalizer first.",
            )

        if not _SHA256_RE.match(meta.checksum):
            return CheckResult(
                name,
                ValidationStatus.FAIL,
                f"metadata.checksum '{meta.checksum[:12]}…' is not a valid "
                "SHA-256 hex digest (expected 64 lowercase hex chars).",
            )

        return CheckResult(name, ValidationStatus.PASS)

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------

    @staticmethod
    def _log_report(report: ValidationReport) -> None:
        if report.failed:
            logger.warning(
                "VALIDATION FAIL uuid=%s series_id=%s — %d check(s) failed: %s",
                report.uuid,
                report.series_id,
                len(report.failures),
                [f.check_name for f in report.failures],
            )
        elif report.overall_status == ValidationStatus.WARN:
            logger.info(
                "VALIDATION WARN uuid=%s series_id=%s — %d warning(s).",
                report.uuid,
                report.series_id,
                len(report.warnings),
            )
        else:
            logger.debug(
                "VALIDATION PASS uuid=%s series_id=%s.",
                report.uuid,
                report.series_id,
            )
