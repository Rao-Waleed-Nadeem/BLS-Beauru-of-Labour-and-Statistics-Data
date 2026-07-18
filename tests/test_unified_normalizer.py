"""
test_unified_normalizer.py — M16 Unified Normalizer Tests

Tests for pipeline.normalizers.unified_normalizer.UnifiedNormalizer.

Coverage:
  - normalize() enriches metadata.uuid when missing
  - normalize() preserves existing uuid
  - normalize() sets normalization_timestamp to UTC ISO-8601
  - normalize() preserves existing normalization_timestamp
  - normalize() sets schema_version when absent
  - normalize() preserves existing schema_version
  - normalize() computes and attaches SHA-256 checksum
  - checksum is stable (same object → same checksum)
  - checksum changes when payload changes
  - normalize() raises ValueError for None metadata
  - normalize() raises ValueError for invalid source_type
  - normalize() raises ValueError for invalid validation_status
  - normalize() raises ValueError for missing source_type
  - normalize() raises ValueError for missing collector
  - normalize_all() normalizes a list of objects
  - normalize_all() collects errors from multiple bad objects
  - Works with API source_type
  - Works with HTML source_type
  - Works with PDF source_type
  - Works with RSS source_type
  - Works with ARCHIVE source_type
  - Export from package works
"""

import json
import re
from dataclasses import asdict

import pytest

from pipeline.normalizers.unified_normalizer import (
    UnifiedNormalizer,
    _compute_checksum,
    _utc_now_iso,
    _validate_metadata,
    VALID_SOURCE_TYPES,
)
from pipeline.parsers.models import (
    APISchema,
    MetadataSchema,
    UnifiedObject,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_meta(
    uuid: str = "",
    source_type: str = "API",
    validation_status: str = "PASS",
    normalization_timestamp: str = "",
    schema_version: str = "1.0",
    collector: str = "test_collector",
    series_id: str = "CUUR0000SA0",
    checksum: str = "",
) -> MetadataSchema:
    return MetadataSchema(
        uuid=uuid,
        dataset_id="BLS-DS-001",
        program_id="BLS-PGM-001",
        series_id=series_id,
        collector=collector,
        collector_version="1.0",
        schema_version=schema_version,
        source_type=source_type,
        collection_timestamp="2026-07-18T08:30:00Z",
        normalization_timestamp=normalization_timestamp,
        validation_status=validation_status,
        checksum=checksum,
    )


def _make_api_schema(
    series_id: str = "CUUR0000SA0",
    year: str = "2026",
    period: str = "M06",
    value: str = "315.605",
) -> APISchema:
    return APISchema(
        series_id=series_id,
        series_title="CPI-U All Items",
        frequency="Monthly",
        year=year,
        period=period,
        period_name="June",
        value=value,
        latest=True,
        footnotes=[],
    )


def _make_obj(
    uuid: str = "",
    source_type: str = "API",
    validation_status: str = "PASS",
    normalization_timestamp: str = "",
    schema_version: str = "1.0",
    collector: str = "test_collector",
) -> UnifiedObject:
    meta = _make_meta(
        uuid=uuid,
        source_type=source_type,
        validation_status=validation_status,
        normalization_timestamp=normalization_timestamp,
        schema_version=schema_version,
        collector=collector,
    )
    return UnifiedObject(metadata=meta, api=_make_api_schema())


_ISO8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)


# ---------------------------------------------------------------------------
# Unit Tests — internal helpers
# ---------------------------------------------------------------------------

class TestUtcNowIso:
    def test_returns_string(self):
        ts = _utc_now_iso()
        assert isinstance(ts, str)

    def test_matches_iso8601_utc(self):
        ts = _utc_now_iso()
        assert _ISO8601_PATTERN.match(ts), f"Unexpected format: {ts!r}"


class TestValidateMetadata:
    def test_valid_metadata_returns_no_errors(self):
        meta = _make_meta()
        assert _validate_metadata(meta) == []

    def test_missing_source_type(self):
        meta = _make_meta(source_type="")
        errors = _validate_metadata(meta)
        assert any("source_type" in e for e in errors)

    def test_invalid_source_type(self):
        meta = _make_meta(source_type="INVALID")
        errors = _validate_metadata(meta)
        assert any("source_type" in e for e in errors)

    def test_missing_validation_status(self):
        meta = _make_meta(validation_status="")
        errors = _validate_metadata(meta)
        assert any("validation_status" in e for e in errors)

    def test_invalid_validation_status(self):
        meta = _make_meta(validation_status="UNKNOWN")
        errors = _validate_metadata(meta)
        assert any("validation_status" in e for e in errors)

    def test_missing_collector(self):
        meta = _make_meta(collector="")
        errors = _validate_metadata(meta)
        assert any("collector" in e for e in errors)

    def test_all_valid_source_types(self):
        for st in VALID_SOURCE_TYPES:
            meta = _make_meta(source_type=st)
            assert _validate_metadata(meta) == [], f"Failed for source_type={st}"


class TestComputeChecksum:
    def test_returns_hex_string(self):
        obj = _make_obj()
        result = _compute_checksum(obj)
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_stable_for_same_object(self):
        obj = _make_obj()
        c1 = _compute_checksum(obj)
        c2 = _compute_checksum(obj)
        assert c1 == c2

    def test_changes_when_payload_changes(self):
        obj1 = _make_obj()
        obj2 = UnifiedObject(
            metadata=_make_meta(series_id="WPU00000000"),
            api=_make_api_schema(value="999.999"),
        )
        assert _compute_checksum(obj1) != _compute_checksum(obj2)

    def test_not_affected_by_existing_checksum_field(self):
        """Checksum of object with pre-set checksum field must equal
        checksum of same object with empty checksum field."""
        obj_empty = _make_obj()
        c_empty = _compute_checksum(obj_empty)

        obj_pre = _make_obj()
        obj_pre.metadata.checksum = "some_previous_value"
        c_pre = _compute_checksum(obj_pre)

        assert c_empty == c_pre


# ---------------------------------------------------------------------------
# Unit Tests — UnifiedNormalizer.normalize()
# ---------------------------------------------------------------------------

class TestNormalizeUUID:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_uuid_generated_when_missing(self):
        obj = _make_obj(uuid="")
        self.normalizer.normalize(obj)
        assert obj.metadata.uuid != ""

    def test_uuid_is_valid_uuid4(self):
        import uuid as _u
        obj = _make_obj(uuid="")
        self.normalizer.normalize(obj)
        # Will raise ValueError if not a valid UUID
        parsed = _u.UUID(obj.metadata.uuid)
        assert parsed.version == 4

    def test_existing_uuid_preserved(self):
        obj = _make_obj(uuid="my-fixed-uuid")
        self.normalizer.normalize(obj)
        assert obj.metadata.uuid == "my-fixed-uuid"


class TestNormalizeTimestamp:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_normalization_timestamp_set_when_missing(self):
        obj = _make_obj(normalization_timestamp="")
        self.normalizer.normalize(obj)
        assert obj.metadata.normalization_timestamp != ""

    def test_normalization_timestamp_is_utc_iso8601(self):
        obj = _make_obj(normalization_timestamp="")
        self.normalizer.normalize(obj)
        ts = obj.metadata.normalization_timestamp
        assert _ISO8601_PATTERN.match(ts), f"Unexpected format: {ts!r}"

    def test_existing_normalization_timestamp_preserved(self):
        obj = _make_obj(normalization_timestamp="2026-01-01T00:00:00Z")
        self.normalizer.normalize(obj)
        assert obj.metadata.normalization_timestamp == "2026-01-01T00:00:00Z"


class TestNormalizeSchemaVersion:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_schema_version_preserved(self):
        obj = _make_obj(schema_version="2.0")
        self.normalizer.normalize(obj)
        assert obj.metadata.schema_version == "2.0"

    def test_schema_version_set_when_missing(self):
        obj = _make_obj(schema_version="")
        obj.metadata.schema_version = ""
        self.normalizer.normalize(obj)
        assert obj.metadata.schema_version != ""


class TestNormalizeChecksum:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_checksum_is_set(self):
        obj = _make_obj()
        self.normalizer.normalize(obj)
        assert obj.metadata.checksum != ""

    def test_checksum_is_64_hex_chars(self):
        obj = _make_obj()
        self.normalizer.normalize(obj)
        c = obj.metadata.checksum
        assert len(c) == 64
        assert all(ch in "0123456789abcdef" for ch in c)

    def test_checksum_stable_across_calls(self):
        """Two normalize calls on equivalent objects should give the same
        checksum (timestamps must be pre-set for determinism)."""
        ts = "2026-07-18T08:31:00Z"
        uid = "fixed-uuid"
        obj1 = _make_obj(uuid=uid, normalization_timestamp=ts)
        obj2 = _make_obj(uuid=uid, normalization_timestamp=ts)
        self.normalizer.normalize(obj1)
        self.normalizer.normalize(obj2)
        assert obj1.metadata.checksum == obj2.metadata.checksum


# ---------------------------------------------------------------------------
# Error / validation tests
# ---------------------------------------------------------------------------

class TestNormalizeErrors:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_none_metadata_raises(self):
        obj = UnifiedObject(metadata=None)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="metadata must not be None"):
            self.normalizer.normalize(obj)

    def test_invalid_source_type_raises(self):
        obj = _make_obj(source_type="INVALID")
        with pytest.raises(ValueError, match="source_type"):
            self.normalizer.normalize(obj)

    def test_empty_source_type_raises(self):
        obj = _make_obj(source_type="")
        with pytest.raises(ValueError, match="source_type"):
            self.normalizer.normalize(obj)

    def test_invalid_validation_status_raises(self):
        obj = _make_obj(validation_status="UNKNOWN")
        with pytest.raises(ValueError, match="validation_status"):
            self.normalizer.normalize(obj)

    def test_missing_collector_raises(self):
        obj = _make_obj(collector="")
        with pytest.raises(ValueError, match="collector"):
            self.normalizer.normalize(obj)


# ---------------------------------------------------------------------------
# Source-type coverage
# ---------------------------------------------------------------------------

class TestSourceTypes:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    @pytest.mark.parametrize("source_type", ["API", "HTML", "PDF", "RSS", "ARCHIVE"])
    def test_valid_source_types_accepted(self, source_type):
        obj = _make_obj(source_type=source_type)
        result = self.normalizer.normalize(obj)
        assert result.metadata.source_type == source_type


# ---------------------------------------------------------------------------
# normalize_all() tests
# ---------------------------------------------------------------------------

class TestNormalizeAll:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_normalizes_list(self):
        objects = [_make_obj() for _ in range(3)]
        results = self.normalizer.normalize_all(objects)
        assert len(results) == 3

    def test_all_results_have_checksums(self):
        objects = [_make_obj() for _ in range(3)]
        results = self.normalizer.normalize_all(objects)
        for r in results:
            assert r.metadata.checksum != ""

    def test_all_results_have_uuids(self):
        objects = [_make_obj(uuid="") for _ in range(3)]
        results = self.normalizer.normalize_all(objects)
        uuids = [r.metadata.uuid for r in results]
        # All UUIDs must be non-empty and unique
        assert all(uuids)
        assert len(set(uuids)) == 3

    def test_empty_list_returns_empty(self):
        results = self.normalizer.normalize_all([])
        assert results == []

    def test_single_bad_object_raises(self):
        bad = _make_obj(source_type="INVALID")
        with pytest.raises(ValueError, match="failed normalization"):
            self.normalizer.normalize_all([bad])

    def test_multiple_bad_objects_collected(self):
        bad1 = _make_obj(source_type="INVALID")
        bad2 = _make_obj(validation_status="WRONG")
        with pytest.raises(ValueError) as exc_info:
            self.normalizer.normalize_all([bad1, bad2])
        assert "2 object(s)" in str(exc_info.value)

    def test_mixed_good_bad_raises_not_partial(self):
        """If any object fails, the whole call raises — no partial results."""
        good = _make_obj()
        bad = _make_obj(source_type="INVALID")
        with pytest.raises(ValueError):
            self.normalizer.normalize_all([good, bad])


# ---------------------------------------------------------------------------
# JSON serialisability
# ---------------------------------------------------------------------------

class TestJsonSerializable:
    def setup_method(self):
        self.normalizer = UnifiedNormalizer()

    def test_normalized_object_is_json_serializable(self):
        obj = _make_obj()
        self.normalizer.normalize(obj)
        d = asdict(obj)
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["metadata"]["checksum"] != ""
        assert parsed["metadata"]["uuid"] != ""

    def test_checksum_in_serialized_output(self):
        obj = _make_obj()
        self.normalizer.normalize(obj)
        d = asdict(obj)
        assert len(d["metadata"]["checksum"]) == 64


# ---------------------------------------------------------------------------
# Export / import tests
# ---------------------------------------------------------------------------

class TestExport:
    def test_import_from_package(self):
        from pipeline.normalizers import UnifiedNormalizer as N
        assert N is not None

    def test_is_instantiable(self):
        from pipeline.normalizers import UnifiedNormalizer as N
        n = N()
        assert hasattr(n, "normalize")
        assert hasattr(n, "normalize_all")
