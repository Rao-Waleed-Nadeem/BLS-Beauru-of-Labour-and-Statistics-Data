"""
test_storage_manager.py — M18 Storage Manager Tests

Tests for pipeline.storage.storage_manager.StorageManager.

Coverage:
  Unit — StorageResult attributes
  Unit — _write_json creates file with correct content
  Unit — _write_json returns False if file exists and overwrite=False
  Unit — _write_json overwrites if overwrite=True
  Unit — _write_csv creates CSV with header and rows
  Unit — _sha256_file returns 64-char hex string
  Unit — _api_to_flat produces flat dict with expected keys

  StorageManager — __init__ creates canonical layer directories
  StorageManager — save_normalized writes normalized.json
  StorageManager — save_normalized skips if file exists
  StorageManager — save_normalized returns StorageResult with checksum
  StorageManager — save_normalized writes metadata sidecar
  StorageManager — save_normalized_batch writes batch JSON array
  StorageManager — save_normalized_batch skips if file exists

  StorageManager — save_validated accepts PASS report → writes file
  StorageManager — save_validated rejects FAIL report → no write
  StorageManager — save_validated writes validation.json sidecar
  StorageManager — save_validated skips if file exists (immutability)
  StorageManager — save_validated_batch filters out FAIL objects
  StorageManager — save_validated_batch rejects if all fail
  StorageManager — save_validated_batch raises if len mismatch
  StorageManager — save_validated_batch skips if file exists

  StorageManager — save_processed writes dataset.json
  StorageManager — save_processed writes dataset.csv
  StorageManager — save_processed writes metadata.json
  StorageManager — save_processed writes relationships.json
  StorageManager — save_processed skips if file exists
  StorageManager — save_processed overwrite=True overwrites
  StorageManager — save_processed rejects empty list
  StorageManager — save_processed write_csv=False skips CSV

  StorageManager — path_exists returns True after write
  StorageManager — path_exists returns False before write
  StorageManager — path_exists works for all three layers

  Export — import from package works
"""

import csv
import json
from pathlib import Path
from typing import List

import pytest

from pipeline.normalizers.unified_normalizer import UnifiedNormalizer
from pipeline.parsers.models import APISchema, MetadataSchema, UnifiedObject
from pipeline.storage import StorageManager, StorageResult
from pipeline.storage.storage_manager import (
    _sha256_file,
    _write_csv,
    _write_json,
)
from pipeline.validators import ValidationEngine, ValidationReport, ValidationStatus
from pipeline.validators.validation_result import CheckResult


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_NORMALIZER = UnifiedNormalizer()
_ENGINE = ValidationEngine()


def _make_meta(
    uuid: str = "test-uuid-0001",
    source_type: str = "API",
    series_id: str = "CUUR0000SA0",
    dataset_id: str = "cpi",
    program_id: str = "BLS-PGM-001",
    collection_timestamp: str = "2026-07-18T08:30:00Z",
) -> MetadataSchema:
    return MetadataSchema(
        uuid=uuid,
        dataset_id=dataset_id,
        program_id=program_id,
        series_id=series_id,
        collector="test_collector",
        collector_version="1.0",
        schema_version="1.0",
        source_type=source_type,
        collection_timestamp=collection_timestamp,
        normalization_timestamp="",
        validation_status="PASS",
        checksum="",
    )


def _make_api(
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


def _make_normalized_obj(
    series_id: str = "CUUR0000SA0",
    year: str = "2026",
    period: str = "M06",
    value: str = "315.605",
    uuid: str = "",
) -> UnifiedObject:
    """Return a fully normalized UnifiedObject."""
    meta = _make_meta(uuid=uuid, series_id=series_id)
    api = _make_api(series_id=series_id, year=year, period=period, value=value)
    meta.checksum = ""
    obj = UnifiedObject(metadata=meta, api=api)
    _NORMALIZER.normalize(obj)
    return obj


def _make_pass_report(obj: UnifiedObject) -> ValidationReport:
    """Return a PASS ValidationReport (using the real engine)."""
    return _ENGINE.validate(obj)


def _make_fail_report() -> ValidationReport:
    """Return an artificially FAILed ValidationReport."""
    report = ValidationReport(uuid="x", series_id="x", source_type="API")
    report.checks.append(CheckResult("schema_validation", ValidationStatus.FAIL, "forced failure"))
    return report


# ---------------------------------------------------------------------------
# Unit Tests — _write_json
# ---------------------------------------------------------------------------

class TestWriteJson:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "sub" / "file.json"
        result = _write_json(p, {"key": "value"})
        assert result is True
        assert p.exists()

    def test_content_is_valid_json(self, tmp_path):
        p = tmp_path / "data.json"
        _write_json(p, {"a": 1, "b": [1, 2]})
        parsed = json.loads(p.read_text())
        assert parsed == {"a": 1, "b": [1, 2]}

    def test_skips_existing_file_by_default(self, tmp_path):
        p = tmp_path / "data.json"
        _write_json(p, {"v": 1})
        result = _write_json(p, {"v": 2})  # should skip
        assert result is False
        # content unchanged
        assert json.loads(p.read_text())["v"] == 1

    def test_overwrites_when_flag_set(self, tmp_path):
        p = tmp_path / "data.json"
        _write_json(p, {"v": 1})
        _write_json(p, {"v": 2}, overwrite=True)
        assert json.loads(p.read_text())["v"] == 2

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "a" / "b" / "c" / "file.json"
        _write_json(p, {})
        assert p.exists()


# ---------------------------------------------------------------------------
# Unit Tests — _write_csv
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_creates_csv_with_header(self, tmp_path):
        p = tmp_path / "data.csv"
        records = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        result = _write_csv(p, records)
        assert result is True
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        assert len(rows) == 2
        assert rows[0]["a"] == "1"

    def test_skips_existing_file(self, tmp_path):
        p = tmp_path / "data.csv"
        _write_csv(p, [{"x": 1}])
        result = _write_csv(p, [{"x": 99}])
        assert result is False

    def test_returns_false_for_empty_records(self, tmp_path):
        p = tmp_path / "data.csv"
        result = _write_csv(p, [])
        assert result is False


# ---------------------------------------------------------------------------
# Unit Tests — _sha256_file
# ---------------------------------------------------------------------------

class TestSha256File:
    def test_returns_64_hex_chars(self, tmp_path):
        p = tmp_path / "file.txt"
        p.write_bytes(b"hello world")
        digest = _sha256_file(p)
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_same_content_same_digest(self, tmp_path):
        p1 = tmp_path / "f1.txt"
        p2 = tmp_path / "f2.txt"
        p1.write_bytes(b"abc")
        p2.write_bytes(b"abc")
        assert _sha256_file(p1) == _sha256_file(p2)

    def test_different_content_different_digest(self, tmp_path):
        p1 = tmp_path / "f1.txt"
        p2 = tmp_path / "f2.txt"
        p1.write_bytes(b"abc")
        p2.write_bytes(b"xyz")
        assert _sha256_file(p1) != _sha256_file(p2)


# ---------------------------------------------------------------------------
# Unit Tests — StorageResult
# ---------------------------------------------------------------------------

class TestStorageResult:
    def test_success_true(self):
        r = StorageResult(success=True, path=Path("/some/path"))
        assert r.success is True
        assert r.skipped is False

    def test_skipped_flag(self):
        r = StorageResult(success=True, skipped=True)
        assert r.skipped is True

    def test_repr_contains_ok(self):
        r = StorageResult(success=True)
        assert "OK" in repr(r)

    def test_repr_contains_skipped(self):
        r = StorageResult(success=True, skipped=True)
        assert "SKIPPED" in repr(r)

    def test_repr_contains_error(self):
        r = StorageResult(success=False)
        assert "ERROR" in repr(r)


# ---------------------------------------------------------------------------
# StorageManager — initialisation
# ---------------------------------------------------------------------------

class TestStorageManagerInit:
    def test_creates_layer_dirs(self, tmp_path):
        sm = StorageManager(tmp_path)
        for layer in ("raw", "normalized", "validated", "processed",
                      "features", "metadata", "logs", "backups"):
            assert (tmp_path / layer / "bls").is_dir()

    def test_accepts_str_path(self, tmp_path):
        sm = StorageManager(str(tmp_path))
        assert sm.root == tmp_path.resolve()


# ---------------------------------------------------------------------------
# StorageManager — save_normalized
# ---------------------------------------------------------------------------

class TestSaveNormalized:
    def test_writes_file(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        result = sm.save_normalized(obj, dataset_id="cpi", year="2026")
        assert result.success
        assert not result.skipped
        assert result.path.exists()

    def test_path_is_correct(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        result = sm.save_normalized(obj, dataset_id="cpi", year="2026")
        expected = tmp_path / "normalized" / "bls" / "cpi" / "2026" / "normalized.json"
        assert result.path == expected

    def test_file_is_valid_json(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        result = sm.save_normalized(obj, dataset_id="cpi", year="2026")
        parsed = json.loads(result.path.read_text())
        assert "metadata" in parsed
        assert parsed["metadata"]["source_type"] == "API"

    def test_returns_checksum(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        result = sm.save_normalized(obj, dataset_id="cpi", year="2026")
        assert len(result.checksum) == 64

    def test_skips_existing_file(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        sm.save_normalized(obj, dataset_id="cpi", year="2026")
        result2 = sm.save_normalized(obj, dataset_id="cpi", year="2026")
        assert result2.skipped

    def test_writes_metadata_sidecar(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        sm.save_normalized(obj, dataset_id="cpi", year="2026")
        meta_dir = tmp_path / "metadata" / "bls" / "cpi"
        sidecars = list(meta_dir.glob("*_metadata.json"))
        assert len(sidecars) >= 1


# ---------------------------------------------------------------------------
# StorageManager — save_normalized_batch
# ---------------------------------------------------------------------------

class TestSaveNormalizedBatch:
    def test_writes_batch_json_array(self, tmp_path):
        sm = StorageManager(tmp_path)
        objects = [_make_normalized_obj(period=f"M{i+1:02d}") for i in range(3)]
        result = sm.save_normalized_batch(objects, dataset_id="cpi", year="2026")
        assert result.success
        data = json.loads(result.path.read_text())
        assert isinstance(data, list)
        assert len(data) == 3

    def test_skips_existing_batch(self, tmp_path):
        sm = StorageManager(tmp_path)
        objects = [_make_normalized_obj()]
        sm.save_normalized_batch(objects, dataset_id="cpi", year="2026")
        result2 = sm.save_normalized_batch(objects, dataset_id="cpi", year="2026")
        assert result2.skipped


# ---------------------------------------------------------------------------
# StorageManager — save_validated
# ---------------------------------------------------------------------------

class TestSaveValidated:
    def test_writes_validated_json(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_pass_report(obj)
        result = sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        assert result.success
        assert result.path.exists()

    def test_path_is_correct(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_pass_report(obj)
        result = sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        expected = tmp_path / "validated" / "bls" / "cpi" / "2026" / "validated.json"
        assert result.path == expected

    def test_rejects_fail_report(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_fail_report()
        result = sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        assert not result.success

    def test_fail_does_not_write_file(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_fail_report()
        sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        expected = tmp_path / "validated" / "bls" / "cpi" / "2026" / "validated.json"
        assert not expected.exists()

    def test_writes_validation_sidecar(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_pass_report(obj)
        sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        sidecar = tmp_path / "validated" / "bls" / "cpi" / "2026" / "validation.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text())
        assert "overall_status" in data

    def test_skips_existing_file(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_pass_report(obj)
        sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        result2 = sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        assert result2.skipped

    def test_checksum_returned(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_pass_report(obj)
        result = sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        assert len(result.checksum) == 64


# ---------------------------------------------------------------------------
# StorageManager — save_validated_batch
# ---------------------------------------------------------------------------

class TestSaveValidatedBatch:
    def test_writes_batch_with_pass_objects(self, tmp_path):
        sm = StorageManager(tmp_path)
        objects = [_make_normalized_obj(period=f"M{i+1:02d}") for i in range(3)]
        reports = [_make_pass_report(o) for o in objects]
        result = sm.save_validated_batch(objects, reports, dataset_id="cpi", year="2026")
        assert result.success
        data = json.loads(result.path.read_text())
        assert len(data) == 3

    def test_filters_fail_objects(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj_pass = _make_normalized_obj(period="M06")
        obj_fail = _make_normalized_obj(period="M07")
        report_pass = _make_pass_report(obj_pass)
        report_fail = _make_fail_report()
        result = sm.save_validated_batch(
            [obj_pass, obj_fail],
            [report_pass, report_fail],
            dataset_id="cpi",
            year="2026",
        )
        assert result.success
        data = json.loads(result.path.read_text())
        assert len(data) == 1

    def test_rejects_if_all_fail(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_fail_report()
        result = sm.save_validated_batch([obj], [report], dataset_id="cpi", year="2026")
        assert not result.success

    def test_raises_on_length_mismatch(self, tmp_path):
        sm = StorageManager(tmp_path)
        objs = [_make_normalized_obj()]
        reports = []
        with pytest.raises(ValueError, match="same length"):
            sm.save_validated_batch(objs, reports, dataset_id="cpi", year="2026")

    def test_skips_if_file_exists(self, tmp_path):
        sm = StorageManager(tmp_path)
        objects = [_make_normalized_obj()]
        reports = [_make_pass_report(objects[0])]
        sm.save_validated_batch(objects, reports, dataset_id="cpi", year="2026")
        result2 = sm.save_validated_batch(objects, reports, dataset_id="cpi", year="2026")
        assert result2.skipped


# ---------------------------------------------------------------------------
# StorageManager — save_processed
# ---------------------------------------------------------------------------

class TestSaveProcessed:
    def _objects(self, count: int = 3) -> list:
        return [_make_normalized_obj(period=f"M{i+1:02d}") for i in range(count)]

    def test_writes_dataset_json(self, tmp_path):
        sm = StorageManager(tmp_path)
        objects = self._objects()
        result = sm.save_processed(objects, dataset_id="cpi")
        assert result.success
        assert result.path.name == "dataset.json"
        data = json.loads(result.path.read_text())
        assert isinstance(data, list)
        assert len(data) == 3

    def test_writes_dataset_csv(self, tmp_path):
        sm = StorageManager(tmp_path)
        objects = self._objects()
        sm.save_processed(objects, dataset_id="cpi")
        csv_path = tmp_path / "processed" / "bls" / "cpi" / "dataset.csv"
        assert csv_path.exists()
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        assert len(rows) == 3

    def test_writes_metadata_json(self, tmp_path):
        sm = StorageManager(tmp_path)
        sm.save_processed(self._objects(), dataset_id="cpi")
        meta_path = tmp_path / "processed" / "bls" / "cpi" / "metadata.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text())
        assert data["record_count"] == 3
        assert data["dataset_id"] == "cpi"

    def test_writes_relationships_json(self, tmp_path):
        sm = StorageManager(tmp_path)
        sm.save_processed(self._objects(), dataset_id="cpi")
        rel_path = tmp_path / "processed" / "bls" / "cpi" / "relationships.json"
        assert rel_path.exists()
        data = json.loads(rel_path.read_text())
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_skips_if_file_exists(self, tmp_path):
        sm = StorageManager(tmp_path)
        sm.save_processed(self._objects(), dataset_id="cpi")
        result2 = sm.save_processed(self._objects(), dataset_id="cpi")
        assert result2.skipped

    def test_overwrite_flag_rewrites(self, tmp_path):
        sm = StorageManager(tmp_path)
        sm.save_processed(self._objects(2), dataset_id="cpi")
        sm.save_processed(self._objects(5), dataset_id="cpi", overwrite=True)
        data = json.loads(
            (tmp_path / "processed" / "bls" / "cpi" / "dataset.json").read_text()
        )
        assert len(data) == 5

    def test_rejects_empty_list(self, tmp_path):
        sm = StorageManager(tmp_path)
        result = sm.save_processed([], dataset_id="cpi")
        assert not result.success

    def test_write_csv_false_skips_csv(self, tmp_path):
        sm = StorageManager(tmp_path)
        sm.save_processed(self._objects(), dataset_id="cpi", write_csv=False)
        csv_path = tmp_path / "processed" / "bls" / "cpi" / "dataset.csv"
        assert not csv_path.exists()

    def test_checksum_returned(self, tmp_path):
        sm = StorageManager(tmp_path)
        result = sm.save_processed(self._objects(), dataset_id="cpi")
        assert len(result.checksum) == 64


# ---------------------------------------------------------------------------
# StorageManager — path_exists
# ---------------------------------------------------------------------------

class TestPathExists:
    def test_false_before_write_normalized(self, tmp_path):
        sm = StorageManager(tmp_path)
        assert not sm.path_exists("normalized", "cpi", "2026")

    def test_true_after_write_normalized(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        sm.save_normalized(obj, dataset_id="cpi", year="2026")
        assert sm.path_exists("normalized", "cpi", "2026")

    def test_false_before_write_validated(self, tmp_path):
        sm = StorageManager(tmp_path)
        assert not sm.path_exists("validated", "cpi", "2026")

    def test_true_after_write_validated(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        report = _make_pass_report(obj)
        sm.save_validated(obj, report, dataset_id="cpi", year="2026")
        assert sm.path_exists("validated", "cpi", "2026")

    def test_false_before_write_processed(self, tmp_path):
        sm = StorageManager(tmp_path)
        assert not sm.path_exists("processed", "cpi")

    def test_true_after_write_processed(self, tmp_path):
        sm = StorageManager(tmp_path)
        obj = _make_normalized_obj()
        sm.save_processed([obj], dataset_id="cpi")
        assert sm.path_exists("processed", "cpi")

    def test_unknown_layer_returns_false(self, tmp_path):
        sm = StorageManager(tmp_path)
        assert not sm.path_exists("raw", "cpi", "2026")


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

class TestExport:
    def test_import_from_package(self):
        from pipeline.storage import StorageManager as SM
        assert SM is not None

    def test_storage_result_importable(self):
        from pipeline.storage import StorageResult as SR
        assert SR is not None

    def test_instantiable(self, tmp_path):
        from pipeline.storage import StorageManager as SM
        sm = SM(tmp_path)
        assert hasattr(sm, "save_normalized")
        assert hasattr(sm, "save_validated")
        assert hasattr(sm, "save_processed")
