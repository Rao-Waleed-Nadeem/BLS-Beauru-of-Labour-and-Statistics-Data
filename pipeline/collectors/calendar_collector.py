from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from pipeline.collectors.calendar_parser import CalendarEvent, parse_ics_events
from pipeline.collectors.calendar_registry_loader import CalendarRegistryLoader
from pipeline.config.loader import ConfigLoader
from pipeline.scheduler.models import Job
from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.utils.base_utils import get_project_root, setup_logger


class CalendarCollector:
    """Calendar Collector (M05).

    Responsibilities per CALENDAR_REGISTRY:
    - Download official calendar(s)
    - Extract events
    - Store raw artifacts + normalized events
    - Detect changes vs previous snapshot
    - Generate scheduler queue items
    """

    def __init__(
        self,
        *,
        scheduler: TaskScheduler,
        registry_loader: Optional[CalendarRegistryLoader] = None,
        config_loader: Optional[ConfigLoader] = None,
        storage_root: Optional[Path] = None,
        logger=None,
    ) -> None:
        self.scheduler = scheduler
        self.registry_loader = registry_loader or CalendarRegistryLoader()
        self.config_loader = config_loader or ConfigLoader()
        self.logger = logger or setup_logger("calendar_collector")

        root = get_project_root()
        self.storage_root = (
            storage_root
            if storage_root is not None
            else root / "storage" / "raw" / "bls" / "calendar"
        )
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _download_text(self, url: str) -> str:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _read_json_if_exists(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def collect(self, *, now: Optional[datetime] = None, dry_run: bool = False) -> Dict[str, Any]:
        now_utc = now or datetime.now(timezone.utc)

        registry_entries = [e for e in self.registry_loader.load() if e.enabled]
        ics_entries = [e for e in registry_entries if e.calendar_url.lower().endswith(".ics")]
        html_entries = [e for e in registry_entries if not e.calendar_url.lower().endswith(".ics")]

        results: Dict[str, Any] = {
            "downloaded": [],
            "events": [],
            "validation": {"status": "unknown"},
        }

        events: List[CalendarEvent] = []
        validation: Dict[str, Any] = {"ics": {}}  # required output shape

        # Download + store ICS
        for entry in ics_entries:
            ics_path = self.storage_root / "calendar.ics"
            events_json_path = self.storage_root / "events.json"
            try:
                if dry_run:
                    ics_text = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20260712T083000Z\nSUMMARY:Test Release\nEND:VEVENT\nEND:VCALENDAR\n"
                else:
                    ics_text = self._download_text(entry.calendar_url)

                ics_path.write_text(ics_text, encoding="utf-8")
                parsed = parse_ics_events(
                    ics_text,
                    source_url=entry.calendar_url,
                    program_id=entry.program_id,
                    timezone_name=entry.timezone,
                )
                events.extend(parsed)

                results["downloaded"].append({"url": entry.calendar_url, "type": "ics"})
                validation["ics"] = {"status": "ok", "event_count": len(parsed)}

            except Exception as e:
                validation["ics"] = {"status": "failed", "error": str(e)}
                self.logger.exception("ICS download/parse failed")

        # Best-effort download HTML (non-blocking; per CALENDAR_REGISTRY)
        for entry in html_entries:
            html_path = self.storage_root / "calendar.html"
            try:
                if dry_run:
                    html_text = "<html></html>"
                else:
                    html_text = self._download_text(entry.calendar_url)
                # Preserve only latest master snapshot to required filename.
                html_path.write_text(html_text, encoding="utf-8")
                results["downloaded"].append({"url": entry.calendar_url, "type": "html"})
            except Exception as e:
                self.logger.exception("HTML download failed")
                results.setdefault("html_failures", []).append({"url": entry.calendar_url, "error": str(e)})

        # Raw events.json
        events_payload = [asdict(ev) for ev in events]
        events_json_path.write_text(json.dumps(events_payload, indent=2), encoding="utf-8")

        # normalized_events.json (milestone normalization step)
        normalized_path = self.storage_root / "normalized_events.json"
        normalized_payload = {
            "generated_at": now_utc.isoformat(),
            "events": events_payload,
        }
        normalized_path.write_text(json.dumps(normalized_payload, indent=2), encoding="utf-8")

        # Diff vs previous snapshot
        prev_path = self.storage_root / "normalized_events_prev.json"
        prev_payload = self._read_json_if_exists(prev_path) or {"events": []}
        prev_events = prev_payload.get("events", []) if isinstance(prev_payload, dict) else []
        prev_ids = {e.get("event_id") for e in prev_events}
        new_ids = {e.get("event_id") for e in events_payload}

        added = [e for e in events_payload if e.get("event_id") not in prev_ids]
        removed = [e for e in prev_events if e.get("event_id") not in new_ids]

        diff_path = self.storage_root / "calendar_diff.json"
        diff_payload = {
            "generated_at": now_utc.isoformat(),
            "added_events": [e.get("event_id") for e in added],
            "removed_events": [e.get("event_id") for e in removed],
            "counts": {"added": len(added), "removed": len(removed)},
        }
        diff_path.write_text(json.dumps(diff_payload, indent=2), encoding="utf-8")

        # Save validation.json and collector.log
        validation_path = self.storage_root / "validation.json"
        validation_payload = {
            "generated_at": now_utc.isoformat(),
            "validation": "calendar_collector",
            "event_count": len(events_payload),
            "details": validation,
        }
        validation_path.write_text(json.dumps(validation_payload, indent=2), encoding="utf-8")

        collector_log_path = self.storage_root / "collector.log"
        with open(collector_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{now_utc.isoformat()}] downloaded_types={[d['type'] for d in results['downloaded']] if results.get('downloaded') else []} events={len(events_payload)}\n")

        # Queue generation: one job per event
        # Scheduler dispatch expects collector names to match; we will schedule html/pdf/api later from other collectors.
        # For now, we schedule a collection job with collector="calendar_event" to represent downstream scheduling.
        # (This project currently only recognizes scheduler job collectors by config keys.)
        for ev in events_payload:
            # create a job at the release datetime represented by ev.release_date/time (interpreted UTC)
            scheduled_time = datetime.fromisoformat(f"{ev['release_date']}T{ev['release_time']}:00+00:00")
            self.scheduler.enqueue_collection_job(
                collector="calendar_event",
                program_id=ev.get("program_id", ""),
                dataset_id="",
                series_id="",
                source_url=ev.get("source_url", ""),
                priority=0,
                scheduled_time=scheduled_time,
            )

        # update previous snapshot
        prev_path.write_text(json.dumps(normalized_payload, indent=2), encoding="utf-8")

        self.scheduler.dispatch()

        results["events"] = events_payload
        results["validation"] = validation_payload
        results["diff"] = diff_payload
        return results

