from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    program_id: str
    release_name: str
    reference_period: str
    release_date: str  # ISO date YYYY-MM-DD
    release_time: str  # HH:MM
    timezone: str
    source_url: str
    status: str = "scheduled"


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_ics_events(
    ics_text: str,
    *,
    source_url: str,
    program_id: str = "",
    timezone_name: str = "America/New_York",
) -> List[CalendarEvent]:
    """Parse a BLS release schedule ICS.

    This implementation focuses on the subset we need for scheduling:
    DTSTART/DTEND and a human-readable SUMMARY.

    If an entry can't be parsed, it is skipped.
    """

    # Normalize line endings
    text = ics_text.replace("\r\n", "\n").replace("\r", "\n")

    events: List[CalendarEvent] = []
    blocks = re.split(r"BEGIN:VEVENT\s*\n", text)
    for blk in blocks:
        if "END:VEVENT" not in blk:
            continue

        # DTSTART line can be like: DTSTART:20260712T083000Z or DTSTART;TZID=...:...
        dt_match = re.search(r"^DTSTART[^:]*:(.+)$", blk, flags=re.MULTILINE)
        summary_match = re.search(r"^SUMMARY:(.+)$", blk, flags=re.MULTILINE)
        dtstart = dt_match.group(1).strip() if dt_match else ""
        summary = summary_match.group(1).strip() if summary_match else ""

        if not dtstart:
            continue

        # Convert DTSTART to a UTC datetime if Z present.
        # Support formats:
        #  - YYYYMMDDTHHMMSSZ
        #  - YYYYMMDDTHHMMZ
        #  - YYYYMMDD
        try:
            if dtstart.endswith("Z"):
                raw = dtstart[:-1]
                if len(raw) == 15:  # YYYYMMDDTHHMMSS
                    dt = datetime.strptime(raw, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                elif len(raw) == 13:  # YYYYMMDDTHHMM
                    dt = datetime.strptime(raw, "%Y%m%dT%H%M").replace(tzinfo=timezone.utc)
                else:
                    continue
            else:
                # If no timezone marker, we treat it as local to timezone_name.
                # For scheduling in this milestone, we only need date/time strings.
                raw = dtstart
                if len(raw) == 15:
                    dt_local = datetime.strptime(raw, "%Y%m%dT%H%M%S")
                elif len(raw) == 13:
                    dt_local = datetime.strptime(raw, "%Y%m%dT%H%M")
                elif len(raw) == 8:
                    dt_local = datetime.strptime(raw, "%Y%m%d")
                else:
                    continue
                # Fake UTC conversion by using date/time components.
                dt = dt_local.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        release_date = dt.date().isoformat()
        release_time = dt.strftime("%H:%M")

        release_name = summary or "BLS Release"
        reference_period = ""  # Not reliably present in ICS subset

        event_key = f"{program_id}|{reference_period}|{release_date}|{release_time}|{release_name}|{source_url}"
        event_id = _sha256(event_key)

        events.append(
            CalendarEvent(
                event_id=event_id,
                program_id=program_id,
                release_name=release_name,
                reference_period=reference_period,
                release_date=release_date,
                release_time=release_time,
                timezone=timezone_name,
                source_url=source_url,
                status="scheduled",
            )
        )

    return events

