from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from BLS.pipeline.utils.base_utils import get_project_root


@dataclass(frozen=True)
class CalendarRegistryEntry:
    calendar_id: str
    calendar_name: str
    calendar_url: str
    calendar_type: str
    timezone: str
    release_time: str
    poll_interval_minutes: int
    enabled: bool
    implementation_status: str
    program_id: str = ""


class CalendarRegistryLoader:
    """Parse CALENDAR_REGISTRY.md blocks into CalendarRegistryEntry objects.

    This is intentionally markdown-pattern based (not a full markdown AST parser)
    because CALENDAR_REGISTRY.md follows a consistent template.
    """

    def __init__(self, docs_path: Optional[Path] = None) -> None:
        root = get_project_root()
        self.docs_path = (
            docs_path
            if docs_path is not None
            else root
            / "Docs"
            / "BLS"
            / "02_Website_Architecture_and_URL_Inventory"
            / "Registery"
            / "CALENDAR_REGISTRY.md"
        )
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Calendar registry not found: {self.docs_path}")

    def load(self) -> List[CalendarRegistryEntry]:
        text = self.docs_path.read_text(encoding="utf-8")

        # Split by each "## CAL-XXX" block.
        blocks = re.split(r"\n##\s+(CAL-\d+)\n", text)
        # re.split includes delimiters; the pattern yields: [preamble, id1, rest1, id2, rest2, ...]
        if len(blocks) < 3:
            return []

        entries: List[CalendarRegistryEntry] = []
        it = iter(blocks[1:])
        for cal_id in it:
            body = next(it)

            def pick(key: str) -> str:
                # Accept either "key\n```text\n...```" or "key\n\n```text\n...```"
                m = re.search(
                    rf"{re.escape(key)}\s*\n\s*```(?:text)?\s*\n(.*?)\n```",
                    body,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                if not m:
                    # fallback: inline code
                    m2 = re.search(
                        rf"{re.escape(key)}\s*\n\s*```text\s*\n(.*?)\n```",
                        body,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    return (m2.group(1).strip() if m2 else "")
                return m.group(1).strip()

            calendar_name = pick("Calendar Name")
            calendar_url = pick("Calendar URL")
            calendar_type = pick("Calendar Type")
            timezone = pick("Timezone")
            release_time = pick("Release Time")
            program_id = pick("Program")
            implementation_status = pick("implementation_status")

            poll_interval_minutes = 60
            # CAL blocks in docs currently don't specify poll interval directly.
            # Use a safe default; scheduler uses interval_minutes per job.
            enabled = True
            # Enabled not explicitly present per entry in docs; default enabled.

            # Calendar type is not present in markdown blocks; infer
            if not calendar_type:
                if calendar_url.lower().endswith(".ics"):
                    calendar_type = "ics"
                else:
                    calendar_type = "html"

            entries.append(
                CalendarRegistryEntry(
                    calendar_id=cal_id.strip(),
                    calendar_name=calendar_name,
                    calendar_url=calendar_url,
                    calendar_type=calendar_type,
                    timezone=timezone or "America/New_York",
                    release_time=release_time,
                    poll_interval_minutes=poll_interval_minutes,
                    enabled=enabled,
                    implementation_status=implementation_status,
                    program_id=program_id,
                )
            )

        return entries

