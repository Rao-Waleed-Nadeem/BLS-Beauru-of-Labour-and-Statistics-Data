from __future__ import annotations

from datetime import datetime, timezone
import json

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.collectors.archive_collector import ArchiveCollector


def test_archive_registry_loader_parses_basic_fields():
    scheduler = TaskScheduler().initialize()
    collector = ArchiveCollector(scheduler=scheduler, logger=None)

    entries = collector.registry_loader.load()
    assert len(entries) >= 6
    # Should include at least one program archive with a program_id
    assert any(e.program_id for e in entries)


def test_archive_collector_dry_run_creates_outputs(tmp_path):
    scheduler = TaskScheduler().initialize()

    collector = ArchiveCollector(
        scheduler=scheduler,
        storage_root=tmp_path,
        logger=None,
    )

    out = collector.collect(
        dry_run=True,
        now=datetime(2026, 7, 12, tzinfo=timezone.utc),
    )

    assert out["releases_discovered"] >= 1 or out["releases_discovered"] == 0

    # Walk expected shape: raw/<program>/<year>/...
    program_dir = None
    for p in (tmp_path / "program").glob("*"):
        program_dir = p
        break
    assert program_dir is not None

    year_dir = None
    for y in program_dir.glob("*"):
        year_dir = y
        break
    assert year_dir is not None

    assert (year_dir / "archive_index.html").exists()
    assert (year_dir / "release_urls.json").exists()
    assert (year_dir / "metadata.json").exists()
    assert (year_dir / "validation.json").exists()
    assert (year_dir / "collector.log").exists()

    release_urls = json.loads((year_dir / "release_urls.json").read_text(encoding="utf-8"))
    assert isinstance(release_urls, dict)
    assert "release_urls" in release_urls
    assert isinstance(release_urls["release_urls"], list)


def test_archive_collector_dry_run_enqueues_html_jobs(tmp_path):
    scheduler = TaskScheduler().initialize()

    collector = ArchiveCollector(
        scheduler=scheduler,
        storage_root=tmp_path,
        logger=None,
    )

    collector.collect(
        dry_run=True,
        now=datetime(2026, 7, 12, tzinfo=timezone.utc),
    )

    pending = scheduler.get_pending_jobs()
    assert any(j.collector == "html" for j in pending)

