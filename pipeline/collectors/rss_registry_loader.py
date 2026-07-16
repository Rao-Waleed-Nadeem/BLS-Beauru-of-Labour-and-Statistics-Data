from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from BLS.pipeline.utils.base_utils import get_project_root


@dataclass(frozen=True)
class RSSRegistryEntry:
    feed_id: str
    feed_name: str
    feed_url: str
    program_id: str
    dataset_id: str
    priority: str
    poll_interval_minutes: int
    enabled: bool
    output_directory: str
    implementation_status: str


class RSSRegistryLoader:
    """Parse RSS_REGISTRY.md blocks into RSSRegistryEntry objects.

    This project uses markdown templates with fenced code blocks for each field.
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
            / "RSS_REGISTRY.md"
        )
        if not self.docs_path.exists():
            raise FileNotFoundError(f"RSS registry not found: {self.docs_path}")

    def _pick_block_value(self, body: str, key: str) -> str:
        m = re.search(
            rf"{re.escape(key)}\s*\n\s*```(?:text)?\s*\n(.*?)\n```",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return (m.group(1).strip() if m else "")

    def _pick_int(self, body: str, key: str, default: int) -> int:
        raw = self._pick_block_value(body, key)
        if not raw:
            return default
        raw = raw.strip()
        # e.g. "5 Minutes"
        m = re.search(r"(\d+)", raw)
        return int(m.group(1)) if m else default

    def load(self) -> List[RSSRegistryEntry]:
        text = self.docs_path.read_text(encoding="utf-8")
        blocks = re.split(r"\n##\s+(RSS-\d+)\n", text)
        if len(blocks) < 3:
            return []

        entries: List[RSSRegistryEntry] = []
        it = iter(blocks[1:])
        for feed_id in it:
            body = next(it)

            feed_name = self._pick_block_value(body, "Feed Name")
            feed_url = self._pick_block_value(body, "Feed URL")
            program_id = self._pick_block_value(body, "Program")

            dataset_id = self._pick_block_value(body, "dataset_id")
            if not dataset_id:
                # Not present in current template; allow empty.
                dataset_id = ""

            priority = self._pick_block_value(body, "Priority")

            poll_interval_minutes = self._pick_int(
                body, "Polling Interval", default=5
            )

            output_directory = self._pick_block_value(body, "Output Directory")

            implementation_status = self._pick_block_value(body, "Status")

            # Enabled defaults to True unless Status says disabled.
            enabled = True
            if implementation_status:
                if re.search(r"disabled", implementation_status, flags=re.IGNORECASE):
                    enabled = False

            entries.append(
                RSSRegistryEntry(
                    feed_id=feed_id.strip(),
                    feed_name=feed_name,
                    feed_url=feed_url,
                    program_id=program_id,
                    dataset_id=dataset_id,
                    priority=priority,
                    poll_interval_minutes=poll_interval_minutes,
                    enabled=enabled,
                    output_directory=output_directory,
                    implementation_status=implementation_status,
                )
            )

        return entries

