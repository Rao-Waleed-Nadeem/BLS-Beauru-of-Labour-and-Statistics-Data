from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from pipeline.incremental import (
    dict_to_unified_object,
    load_processed_objects,
    load_validated_objects,
    run_incremental,
)
from pipeline.parsers.models import APISchema, MetadataSchema, UnifiedObject
from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.storage.storage_manager import StorageManager


def test_dict_to_unified_object_round_trip():
    meta = MetadataSchema(
        uuid="test-uuid",
        dataset_id="cpi",
        program_id="cpi_prog",
        series_id="CUUR0000SA0",
        collector="test",
        collector_version="1.0",
        schema_version="1.0",
        source_type="API",
        collection_timestamp="2026-07-18T08:30:00Z",
        validation_status="PASS",
        checksum="abc",
        normalization_timestamp="2026-07-18T08:31:00Z",
    )
    api = APISchema(
        series_id="CUUR0000SA0",
        series_title="CPI-U",
        frequency="Monthly",
        year="2026",
        period="M06",
        period_name="June",
        value="315.605",
        latest=True,
        footnotes=["Footnote 1"],
    )
    obj = UnifiedObject(metadata=meta, api=api)

    from dataclasses import asdict

    serialized = asdict(obj)

    restored = dict_to_unified_object(serialized)
    assert restored.metadata.uuid == "test-uuid"
    assert restored.api.value == "315.605"
    assert restored.api.footnotes == ["Footnote 1"]


def test_incremental_orchestrator_dry_run(tmp_path):
    # Setup storage root structure
    storage = StorageManager(tmp_path)

    # Run incremental update orchestrator in dry_run mode
    now = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
    res = run_incremental(now=now, dry_run=True, storage_root=str(tmp_path))

    assert res["status"] == "complete"


def test_incremental_processing_loop(tmp_path, monkeypatch):
    # Setup storage
    storage = StorageManager(tmp_path)

    # Create a mock response file
    mock_response = {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 100,
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": "CUUR0000SA0",
                    "catalog": {"series_title": "CPI-U All Items", "frequency": "Monthly"},
                    "data": [
                        {
                            "year": "2026",
                            "period": "M06",
                            "periodName": "June",
                            "value": "315.605",
                            "latest": "true",
                            "footnotes": [{}],
                        }
                    ],
                }
            ]
        },
    }

    response_path = tmp_path / "raw_api_response.json"
    response_path.write_text(json.dumps(mock_response), encoding="utf-8")

    # Initialize scheduler
    scheduler = TaskScheduler().initialize()
    # Clear any default scheduled jobs
    scheduler.queue.clear()

    # Enqueue a parser job
    scheduler.enqueue_collection_job(
        collector="api_parser",
        program_id="cpi",
        dataset_id="cpi_data",
        series_id="CUUR0000SA0",
        source_url=str(response_path),
        priority=0,
    )

    # Patch TaskScheduler.initialize to return our pre-populated scheduler
    monkeypatch.setattr(TaskScheduler, "initialize", lambda self: scheduler)

    # Run incremental
    res = run_incremental(
        now=datetime(2026, 7, 23, tzinfo=timezone.utc),
        dry_run=True,
        storage_root=str(tmp_path),
    )

    # Assert
    assert "cpi_data" in res["updated_datasets"]

    # Verify processed outputs
    processed_dir = tmp_path / "processed" / "bls" / "cpi_data"
    assert (processed_dir / "dataset.json").exists()
    assert (processed_dir / "dataset.csv").exists()

    features_dir = tmp_path / "features" / "bls" / "cpi_data"
    assert (features_dir / "feature_set.json").exists()
    assert (features_dir / "feature_set.csv").exists()
