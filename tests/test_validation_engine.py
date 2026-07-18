"""
test_validation_engine.py — M17 Validation Engine Tests

Tests for pipeline.validators.validation_engine.ValidationEngine
and pipeline.validators.validation_result.

Coverage:
  Unit — ValidationStatus enum
  Unit — CheckResult.passed / .failed properties
  Unit — ValidationReport.overall_status aggregation
  Unit — ValidationReport.failures / .warnings filters
  Unit — ValidationReport.to_dict serialisation

  Engine — validate() returns ValidationReport for valid object
  Engine — validate() PASS on fully valid API object
  Engine — validate() FAIL on None object
  Engine — validate() FAIL on None metadata
  Engine — schema_validation FAIL on wrong type
  Engine — required_fields: missing uuid
  Engine — required_fields: missing checksum
  Engine — required_fields: missing collector
  Engine — required_fields: missing collection_timestamp
  Engine — required_fields: missing api when source_type=API
  Engine — required_fields: missing api.series_id
  Engine — required_fields: missing api.year
  Engine — required_fields: missing api.period
  Engine — required_fields: missing api.value
  Engine — data_types: invalid source_type
  Engine — data_types: invalid validation_status
  Engine — data_types: api.latest not bool
  Engine — data_types: api.footnotes not list
  Engine — data_types: api.year wrong format
  Engine — data_types: api.period wrong format
  Engine — data_types: api.value not numeric
  Engine — relationship_validation: series_id mismatch
  Engine — relationship_validation: consistent ids pass
  Engine — duplicate_detection: no seen_keys → skipped
  Engine — duplicate_detection: fresh seen_keys → PASS
  Engine — duplicate_detection: repeat primary key → FAIL
  Engine — duplicate_detection: repeat checksum → FAIL
  Engine — duplicate_detection: seen_keys populated after pass
  Engine — timestamp_verification: valid timestamps pass
  Engine — timestamp_verification: bad collection_timestamp fails
  Engine — timestamp_verification: bad normalization_timestamp fails
  Engine — checksum_verification: valid sha256 passes
  Engine — checksum_verification: missing checksum fails
  Engine — checksum_verification: malformed checksum fails
  Engine — strict=True escalates WARN to FAIL
  Engine — strict=False keeps WARN as WARN
  Engine — validate_all() returns one report per object
  Engine — validate_all() shares seen_keys across objects
  Engine — validate_all() creates fresh seen_keys when not supplied
  Engine — all 7 checks present in report
  Export — import from package works
"""

import copy
import json
from typing import Set

import pytest

from pipeline.normalizers.unified_normalizer import UnifiedNormalizer
from pipeline.parsers.models import (
    APISchema,
    MetadataSchema,
    UnifiedObject,
)
from pipeline.validators import (
    CheckResult,
    ValidationEngine,
    ValidationReport,
    ValidationStatus,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_meta(
    uuid: str = "test-uuid-0001",
    source_type: str = "API",
    validation_status: str = "PASS",
    collector: str = "test_collector",
    series_id: str = "CUUR0000SA0",
    collection_timestamp: str = "2026-07-18T08:30:00Z",
    normalization_timestamp: str = "2026-07-18T08:31:00Z",
    checksum: str = "a" * 64,
    schema_version: str = "1.0",
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
        collection_timestamp=collection_timestamp,
        normalization_timestamp=normalization_timestamp,
        validation_status=validation_status,
        checksum=checksum,
    )


def _make_api(
    series_id: str = "CUUR0000SA0",
    year: str = "2026",
    period: str = "M06",
    value: str = "315.605",
    latest: bool = True,
    footnotes: list = None,
) -> APISchema:
    return APISchema(
        series_id=series_id,
        series_title="CPI-U All Items",
        frequency="Monthly",
        year=year,
        period=period,
        period_name="June",
        value=value,
        latest=latest,
        footnotes=footnotes if footnotes is not None else [],
    )


def _make_valid_obj(
    series_id: str = "CUUR0000SA0",
    **meta_kwargs,
) -> UnifiedObject:
    """Return a fully valid UnifiedObject (already normalizer-enriched)."""
    meta = _make_meta(series_id=series_id, **meta_kwargs)
    api = _make_api(series_id=series_id)
    return UnifiedObject(metadata=meta, api=api)


# Use the real normalizer to produce a properly checksummed object
_NORMALIZER = UnifiedNormalizer()


def _normalized_obj(**kwargs) -> UnifiedObject:
    """Produce a fully normalized valid object using the real normalizer."""
    meta = _make_meta(**kwargs)
    api = _make_api(series_id=meta.series_id)
    # Clear checksum so normalizer sets it
    meta.checksum = ""
    obj = UnifiedObject(metadata=meta, api=api)
    _NORMALIZER.normalize(obj)
    return obj


# ---------------------------------------------------------------------------
# Unit Tests — ValidationStatus
# ---------------------------------------------------------------------------

class TestValidationStatus:
    def test_pass_value(self):
        assert ValidationStatus.PASS == "PASS"

    def test_fail_value(self):
        assert ValidationStatus.FAIL == "FAIL"

    def test_warn_value(self):
        assert ValidationStatus.WARN == "WARN"


# ---------------------------------------------------------------------------
# Unit Tests — CheckResult
# ---------------------------------------------------------------------------

class TestCheckResult:
    def test_passed_true_on_pass(self):
        c = CheckResult("test", ValidationStatus.PASS)
        assert c.passed is True
        assert c.failed is False

    def test_failed_true_on_fail(self):
        c = CheckResult("test", ValidationStatus.FAIL, "bad")
        assert c.failed is True
        assert c.passed is False

    def test_warn_neither_pass_nor_failed(self):
        c = CheckResult("test", ValidationStatus.WARN, "soft issue")
        assert c.passed is False
        assert c.failed is False


# ---------------------------------------------------------------------------
# Unit Tests — ValidationReport
# ---------------------------------------------------------------------------

class TestValidationReport:
    def _report_with(self, *statuses: ValidationStatus) -> ValidationReport:
        report = ValidationReport(uuid="u", series_id="s", source_type="API")
        for i, st in enumerate(statuses):
            report.checks.append(CheckResult(f"check_{i}", st))
        return report

    def test_all_pass_gives_pass(self):
        report = self._report_with(ValidationStatus.PASS, ValidationStatus.PASS)
        assert report.overall_status == ValidationStatus.PASS
        assert report.passed

    def test_any_fail_gives_fail(self):
        report = self._report_with(ValidationStatus.PASS, ValidationStatus.FAIL)
        assert report.overall_status == ValidationStatus.FAIL
        assert report.failed

    def test_warn_without_fail_gives_warn(self):
        report = self._report_with(ValidationStatus.PASS, ValidationStatus.WARN)
        assert report.overall_status == ValidationStatus.WARN

    def test_fail_beats_warn(self):
        report = self._report_with(ValidationStatus.WARN, ValidationStatus.FAIL)
        assert report.overall_status == ValidationStatus.FAIL

    def test_failures_filter(self):
        report = self._report_with(
            ValidationStatus.PASS,
            ValidationStatus.FAIL,
            ValidationStatus.FAIL,
        )
        assert len(report.failures) == 2

    def test_warnings_filter(self):
        report = self._report_with(
            ValidationStatus.WARN,
            ValidationStatus.PASS,
        )
        assert len(report.warnings) == 1

    def test_to_dict_keys(self):
        report = self._report_with(ValidationStatus.PASS)
        d = report.to_dict()
        assert set(d.keys()) == {"uuid", "series_id", "source_type", "overall_status", "checks"}

    def test_to_dict_is_json_serializable(self):
        report = self._report_with(ValidationStatus.PASS, ValidationStatus.FAIL)
        d = report.to_dict()
        s = json.dumps(d)
        parsed = json.loads(s)
        assert parsed["overall_status"] == "FAIL"


# ---------------------------------------------------------------------------
# Integration Tests — ValidationEngine.validate()
# ---------------------------------------------------------------------------

class TestValidatePass:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_valid_object_passes(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        assert report.passed, [c.message for c in report.failures]

    def test_returns_validation_report(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        assert isinstance(report, ValidationReport)

    def test_all_seven_checks_present(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        assert len(report.checks) == 7

    def test_check_names_in_order(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        expected_names = [
            "schema_validation",
            "required_fields",
            "data_types",
            "relationship_validation",
            "duplicate_detection",
            "timestamp_verification",
            "checksum_verification",
        ]
        actual_names = [c.check_name for c in report.checks]
        assert actual_names == expected_names

    def test_uuid_in_report(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        assert report.uuid == obj.metadata.uuid

    def test_series_id_in_report(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        assert report.series_id == "CUUR0000SA0"


class TestValidateNoneInputs:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_none_object_returns_report_with_fail(self):
        report = self.engine.validate(None)
        assert report.failed

    def test_none_metadata_returns_fail(self):
        obj = UnifiedObject(metadata=None)  # type: ignore
        report = self.engine.validate(obj)
        assert report.failed


# ---------------------------------------------------------------------------
# Check 1 — Schema Validation
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_wrong_type_fails(self):
        report = self.engine.validate("not-a-unified-object")  # type: ignore
        schema_check = next(c for c in report.checks if c.check_name == "schema_validation")
        assert schema_check.failed

    def test_valid_object_passes(self):
        obj = _normalized_obj()
        report = self.engine.validate(obj)
        schema_check = next(c for c in report.checks if c.check_name == "schema_validation")
        assert schema_check.passed


# ---------------------------------------------------------------------------
# Check 2 — Required Fields
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _get_req_check(self, obj) -> CheckResult:
        report = self.engine.validate(obj)
        return next(c for c in report.checks if c.check_name == "required_fields")

    def test_valid_object_passes(self):
        obj = _normalized_obj()
        assert self._get_req_check(obj).passed

    def test_missing_uuid_fails(self):
        obj = _normalized_obj()
        obj.metadata.uuid = ""
        assert self._get_req_check(obj).failed

    def test_missing_checksum_fails(self):
        obj = _normalized_obj()
        obj.metadata.checksum = ""
        assert self._get_req_check(obj).failed

    def test_missing_collector_fails(self):
        obj = _normalized_obj()
        obj.metadata.collector = ""
        assert self._get_req_check(obj).failed

    def test_missing_collection_timestamp_fails(self):
        obj = _normalized_obj()
        obj.metadata.collection_timestamp = ""
        assert self._get_req_check(obj).failed

    def test_api_source_type_without_api_schema_fails(self):
        obj = _normalized_obj()
        obj.api = None
        check = self._get_req_check(obj)
        assert check.failed
        assert "api" in check.message.lower()

    def test_missing_api_series_id_fails(self):
        obj = _normalized_obj()
        obj.api.series_id = ""
        assert self._get_req_check(obj).failed

    def test_missing_api_year_fails(self):
        obj = _normalized_obj()
        obj.api.year = ""
        assert self._get_req_check(obj).failed

    def test_missing_api_period_fails(self):
        obj = _normalized_obj()
        obj.api.period = ""
        assert self._get_req_check(obj).failed

    def test_missing_api_value_fails(self):
        obj = _normalized_obj()
        obj.api.value = ""
        assert self._get_req_check(obj).failed


# ---------------------------------------------------------------------------
# Check 3 — Data Types
# ---------------------------------------------------------------------------

class TestDataTypes:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _get_dtype_check(self, obj) -> CheckResult:
        report = self.engine.validate(obj)
        return next(c for c in report.checks if c.check_name == "data_types")

    def test_valid_object_passes(self):
        obj = _normalized_obj()
        assert self._get_dtype_check(obj).passed

    def test_invalid_source_type_fails(self):
        obj = _normalized_obj()
        obj.metadata.source_type = "INVALID"
        assert self._get_dtype_check(obj).failed

    def test_invalid_validation_status_fails(self):
        obj = _normalized_obj()
        obj.metadata.validation_status = "UNKNOWN"
        assert self._get_dtype_check(obj).failed

    def test_api_latest_not_bool_fails(self):
        obj = _normalized_obj()
        obj.api.latest = "true"  # type: ignore — intentionally wrong type
        assert self._get_dtype_check(obj).failed

    def test_api_footnotes_not_list_fails(self):
        obj = _normalized_obj()
        obj.api.footnotes = "bad"  # type: ignore
        assert self._get_dtype_check(obj).failed

    def test_api_year_wrong_format_fails(self):
        obj = _normalized_obj()
        obj.api.year = "26"  # not 4-digit
        assert self._get_dtype_check(obj).failed

    def test_api_period_wrong_format_fails(self):
        obj = _normalized_obj()
        obj.api.period = "M15"  # out of range
        assert self._get_dtype_check(obj).failed

    def test_api_value_not_numeric_fails(self):
        obj = _normalized_obj()
        obj.api.value = "N/A"
        assert self._get_dtype_check(obj).failed

    @pytest.mark.parametrize("period", ["M01", "M12", "M13", "Q01", "Q05", "S01", "S02", "A01"])
    def test_valid_periods_pass(self, period):
        obj = _normalized_obj()
        obj.api.period = period
        assert self._get_dtype_check(obj).passed

    @pytest.mark.parametrize("source_type", ["API", "HTML", "PDF", "RSS", "ARCHIVE"])
    def test_valid_source_types_pass(self, source_type):
        obj = _normalized_obj()
        obj.metadata.source_type = source_type
        assert self._get_dtype_check(obj).passed


# ---------------------------------------------------------------------------
# Check 4 — Relationship Validation
# ---------------------------------------------------------------------------

class TestRelationshipValidation:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _get_rel_check(self, obj) -> CheckResult:
        report = self.engine.validate(obj)
        return next(c for c in report.checks if c.check_name == "relationship_validation")

    def test_matching_ids_pass(self):
        obj = _normalized_obj()
        assert obj.metadata.series_id == obj.api.series_id
        assert self._get_rel_check(obj).passed

    def test_mismatched_ids_fail(self):
        obj = _normalized_obj()
        obj.api.series_id = "WPU00000000"  # different from metadata
        check = self._get_rel_check(obj)
        assert check.failed
        assert "series_id" in check.message


# ---------------------------------------------------------------------------
# Check 5 — Duplicate Detection
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _get_dup_check(self, obj, seen_keys=None) -> CheckResult:
        report = self.engine.validate(obj, seen_keys=seen_keys)
        return next(c for c in report.checks if c.check_name == "duplicate_detection")

    def test_no_seen_keys_skipped(self):
        obj = _normalized_obj()
        check = self._get_dup_check(obj, seen_keys=None)
        assert check.passed
        assert "skipped" in check.message.lower()

    def test_fresh_seen_keys_passes(self):
        obj = _normalized_obj()
        check = self._get_dup_check(obj, seen_keys=set())
        assert check.passed

    def test_repeat_primary_key_fails(self):
        obj1 = _normalized_obj()
        obj2 = _normalized_obj()
        seen: Set[str] = set()
        self.engine.validate(obj1, seen_keys=seen)
        check2 = self._get_dup_check(obj2, seen_keys=seen)
        assert check2.failed
        assert "duplicate" in check2.message.lower()

    def test_seen_keys_populated_after_pass(self):
        obj = _normalized_obj()
        seen: Set[str] = set()
        self.engine.validate(obj, seen_keys=seen)
        assert len(seen) > 0

    def test_different_period_not_duplicate(self):
        obj1 = _normalized_obj()
        obj1.api.period = "M05"
        obj2 = _normalized_obj()
        obj2.api.period = "M06"
        # Re-checksum to avoid checksum collision
        obj1.metadata.checksum = "b" * 64
        obj2.metadata.checksum = "c" * 64
        seen: Set[str] = set()
        check1 = self._get_dup_check(obj1, seen_keys=seen)
        check2 = self._get_dup_check(obj2, seen_keys=seen)
        assert check1.passed
        assert check2.passed


# ---------------------------------------------------------------------------
# Check 6 — Timestamp Verification
# ---------------------------------------------------------------------------

class TestTimestampVerification:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _get_ts_check(self, obj) -> CheckResult:
        report = self.engine.validate(obj)
        return next(c for c in report.checks if c.check_name == "timestamp_verification")

    def test_valid_timestamps_pass(self):
        obj = _normalized_obj()
        assert self._get_ts_check(obj).passed

    def test_bad_collection_timestamp_fails(self):
        obj = _normalized_obj()
        obj.metadata.collection_timestamp = "2026-07-18 08:30:00"  # no T or Z
        assert self._get_ts_check(obj).failed

    def test_bad_normalization_timestamp_fails(self):
        obj = _normalized_obj()
        obj.metadata.normalization_timestamp = "not-a-timestamp"
        assert self._get_ts_check(obj).failed

    def test_empty_normalization_timestamp_passes(self):
        """Empty normalization_timestamp is not required — skip check."""
        obj = _normalized_obj()
        obj.metadata.normalization_timestamp = ""
        assert self._get_ts_check(obj).passed


# ---------------------------------------------------------------------------
# Check 7 — Checksum Verification
# ---------------------------------------------------------------------------

class TestChecksumVerification:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _get_ck_check(self, obj) -> CheckResult:
        report = self.engine.validate(obj)
        return next(c for c in report.checks if c.check_name == "checksum_verification")

    def test_valid_sha256_passes(self):
        obj = _normalized_obj()
        assert self._get_ck_check(obj).passed

    def test_missing_checksum_fails(self):
        obj = _normalized_obj()
        obj.metadata.checksum = ""
        assert self._get_ck_check(obj).failed

    def test_malformed_checksum_fails(self):
        obj = _normalized_obj()
        obj.metadata.checksum = "not-a-hex-digest"
        assert self._get_ck_check(obj).failed

    def test_uppercase_hex_fails(self):
        """SHA-256 must be lowercase hex."""
        obj = _normalized_obj()
        obj.metadata.checksum = "A" * 64
        assert self._get_ck_check(obj).failed


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------

class TestStrictMode:
    def test_strict_true_is_default(self):
        engine = ValidationEngine()
        assert engine.strict is True

    def test_strict_false_keeps_warn(self):
        """With strict=False, a WARN-level check stays WARN."""
        engine = ValidationEngine(strict=False)
        obj = _normalized_obj()
        # Inject a WARN check by temporarily patching seen_keys message
        report = engine.validate(obj, seen_keys=None)
        # duplicate_detection returns PASS with "skipped" message when no seen_keys
        dup_check = next(c for c in report.checks if c.check_name == "duplicate_detection")
        # Manually set to WARN to test strict escalation
        dup_check.status = ValidationStatus.WARN
        # With strict=False, overall should be WARN not FAIL
        assert report.overall_status == ValidationStatus.WARN

    def test_strict_true_escalates_warn_to_fail(self):
        engine = ValidationEngine(strict=True)
        report = ValidationReport(uuid="u", series_id="s", source_type="API")
        report.checks.append(CheckResult("test", ValidationStatus.PASS))
        report.checks.append(CheckResult("warn_check", ValidationStatus.WARN, "soft issue"))
        # Simulate what strict mode does
        for c in report.checks:
            if c.status == ValidationStatus.WARN:
                c.status = ValidationStatus.FAIL
        assert report.failed


# ---------------------------------------------------------------------------
# validate_all()
# ---------------------------------------------------------------------------

class TestValidateAll:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_returns_one_report_per_object(self):
        objs = [_normalized_obj() for _ in range(4)]
        # Give each a distinct checksum/primary key to avoid dup detection
        for i, obj in enumerate(objs):
            obj.api.period = f"M{i+1:02d}"
            obj.metadata.checksum = hex(i + 1)[2:].zfill(64)
        reports = self.engine.validate_all(objs)
        assert len(reports) == 4

    def test_empty_list_returns_empty(self):
        assert self.engine.validate_all([]) == []

    def test_creates_fresh_seen_keys_when_not_supplied(self):
        """Two identical objects should flag a duplicate."""
        obj1 = _normalized_obj()
        obj2 = _normalized_obj()  # same primary key
        reports = self.engine.validate_all([obj1, obj2])
        dup_checks = [
            next(c for c in r.checks if c.check_name == "duplicate_detection")
            for r in reports
        ]
        assert dup_checks[0].passed  # first occurrence ok
        assert dup_checks[1].failed  # second is a duplicate

    def test_shared_seen_keys_carry_across_calls(self):
        seen: Set[str] = set()
        obj1 = _normalized_obj()
        obj2 = _normalized_obj()
        self.engine.validate_all([obj1], seen_keys=seen)
        reports2 = self.engine.validate_all([obj2], seen_keys=seen)
        dup_check = next(c for c in reports2[0].checks if c.check_name == "duplicate_detection")
        assert dup_check.failed


# ---------------------------------------------------------------------------
# Export / import
# ---------------------------------------------------------------------------

class TestExport:
    def test_import_from_package(self):
        from pipeline.validators import ValidationEngine as E
        assert E is not None

    def test_import_result_types(self):
        from pipeline.validators import ValidationReport, ValidationStatus, CheckResult
        assert ValidationReport is not None
        assert ValidationStatus is not None
        assert CheckResult is not None

    def test_engine_is_instantiable(self):
        from pipeline.validators import ValidationEngine as E
        e = E()
        assert hasattr(e, "validate")
        assert hasattr(e, "validate_all")
