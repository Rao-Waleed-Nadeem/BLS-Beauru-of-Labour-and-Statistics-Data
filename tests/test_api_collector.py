import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.collectors.api_collector import APICollector
from pipeline.collectors.series_registry_loader import SeriesRegistryLoader, SeriesRegistryEntry

class DummyScheduler:
    def __init__(self):
        self.jobs = []
        
    def enqueue_collection_job(self, **kwargs):
        self.jobs.append(kwargs)

class DummySeriesLoader(SeriesRegistryLoader):
    def __init__(self):
        pass
        
    def load(self):
        return [
            SeriesRegistryEntry(
                entry_id="SERIES-001",
                series_id="CUUR0000SA0",
                title="CPI-U",
                program_id="cpi",
                dataset_id="cpi_data",
                priority="Critical",
                collection_method="API",
                storage_path="",
                api_payload={"seriesid": ["CUUR0000SA0"], "startyear": "2020", "endyear": "2026"},
                enabled=True,
                implementation_status=""
            ),
            SeriesRegistryEntry(
                entry_id="SERIES-002",
                series_id="CUSR0000SA0",
                title="CPI-U SA",
                program_id="cpi",
                dataset_id="cpi_data",
                priority="High",
                collection_method="API",
                storage_path="",
                api_payload={"seriesid": ["CUSR0000SA0"], "startyear": "2020", "endyear": "2026"},
                enabled=True,
                implementation_status=""
            )
        ]

def test_api_collector_dry_run(tmp_path: Path):
    scheduler = DummyScheduler()
    storage_root = tmp_path / "raw" / "bls" / "api"
    
    loader = DummySeriesLoader()
    
    collector = APICollector(
        scheduler=scheduler,
        registry_loader=loader,
        storage_root=storage_root,
    )
    
    now = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    res = collector.collect(now=now, dry_run=True)
    
    assert res["batches"] == 1
    assert res["success"] == 1
    assert res["failed"] == 0
    
    year_str = "2026"
    timestamp_str = "2026-07-15T12-00-00Z"
    batch_dir = storage_root / year_str / timestamp_str
    
    assert (batch_dir / "request.json").exists()
    assert (batch_dir / "response.json").exists()
    assert (batch_dir / "validation_report.json").exists()
    assert (batch_dir / "request.log").exists()
    
    # Check that jobs were dispatched (one for each series in the batch chunk)
    assert len(scheduler.jobs) == 2
    assert scheduler.jobs[0]["collector"] == "api_parser"
    assert scheduler.jobs[0]["series_id"] == "CUUR0000SA0"
    
    # Check validation payload
    val_payload = json.loads((batch_dir / "validation_report.json").read_text(encoding="utf-8"))
    assert val_payload["status"] == "ok"
    assert val_payload["series_requested"] == 2
    assert val_payload["series_returned"] == 2
