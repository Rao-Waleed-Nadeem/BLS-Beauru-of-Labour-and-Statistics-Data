from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from BLS.pipeline.utils.base_utils import get_project_root


@dataclass(frozen=True)
class HTMLRegistryEntry:
    html_id: str
    program_id: str
    dataset_id: str
    page_name: str
    page_url: str
    page_type: str
    priority: str
    discovery_source: str
    parser: str
    output_directory: str
    enabled: bool
    implementation_status: str


class HTMLRegistryLoader:
    """Parse HTML_REGISTRY.md blocks into HTMLRegistryEntry objects."""

    def __init__(self, docs_path: Optional[object] = None) -> None:
        root = get_project_root()
        # Keep signature generic to match other loaders; tests won't pass custom docs_path.
        if docs_path is not None:
            self.docs_path = docs_path  # type: ignore[assignment]
        else:
            self.docs_path = (
                root
                / "Docs"
                / "BLS"
                / "02_Website_Architecture_and_URL_Inventory"
                / "Registery"
                / "HTML_REGISTRY.md"
            )

        if not self.docs_path.exists():
            raise FileNotFoundError(f"HTML registry not found: {self.docs_path}")

    def _pick_block_value(self, body: str, key: str) -> str:
        # Example key occurrences: "URL\n```text\n...\n```" or inline.
        m = re.search(
            rf"{re.escape(key)}\s*\n\s*```(?:text)?\s*\n(.*?)\n```",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return (m.group(1).strip() if m else "")

    def load(self) -> List[HTMLRegistryEntry]:
        text = self.docs_path.read_text(encoding="utf-8")

        blocks = re.split(r"\n##\s+(HTML-\d+)\n", text)
        if len(blocks) < 3:
            return []

        entries: List[HTMLRegistryEntry] = []
        it = iter(blocks[1:])
        for html_id in it:
            body = next(it)

            program_id = self._pick_block_value(body, "Program")
            dataset_id = self._pick_block_value(body, "dataset_id")

            if not dataset_id:
                dataset_id = ""

            page_name = self._pick_block_value(body, "Page")
            page_url = self._pick_block_value(body, "URL")
            page_type = self._pick_block_value(body, "Type")
            priority = self._pick_block_value(body, "Priority")
            discovery_source = self._pick_block_value(body, "Discovery")
            parser = self._pick_block_value(body, "Parser")
            output_directory = self._pick_block_value(body, "Output Directory")
            implementation_status = self._pick_block_value(body, "Status")

            # Enabled defaults to True unless implementation_status says disabled.
            enabled = True
            if implementation_status:
                if re.search(r"disabled", implementation_status, flags=re.IGNORECASE):
                    enabled = False

            entries.append(
                HTMLRegistryEntry(
                    html_id=html_id.strip(),
                    program_id=program_id.strip(),
                    dataset_id=dataset_id.strip(),
                    page_name=page_name,
                    page_url=page_url,
                    page_type=page_type,
                    priority=priority,
                    discovery_source=discovery_source,
                    parser=parser,
                    output_directory=output_directory,
                    enabled=enabled,
                    implementation_status=implementation_status,
                )
            )

        return entries

