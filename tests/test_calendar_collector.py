from __future__ import annotations

from datetime import datetime, timezone

import json
from pathlib import Path

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.collectors.calendar_collector import CalendarCollector


def test_calendar_registry_loader_parses_basic_fields():
    scheduler = TaskScheduler().initialize()
    collector = CalendarCollector(scheduler=scheduler, logger=None)

    entries = collector.registry_loader.load()
    # At minimum CAL-001..CAL-006 exist.
    assert len(entries) >= 6
    assert any(e.calendar_url.endswith("bls.ics") for e in entries)


def test_parse_ics_in_dry_run_creates_outputs(tmp_path):
    scheduler = TaskScheduler().initialize()

    collector = CalendarCollector(
        scheduler=scheduler,
        storage_root=tmp_path,
        logger=None,
    )

    # dry_run avoids network access
    out = collector.collect(dry_run=True, now=datetime(2026, 7, 12, tzinfo=timezone.utc))

    assert "events" in out
    assert len(out["events"]) >= 1

    # Check output files
    events_json = tmp_path / "events.json"
    normalized = tmp_path / "normalized_events.json"
    diff = tmp_path / "calendar_diff.json"
    validation = tmp_path / "validation.json"

    assert events_json.exists()
    assert normalized.exists()
    assert diff.exists()
    assert validation.exists()

    loaded_events = json.loads(events_json.read_text(encoding="utf-8"))
    assert isinstance(loaded_events, list)
    assert len(loaded_events) >= 1

