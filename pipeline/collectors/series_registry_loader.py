from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from BLS.pipeline.utils.base_utils import get_project_root


@dataclass(frozen=True)
class SeriesRegistryEntry:
    entry_id: str
    series_id: str
    title: str
    program_id: str
    dataset_id: str
    priority: str
    collection_method: str
    storage_path: str
    api_payload: Dict[str, Any]
    enabled: bool
    implementation_status: str


class SeriesRegistryLoader:
    """Parse SERIES_REGISTRY.md blocks into SeriesRegistryEntry objects."""

    def __init__(self, docs_path: Optional[object] = None) -> None:
        root = get_project_root()
        if docs_path is not None:
            self.docs_path = docs_path  # type: ignore[assignment]
        else:
            self.docs_path = (
                root
                / "Docs"
                / "BLS"
                / "02_Website_Architecture_and_URL_Inventory"
                / "Registery"
                / "SERIES_REGISTRY.md"
            )

        if not self.docs_path.exists():
            raise FileNotFoundError(f"Series registry not found: {self.docs_path}")

    def _pick_block_value(self, body: str, key: str) -> str:
        m = re.search(
            rf"{re.escape(key)}\s*\n\s*```(?:text)?\s*\n(.*?)\n```",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return m.group(1).strip() if m else ""

    def _pick_json_block(self, body: str, key: str) -> Dict[str, Any]:
        m = re.search(
            rf"{re.escape(key)}\s*\n\s*```(?:json)?\s*\n(.*?)\n```",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if m:
            try:
                payload = json.loads(m.group(1).strip())
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass
        return {}

    def load(self) -> List[SeriesRegistryEntry]:
        text = self.docs_path.read_text(encoding="utf-8")

        blocks = re.split(r"\n##\s+(SERIES-\d+)\n", text)
        if len(blocks) < 3:
            return []

        entries: List[SeriesRegistryEntry] = []
        it = iter(blocks[1:])
        for entry_id in it:
            body = next(it)

            series_id = self._pick_block_value(body, "Series ID")
            title = self._pick_block_value(body, "Title")
            program_id = self._pick_block_value(body, "Program")
            dataset_id = self._pick_block_value(body, "Dataset")
            priority = self._pick_block_value(body, "Priority")
            collection_method = self._pick_block_value(body, "Collection Method")
            storage_path = self._pick_block_value(body, "Storage")
            api_payload = self._pick_json_block(body, "API Payload")
            implementation_status = self._pick_block_value(body, "Status")

            enabled = True
            if implementation_status:
                if re.search(r"disabled", implementation_status, flags=re.IGNORECASE):
                    enabled = False

            entries.append(
                SeriesRegistryEntry(
                    entry_id=entry_id.strip(),
                    series_id=series_id,
                    title=title,
                    program_id=program_id,
                    dataset_id=dataset_id,
                    priority=priority,
                    collection_method=collection_method,
                    storage_path=storage_path,
                    api_payload=api_payload,
                    enabled=enabled,
                    implementation_status=implementation_status,
                )
            )

        return entries
