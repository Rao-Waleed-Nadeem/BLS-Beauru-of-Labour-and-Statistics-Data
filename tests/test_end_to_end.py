"""M23 end-to-end pipeline verification tests."""

from __future__ import annotations

import json

from pipeline.datasets.dataset_builder import DatasetBuilder
from pipeline.features.feature_builder import FeatureBuilder
from pipeline.normalizers.unified_normalizer import UnifiedNormalizer
from pipeline.parsers.api_parser import APIParser
from pipeline.storage.storage_manager import StorageManager
from pipeline.validators import (
    ReleaseKey,
    ValidationEngine,
    detect_duplicate_records,
    write_release_quality_reports,
)
from pipeline.validators.validation_result import ValidationStatus


def _api_fixture() -> dict:
    return {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 42,
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": "CUUR0000SA0",
                    "catalog": {
                        "series_title": "CPI-U All Items",
                        "frequency": "Monthly",
                    },
                    "data": [
                        {
                            "year": "2026",
                            "period": "M05",
                            "periodName": "May",
                            "value": "314.100",
                            "latest": "false",
                            "footnotes": [{}],
                        },
                        {
                            "year": "2026",
                            "period": "M06",
                            "periodName": "June",
                            "value": "315.605",
                            "latest": "true",
                            "footnotes": [{"text": "Preliminary."}],
                        },
                    ],
                }
            ]
        },
    }


def _metadata(source_path) -> dict:
    return {
        "dataset_id": "cpi",
        "program_id": "BLS-PROGRAM-CPI",
        "series_id": "CUUR0000SA0",
        "collector": "api_collector",
        "collector_version": "1.0",
        "schema_version": "1.0",
        "source_type": "API",
        "collection_timestamp": "2026-07-23T12:00:00Z",
        "validation_status": "PASS",
        "source_url": str(source_path),
    }


def test_api_pipeline_storage_dataset_features_and_quality_reports(tmp_path):
    storage = StorageManager(tmp_path)
    raw_response = tmp_path / "raw" / "bls" / "api" / "response.json"
    raw_response.parent.mkdir(parents=True, exist_ok=True)
    raw_response.write_text(json.dumps(_api_fixture()), encoding="utf-8")

    parsed = APIParser().parse_all(raw_response, _metadata(raw_response))
    normalized = UnifiedNormalizer().normalize_all(parsed)

    validator = ValidationEngine(strict=True)
    reports = validator.validate_all(normalized, seen_keys=set())

    assert [report.overall_status for report in reports] == [
        ValidationStatus.PASS,
        ValidationStatus.PASS,
    ]

    normalized_result = storage.save_normalized_batch(normalized, "cpi", "2026")
    validated_result = storage.save_validated_batch(normalized, reports, "cpi", "2026")
    assert normalized_result.success
    assert validated_result.success

    dataset_summary = DatasetBuilder(storage=storage).build_processed_from_validated(
        normalized,
        write_csv=True,
    )
    feature_summary = FeatureBuilder(storage=storage).build_features(
        "cpi",
        normalized,
        write_csv=True,
    )

    assert dataset_summary["cpi"]["record_count"] == 2
    assert feature_summary["record_count"] == 2

    processed_dir = tmp_path / "processed" / "bls" / "cpi"
    features_dir = tmp_path / "features" / "bls" / "cpi"
    assert (processed_dir / "dataset.json").exists()
    assert (processed_dir / "dataset.csv").exists()
    assert (processed_dir / "metadata.json").exists()
    assert (processed_dir / "relationships.json").exists()
    assert (features_dir / "feature_set.json").exists()
    assert (features_dir / "feature_set.csv").exists()

    reports_dir = tmp_path / "reports" / "bls" / "cpi"
    report_paths = write_release_quality_reports(
        expected_releases=[
            ReleaseKey("CUUR0000SA0", "2026", "M05"),
            ReleaseKey("CUUR0000SA0", "2026", "M06"),
            ReleaseKey("CUUR0000SA0", "2026", "M07"),
        ],
        collected_objects=normalized,
        output_dir=reports_dir,
    )

    missing_report = json.loads(report_paths["missing_releases.json"].read_text())
    duplicate_report = json.loads(report_paths["duplicate_report.json"].read_text())
    completeness_report = json.loads(report_paths["completeness_report.json"].read_text())

    assert missing_report["missing_count"] == 1
    assert missing_report["missing_releases"] == [
        {"series_id": "CUUR0000SA0", "year": "2026", "period": "M07"}
    ]
    assert duplicate_report["duplicate_count"] == 0
    assert completeness_report["complete"] is False


def test_end_to_end_duplicate_detection_rejects_duplicate_primary_key(tmp_path):
    raw_response = tmp_path / "response.json"
    raw_response.write_text(json.dumps(_api_fixture()), encoding="utf-8")

    parsed = APIParser().parse_all(raw_response, _metadata(raw_response))
    duplicate_batch = [parsed[0], parsed[0]]
    normalized = UnifiedNormalizer().normalize_all(duplicate_batch)

    reports = ValidationEngine(strict=True).validate_all(normalized, seen_keys=set())
    assert reports[0].overall_status == ValidationStatus.PASS
    assert reports[1].overall_status == ValidationStatus.FAIL
    assert any(
        check.check_name == "duplicate_detection"
        for check in reports[1].failures
    )

    duplicate_report = detect_duplicate_records(normalized)
    assert duplicate_report["duplicate_count"] >= 1
