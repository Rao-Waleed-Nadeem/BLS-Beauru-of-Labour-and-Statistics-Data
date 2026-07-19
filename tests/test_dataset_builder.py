"""tests.test_dataset_builder — M19 Dataset Builder Tests"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.datasets.dataset_builder import DatasetBuilder
from pipeline.normalizers.unified_normalizer import UnifiedNormalizer
from pipeline.parsers.models import APISchema, MetadataSchema, UnifiedObject
from pipeline.storage.storage_manager import StorageManager


def _make_meta(
    dataset_id: str = "cpi",
    series_id: str = "CUUR0000SA0",
    uuid: str = "",
    program_id: str = "BLS-PGM-001",
) -> MetadataSchema:
    return MetadataSchema(
        uuid=uuid,
        dataset_id=dataset_id,
        program_id=program_id,
        series_id=series_id,
        collector="test_collector",
        collector_version="1.0",
        schema_version="1.0",
        source_type="API",
        collection_timestamp="2026-07-18T08:30:00Z",
        normalization_timestamp="2026-07-18T08:31:00Z",
        validation_status="PASS",
        checksum="",
    )


def _make_api(year: str, period: str, value: str = "1.0") -> APISchema:
    return APISchema(
        series_id="CUUR0000SA0",
        series_title="CPI-U",
        frequency="Monthly",
        year=year,
        period=period,
        period_name="",
        value=value,
        latest=True,
        footnotes=[],
    )


def _make_validated_obj(*, dataset_id: str, year: str, period: str, uuid: str = "") -> UnifiedObject:
    """Create a UnifiedObject and run UnifiedNormalizer so checksum/timestamps are correct."""
    meta = _make_meta(dataset_id=dataset_id, uuid=uuid)
    api = _make_api(year=year, period=period)
    meta.checksum = ""  # allow normalizer to compute
    obj = UnifiedObject(metadata=meta, api=api)
    UnifiedNormalizer().normalize(obj)

    # Ensure it's treated as validated by having validation_status PASS.
    obj.metadata.validation_status = "PASS"
    return obj


class TestDatasetBuilderGroupingAndMerging:
    def test_group_by_dataset(self, tmp_path):
        storage = StorageManager(tmp_path)
        b = DatasetBuilder(storage=storage)

        objs = [
            _make_validated_obj(dataset_id="cpi", year="2026", period="M06"),
            _make_validated_obj(dataset_id="ppi", year="2026", period="M06"),
        ]
        grouped = b.group_by_dataset(objs)
        assert set(grouped.keys()) == {"cpi", "ppi"}
        assert len(grouped["cpi"]) == 1
        assert len(grouped["ppi"]) == 1

    def test_dedupe_by_primary_key(self, tmp_path):
        storage = StorageManager(tmp_path)
        b = DatasetBuilder(storage=storage)

        # Same series/year/period => should merge to 1
        o1 = _make_validated_obj(dataset_id="cpi", year="2026", period="M06", uuid="uuid-1")
        o2 = _make_validated_obj(dataset_id="cpi", year="2026", period="M06", uuid="uuid-2")
        merged = b.merge_dedupe_sort([o1, o2])
        assert len(merged) == 1

    def test_chronological_sort_year_then_period(self, tmp_path):
        storage = StorageManager(tmp_path)
        b = DatasetBuilder(storage=storage)

        objs = [
            _make_validated_obj(dataset_id="cpi", year="2026", period="M12"),
            _make_validated_obj(dataset_id="cpi", year="2025", period="M06"),
            _make_validated_obj(dataset_id="cpi", year="2026", period="M01"),
        ]
        merged = b.merge_dedupe_sort(objs)
        ordered = [(o.api.year, o.api.period) for o in merged]
        assert ordered == [("2025", "M06"), ("2026", "M01"), ("2026", "M12")]


class TestDatasetBuilderIntegrationToStorage:
    def test_build_processed_writes_required_files(self, tmp_path):
        storage = StorageManager(tmp_path)
        b = DatasetBuilder(storage=storage)

        objs = [
            _make_validated_obj(dataset_id="cpi", year="2026", period="M06"),
            _make_validated_obj(dataset_id="cpi", year="2026", period="M07"),
        ]

        summary = b.build_processed_from_validated(objs, write_csv=True, overwrite=False)
        assert "cpi" in summary
        assert summary["cpi"]["record_count"] == 2

        processed_dir = tmp_path / "processed" / "bls" / "cpi"
        assert (processed_dir / "dataset.json").exists()
        assert (processed_dir / "dataset.csv").exists()
        assert (processed_dir / "metadata.json").exists()
        assert (processed_dir / "relationships.json").exists()


    def test_overwrite_false_skips_existing_processed(self, tmp_path):
        storage = StorageManager(tmp_path)
        b = DatasetBuilder(storage=storage)

        objs = [_make_validated_obj(dataset_id="cpi", year="2026", period="M06")]
        b.build_processed_from_validated(objs, overwrite=False)

        # Second run with different record count should be skipped due to immutability rule
        objs2 = [
            _make_validated_obj(dataset_id="cpi", year="2026", period="M06"),
            _make_validated_obj(dataset_id="cpi", year="2026", period="M07"),
        ]
        summary2 = b.build_processed_from_validated(objs2, overwrite=False)
        assert summary2["cpi"]["storage"]["skipped"] is True

