from __future__ import annotations

from datetime import datetime, timezone
import json

from BLS.pipeline.scheduler.scheduler import TaskScheduler
from BLS.pipeline.collectors.html_collector import HTMLCollector


def test_html_registry_loader_parses_enabled_pages():
    scheduler = TaskScheduler().initialize()
    collector = HTMLCollector(scheduler=scheduler, logger=None)

    entries = collector.registry_loader.load()
    assert len(entries) >= 1
    assert any(e.enabled for e in entries)


def test_html_collector_dry_run_creates_outputs(tmp_path):
    scheduler = TaskScheduler().initialize()
    collector = HTMLCollector(scheduler=scheduler, storage_root=tmp_path, logger=None)

    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    out = collector.collect(dry_run=True, now=now)

    assert out["validation"]["status"] in {"ok", "failed", "unknown"}

    entries = [e for e in collector.registry_loader.load() if e.enabled]
    assert len(entries) >= 1

    # Verify required outputs exist for enabled pages.
    for entry in entries:
        program_id = entry.program_id or "unknown_program"
        year_dir = tmp_path / program_id / str(now.year)

        assert year_dir.exists()
        assert (year_dir / "release.html").exists()
        assert (year_dir / "metadata.json").exists()
        assert (year_dir / "validation.json").exists()
        assert (year_dir / "discovered_links.json").exists()
        assert (year_dir / "collector.log").exists()

        metadata = json.loads((year_dir / "metadata.json").read_text(encoding="utf-8"))
        assert metadata["html_id"] == entry.html_id


def test_html_collector_duplicate_detection_idempotent(tmp_path):
    scheduler = TaskScheduler().initialize()
    collector = HTMLCollector(scheduler=scheduler, storage_root=tmp_path, logger=None)

    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    out1 = collector.collect(dry_run=True, now=now)
    out2 = collector.collect(dry_run=True, now=now)

    # In dry-run deterministic content uses same SHA so second run should find duplicates.
    assert out1["new_pages"] >= 0
    assert out2["new_pages"] == 0


def test_html_collector_triggers_jobs_only_for_new_pages(tmp_path):
    scheduler = TaskScheduler().initialize()
    collector = HTMLCollector(scheduler=scheduler, storage_root=tmp_path, logger=None)

    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    out1 = collector.collect(dry_run=True, now=now)
    jobs_after_first = scheduler.queue.pending_count()

    # Dry-run HTML discovery emits one pdf and one archive link;
    # collector enqueues up to 3 pdf jobs + up to 3 html jobs, but limited by discovered list.
    # With our deterministic dry-run HTML, expected jobs are 2 (1 pdf + 1 html) per enabled entry (if not duplicate).
    # First run should schedule exactly that.
    enabled_entries = [e for e in collector.registry_loader.load() if e.enabled]
    assert jobs_after_first == len(enabled_entries) * 2 * 1  # new_pages computed per entry; deterministic content unique per entry

    collector.collect(dry_run=True, now=now)
    jobs_after_second = scheduler.queue.pending_count()
    assert jobs_after_second == jobs_after_first

