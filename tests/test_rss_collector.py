from __future__ import annotations

from datetime import datetime, timezone
import json

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.collectors.rss_collector import RSSCollector


def test_rss_registry_loader_parses_enabled_feeds():
    scheduler = TaskScheduler().initialize()
    collector = RSSCollector(scheduler=scheduler, logger=None)

    entries = collector.registry_loader.load()
    assert len(entries) >= 1
    # At least one feed should be enabled from the template (RSS-001)
    assert any(e.enabled for e in entries)


def test_rss_collector_dry_run_creates_outputs(tmp_path):
    scheduler = TaskScheduler().initialize()
    collector = RSSCollector(scheduler=scheduler, storage_root=tmp_path, logger=None)

    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    out = collector.collect(dry_run=True, now=now)

    assert out["validation"]["status"] in {"ok", "failed"}
    assert "items" in out

    # Ensure raw snapshot + metadata exist for every enabled feed.
    entries = [e for e in collector.registry_loader.load() if e.enabled]
    assert len(entries) >= 1

    for entry in entries:
        feed_dir = tmp_path / entry.feed_name / entry.feed_id
        assert feed_dir.exists()

        xml_path = feed_dir / f"{now.year}" / f"{now.month:02d}" / "rss.xml"
        metadata_path = feed_dir / "metadata.json"
        dup_path = feed_dir / "duplicate_index.json"

        assert xml_path.exists()
        assert metadata_path.exists()
        assert dup_path.exists()

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["feed_id"] == entry.feed_id
        assert metadata["item_count"] >= metadata["new_items"]


def test_rss_collector_duplicate_detection_idempotent(tmp_path):
    scheduler = TaskScheduler().initialize()
    collector = RSSCollector(scheduler=scheduler, storage_root=tmp_path, logger=None)

    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    out1 = collector.collect(dry_run=True, now=now)
    first_new = out1["new_items"]

    # Run again at same time; should not create new_items.
    out2 = collector.collect(dry_run=True, now=now)
    second_new = out2["new_items"]

    assert first_new >= 0
    assert second_new == 0


def test_rss_collector_triggers_jobs_only_for_new_items(tmp_path):
    scheduler = TaskScheduler().initialize()
    collector = RSSCollector(scheduler=scheduler, storage_root=tmp_path, logger=None)

    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    out1 = collector.collect(dry_run=True, now=now)
    jobs_after_first = scheduler.queue.pending_count()

    # Trigger count should be new_items * 3 (html/pdf/api) for this milestone.
    assert jobs_after_first == out1["new_items"] * 3

    # Second run should add no new jobs.
    collector.collect(dry_run=True, now=now)
    jobs_after_second = scheduler.queue.pending_count()

    assert jobs_after_second == jobs_after_first

