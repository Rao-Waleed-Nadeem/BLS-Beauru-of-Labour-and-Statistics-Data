from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from pipeline.utils.base_utils import get_project_root


@dataclass(frozen=True)
class PDFRegistryEntry:
    pdf_id: str
    document_id: str
    program_id: str
    dataset_id: str
    document_name: str
    discovery: str
    priority: str
    enabled: bool
    implementation_status: str


class PDFRegistryLoader:
    """Parse PDF_REGISTRY.md blocks into PDFRegistryEntry objects."""

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
                / "PDF_REGISTRY.md"
            )

        if not self.docs_path.exists():
            raise FileNotFoundError(f"PDF registry not found: {self.docs_path}")

    def _pick_block_value(self, body: str, key: str) -> str:
        # Matches patterns like `Key\n\n```text\nvalue\n``` ` or without extra newlines.
        m = re.search(
            rf"{re.escape(key)}\s*\n\s*```(?:text)?\s*\n(.*?)\n```",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return (m.group(1).strip() if m else "")

    def load(self) -> List[PDFRegistryEntry]:
        text = self.docs_path.read_text(encoding="utf-8")

        blocks = re.split(r"\n##\s+(PDF-\d+)\n", text)
        if len(blocks) < 3:
            return []

        entries: List[PDFRegistryEntry] = []
        it = iter(blocks[1:])
        for pdf_id in it:
            body = next(it)

            document_id = self._pick_block_value(body, "Document ID")
            program_id = self._pick_block_value(body, "Program")
            dataset_id = self._pick_block_value(body, "Dataset")
            document_name = self._pick_block_value(body, "Document")
            discovery = self._pick_block_value(body, "Discovery")
            priority = self._pick_block_value(body, "Priority")
            implementation_status = self._pick_block_value(body, "Status")

            # Fallback if no block found for Document (in some examples it's just plain text, but looking at PDF_REGISTRY it's in text blocks or plain text)
            if not document_name:
                m_doc = re.search(r"##.*?\n\s*(?:```text\n)?(.*?)(?:\n```)?\n\s*Program", "\n## " + pdf_id + "\n" + body, flags=re.IGNORECASE | re.DOTALL)
                if m_doc:
                    # simplistic fallback
                    document_name = m_doc.group(1).strip()

            enabled = True
            if implementation_status:
                if re.search(r"disabled", implementation_status, flags=re.IGNORECASE):
                    enabled = False

            entries.append(
                PDFRegistryEntry(
                    pdf_id=pdf_id.strip(),
                    document_id=document_id,
                    program_id=program_id,
                    dataset_id=dataset_id,
                    document_name=document_name,
                    discovery=discovery,
                    priority=priority,
                    enabled=enabled,
                    implementation_status=implementation_status,
                )
            )

        return entries
