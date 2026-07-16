import json
from datetime import datetime, timezone
from pathlib import Path

from BLS.pipeline.collectors.pdf_collector import PDFCollector

class DummyScheduler:
    def __init__(self):
        self.jobs = []
        
    def enqueue_collection_job(self, **kwargs):
        self.jobs.append(kwargs)

def test_pdf_collector_dry_run(tmp_path: Path):
    scheduler = DummyScheduler()
    storage_root = tmp_path / "raw"
    processed_root = tmp_path / "processed"
    
    collector = PDFCollector(
        scheduler=scheduler,
        storage_root=storage_root,
        processed_root=processed_root,
    )
    
    now = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    
    # Run collector in dry_run mode
    res = collector.collect(
        source_url="https://www.bls.gov/bls/news-release/cpi_2024_01.pdf",
        program_id="cpi",
        dataset_id="cpi_data",
        now=now,
        dry_run=True,
    )
    
    assert res["validation"]["status"] == "ok"
    assert res["duplicate"] is False
    assert "sha256" in res
    
    year_dir = storage_root / "cpi" / "2026"
    processed_dir = processed_root / "cpi"
    
    pdf_filename = "2026-07-15_cpi.pdf"
    text_filename = "2026-07-15_cpi.txt"
    
    # Check created files
    assert (year_dir / pdf_filename).exists()
    assert (processed_dir / text_filename).exists()
    assert (year_dir / "metadata.json").exists()
    assert (year_dir / "validation.json").exists()
    assert (year_dir / "collector.log").exists()
    assert (year_dir / "duplicate_index.json").exists()
    
    # Check extracted text
    text_content = (processed_dir / text_filename).read_text(encoding="utf-8")
    assert text_content == ""
    
    # Check scheduler jobs
    assert len(scheduler.jobs) == 1
    job = scheduler.jobs[0]
    assert job["collector"] == "pdf_parser"
    assert job["program_id"] == "cpi"
    assert job["source_url"] == str(processed_dir / text_filename)
    
    # Run again to test duplicate detection
    res_dup = collector.collect(
        source_url="https://www.bls.gov/bls/news-release/cpi_2024_01.pdf",
        program_id="cpi",
        dataset_id="cpi_data",
        now=now,
        dry_run=True,
    )
    
    assert res_dup["duplicate"] is True
    assert res_dup["validation"]["status"] == "ok"
    
    # Read validation payload
    val_payload = json.loads((year_dir / "validation.json").read_text(encoding="utf-8"))
    assert val_payload["duplicate"] is True
    assert val_payload["reason"] == "duplicate"
    
    # No new jobs queued
    assert len(scheduler.jobs) == 1
