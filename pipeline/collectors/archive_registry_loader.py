from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pipeline.utils.base_utils import get_project_root


@dataclass(frozen=True)
class ArchiveRegistryEntry:
    archive_id: str
    program_id: str
    archive_name: str
    archive_url: str
    archive_type: str
    supported_years: List[str]
    enabled: bool
    implementation_status: str


class ArchiveRegistryLoader:
    """Parse ARCHIVE_REGISTRY.md blocks into ArchiveRegistryEntry objects.

    The registry markdown follows a consistent template with blocks introduced by:
    
      ## ARCHIVE-001
      ## ARCHIVE-002
      ...

    Each field is represented as a key followed by a fenced code block.
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
            / "ARCHIVE_REGISTRY.md"
        )
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Archive registry not found: {self.docs_path}")

    def _pick_block_value(self, body: str, key: str) -> str:
        # key can be followed by a ```text ... ``` fenced block.
        m = re.search(
            rf"{re.escape(key)}\s*\n\s*```(?:text)?\s*\n(.*?)\n```",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return (m.group(1).strip() if m else "")

    def _pick_supported_years(self, body: str) -> List[str]:
        raw = self._pick_block_value(body, "Supported Years")
        if not raw:
            return []
        # Supported years format uses arrows; normalize by splitting on arrows.
        parts = [p.strip() for p in re.split(r"→|->", raw) if p.strip()]
        return parts

    def load(self) -> List[ArchiveRegistryEntry]:
        text = self.docs_path.read_text(encoding="utf-8")

        # Split by each "## ARCHIVE-XXX" block.
        blocks = re.split(r"\n##\s+(ARCHIVE-\d+)\n", text)
        if len(blocks) < 3:
            return []

        entries: List[ArchiveRegistryEntry] = []
        it = iter(blocks[1:])
        for archive_id in it:
            body = next(it)

            program_id = self._pick_block_value(body, "Program")
            archive_name = self._pick_block_value(body, "Archive")
            # In current template, Archive Name is under "Archive Name" for master index,
            # but for program archives the field uses "Archive".
            if not archive_name:
                archive_name = self._pick_block_value(body, "Archive Name")

            archive_url = self._pick_block_value(body, "Archive URL")
            archive_type = self._pick_block_value(body, "Archive Type")
            supported_years = self._pick_supported_years(body)

            enabled = True
            implementation_status = self._pick_block_value(body, "implementation_status")

            # For program archive entries, ARCHIVE_TYPE might be empty; keep empty.

            entries.append(
                ArchiveRegistryEntry(
                    archive_id=archive_id.strip(),
                    program_id=program_id,
                    archive_name=archive_name,
                    archive_url=archive_url,
                    archive_type=archive_type,
                    supported_years=supported_years,
                    enabled=enabled,
                    implementation_status=implementation_status,
                )
            )

        return entries

