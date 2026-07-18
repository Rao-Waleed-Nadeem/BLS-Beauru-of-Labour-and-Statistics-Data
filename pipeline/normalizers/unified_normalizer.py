"""
unified_normalizer.py — M16 Unified Normalizer

Converts a raw parser-produced UnifiedObject into a fully-enriched
normalized UnifiedObject that satisfies 01_UNIFIED_SCHEMA.md.

Responsibilities (pipeline Stage 6):
  - Set normalization_timestamp (UTC ISO-8601).
  - Generate UUID if metadata.uuid is empty.
  - Compute SHA-256 checksum of the serialized payload.
  - Validate required metadata fields.
  - Return an immutable-style copy with enriched metadata.

This module does NOT:
  - Download data        (that is a Collector responsibility)
  - Parse raw bytes/HTML (that is a Parser responsibility)
  - Persist anything     (that is a Storage responsibility)
  - Validate schema      (deep validation is a Validator responsibility)

Input:
    UnifiedObject — produced by any parser (APIParser, HTMLParser,
                    PDFParser, RSSParser)

Output:
    UnifiedObject — same object, with metadata.uuid, metadata.checksum,
                    and metadata.normalization_timestamp guaranteed to be set.

Rules (from 01_UNIFIED_SCHEMA.md):
  - source_type must be one of: API, HTML, PDF, RSS, ARCHIVE.
  - validation_status must be PASS or FAIL.
  - All timestamps must be UTC.
  - uuid must be globally unique.
  - Checksum is computed over the full serialized payload.
"""

import hashlib
import json
import logging
import uuid as _uuid_module
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Optional

from pipeline.parsers.models import MetadataSchema, UnifiedObject

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SOURCE_TYPES: frozenset = frozenset({"API", "HTML", "PDF", "RSS", "ARCHIVE"})
VALID_VALIDATION_STATUSES: frozenset = frozenset({"PASS", "FAIL"})
SCHEMA_VERSION: str = "1.0"


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------

def _compute_checksum(obj: UnifiedObject) -> str:
    """
    Compute a deterministic SHA-256 hex-digest of a UnifiedObject.

    The checksum is computed over the canonical JSON serialisation
    (sorted keys, no whitespace).  The metadata.checksum field itself
    is excluded to avoid a circular dependency.

    Parameters
    ----------
    obj : UnifiedObject
        The object to checksum.  Its ``metadata.checksum`` field is
        ignored during serialisation.

    Returns
    -------
    str
        64-character lower-case hex digest.
    """
    raw = asdict(obj)
    # Zero out the checksum field so the hash is stable
    if "metadata" in raw and raw["metadata"] is not None:
        raw["metadata"]["checksum"] = ""
    serialised = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_metadata(meta: MetadataSchema) -> List[str]:
    """
    Return a list of validation error strings for *meta*.

    An empty list means the metadata is valid.
    """
    errors: List[str] = []

    if not meta.source_type:
        errors.append("metadata.source_type is required.")
    elif meta.source_type not in VALID_SOURCE_TYPES:
        errors.append(
            f"metadata.source_type '{meta.source_type}' is not valid. "
            f"Must be one of: {sorted(VALID_SOURCE_TYPES)}."
        )

    if not meta.validation_status:
        errors.append("metadata.validation_status is required.")
    elif meta.validation_status not in VALID_VALIDATION_STATUSES:
        errors.append(
            f"metadata.validation_status '{meta.validation_status}' is not valid. "
            f"Must be PASS or FAIL."
        )

    if not meta.schema_version:
        errors.append("metadata.schema_version is required.")

    if not meta.collector:
        errors.append("metadata.collector is required.")

    return errors


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (with 'Z' suffix)."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# UnifiedNormalizer
# ---------------------------------------------------------------------------

class UnifiedNormalizer:
    """
    M16 Unified Normalizer.

    Enriches a parser-produced ``UnifiedObject`` with system-generated
    metadata (UUID, normalization timestamp, checksum) and validates
    required metadata fields before the object is forwarded to the
    Validator (M17) and Storage (M18) stages.

    Usage::

        normalizer = UnifiedNormalizer()

        # From an APIParser result
        raw_objects = api_parser.parse_all(response, metadata)
        normalized = [normalizer.normalize(obj) for obj in raw_objects]

        # From any other parser
        raw_obj = html_parser.parse(html_bytes, metadata)
        normalized_obj = normalizer.normalize(raw_obj)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, obj: UnifiedObject) -> UnifiedObject:
        """
        Normalize a single ``UnifiedObject``.

        Steps
        -----
        1. Validate required metadata fields.
        2. Generate UUID if ``metadata.uuid`` is empty.
        3. Set ``metadata.normalization_timestamp`` to current UTC time.
        4. Set ``metadata.schema_version`` to the module constant if absent.
        5. Compute SHA-256 checksum and set ``metadata.checksum``.

        Parameters
        ----------
        obj : UnifiedObject
            A parser-produced object.  Must have a populated
            ``metadata`` field.

        Returns
        -------
        UnifiedObject
            The same object with enriched metadata.  The input object
            is modified in-place and also returned for convenience.

        Raises
        ------
        ValueError
            If ``obj.metadata`` is ``None``, or required metadata fields
            fail validation.
        """
        if obj.metadata is None:
            raise ValueError(
                "UnifiedObject.metadata must not be None before normalization."
            )

        meta = obj.metadata

        # --- 1. Apply defaults before validation ------------------------
        # schema_version can be defaulted so parsers don't have to know
        # the current version string.
        if not meta.schema_version:
            meta.schema_version = SCHEMA_VERSION

        # --- 2. Validate required metadata fields -----------------------
        errors = _validate_metadata(meta)
        if errors:
            raise ValueError(
                f"Metadata validation failed ({len(errors)} error(s)): "
                + "; ".join(errors)
            )

        # --- 3. Generate UUID if missing --------------------------------
        if not meta.uuid:
            meta.uuid = str(_uuid_module.uuid4())
            logger.debug("Generated UUID %s for normalized object.", meta.uuid)

        # --- 4. Set normalization_timestamp if missing ------------------
        if not meta.normalization_timestamp:
            meta.normalization_timestamp = _utc_now_iso()

        # --- 5. Compute and attach checksum -----------------------------
        meta.checksum = _compute_checksum(obj)

        logger.debug(
            "Normalized object: uuid=%s series_id=%s source_type=%s checksum=%s",
            meta.uuid,
            meta.series_id,
            meta.source_type,
            meta.checksum[:8] + "...",
        )

        return obj

    def normalize_all(self, objects: List[UnifiedObject]) -> List[UnifiedObject]:
        """
        Normalize a list of ``UnifiedObject``s.

        Calls :meth:`normalize` on each element.  Failures on individual
        objects are collected and re-raised as a single ``ValueError``
        after all objects have been attempted, so the caller can see
        the full error set.

        Parameters
        ----------
        objects : list[UnifiedObject]
            Parser-produced objects.

        Returns
        -------
        list[UnifiedObject]
            Successfully normalized objects (in the same order).
            If *any* normalization fails, a ``ValueError`` is raised
            instead and no list is returned.

        Raises
        ------
        ValueError
            If one or more objects fail normalization.
        """
        results: List[UnifiedObject] = []
        failures: List[str] = []

        for i, obj in enumerate(objects):
            try:
                results.append(self.normalize(obj))
            except ValueError as exc:
                failures.append(f"Object[{i}]: {exc}")

        if failures:
            raise ValueError(
                f"{len(failures)} object(s) failed normalization:\n"
                + "\n".join(failures)
            )

        return results
