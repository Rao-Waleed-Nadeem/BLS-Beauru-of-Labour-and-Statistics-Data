"""
pdf_parser.py — M13 PDF Parser

Converts raw PDF bytes (or pre-extracted text) into a UnifiedObject
containing a fully populated PDFSchema.

Input contract (raw_data):
    bytes  — raw PDF file bytes (parser performs text extraction internally)
    str    — pre-extracted UTF-8 text (skips extraction step)
    Path   — path to a .pdf or .txt file (parser reads and processes it)

The parser:
  1. Accepts raw PDF bytes, a pre-extracted text string, or a file path.
  2. Extracts full text and page count using pypdf (when bytes are given).
  3. Parses structured tables from the extracted text (lightweight heuristic).
  4. Computes SHA-256 of the original PDF bytes when available.
  5. Builds MetadataSchema from the provided metadata dict.
  6. Returns a UnifiedObject with metadata + pdf fields populated.

Rules (from PDF_REGISTRY.md):
  - Never modify extracted values.
  - Preserve numeric values, dates, tables, and paragraph order.
  - Output is UTF-8.
  - sha256 is the primary key for deduplication.
"""

import hashlib
import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pypdf

from pipeline.parsers.base_parser import BaseParser
from pipeline.parsers.models import (
    MetadataSchema,
    PDFSchema,
    UnifiedObject,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    """Return hex-encoded SHA-256 of *data*."""
    return hashlib.sha256(data).hexdigest()


def _extract_from_bytes(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Use pypdf to extract full text and page count from raw PDF bytes.

    Returns
    -------
    dict with keys:
        text  : str  — concatenated page text, pages separated by double newline
        pages : int  — total page count
    """
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    pages = len(reader.pages)
    extracted: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            extracted.append(page_text)
    return {
        "text": "\n\n".join(extracted),
        "pages": pages,
    }


def _parse_tables_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Lightweight heuristic table parser for BLS news-release text.

    BLS PDFs present tables as rows of whitespace-separated columns.
    A "table" is detected as a consecutive block of lines where every
    line contains two or more numeric tokens.  The first such line that
    also contains alphabetic tokens is treated as the header row.

    Returns a list of table dicts matching the PDFSchema.tables contract::

        [
            {
                "headers": ["Category", "Value", ...],
                "rows":    [["Food", "1.2", ...], ...]
            },
            ...
        ]

    Rules from PDF_REGISTRY.md:
        - Preserve numeric values exactly as they appear.
        - Do not reformat numbers.
        - Do not modify extracted values.
    """
    tables: List[Dict[str, Any]] = []
    if not text:
        return tables

    lines = text.splitlines()
    current_table: Optional[Dict[str, Any]] = None

    # A line is "data-like" if it contains at least 2 whitespace-separated
    # tokens that look like numbers (int, float, percent, or signed value).
    _num_re = re.compile(r"^[+\-]?\d[\d,]*\.?\d*%?$")

    def _is_data_line(line: str) -> bool:
        tokens = line.split()
        numeric_count = sum(1 for t in tokens if _num_re.match(t))
        return len(tokens) >= 2 and numeric_count >= 2

    def _split_row(line: str) -> List[str]:
        """Split a raw text row on runs of 2+ spaces (column separator)."""
        # BLS PDFs use multiple spaces to visually align columns.
        parts = re.split(r"  +", line.strip())
        return [p.strip() for p in parts if p.strip()]

    for line in lines:
        stripped = line.strip()

        if _is_data_line(stripped):
            if current_table is None:
                current_table = {"headers": [], "rows": []}
            row = _split_row(stripped)
            current_table["rows"].append(row)
        else:
            # Non-data line — flush current table if it has rows
            if current_table is not None and current_table["rows"]:
                tables.append(current_table)
                current_table = None

    # Flush any table still open at end-of-text
    if current_table is not None and current_table["rows"]:
        tables.append(current_table)

    return tables


# ---------------------------------------------------------------------------
# PDFParser
# ---------------------------------------------------------------------------

class PDFParser(BaseParser):
    """
    Parser for BLS PDF news releases (M13).

    Accepts raw PDF bytes, pre-extracted text, or a filesystem path.
    Produces a UnifiedObject with ``metadata`` and ``pdf`` fields populated.

    Usage::

        parser = PDFParser()

        # From raw bytes (most common — direct output from PDFCollector)
        unified = parser.parse(pdf_bytes, metadata)

        # From a pre-extracted text file path (enqueued by PDFCollector)
        from pathlib import Path
        unified = parser.parse(Path("/storage/processed/bls/pdf_text/cpi/2026-07-18_cpi.txt"), metadata)

        # From a plain text string
        unified = parser.parse("CPI increased 0.2 percent...", metadata)
    """

    def parse(self, raw_data: Any, metadata: Dict[str, Any]) -> UnifiedObject:
        """
        Parse PDF content into a UnifiedObject.

        Parameters
        ----------
        raw_data : bytes | str | Path
            - ``bytes`` — raw PDF bytes; text is extracted internally.
            - ``str``   — pre-extracted UTF-8 text.
            - ``Path``  — filesystem path to a ``.pdf`` or ``.txt`` file.
        metadata : dict
            Collection metadata dict.  Expected keys (all optional with
            safe defaults):

            ============  =====================================================
            Key           Description
            ============  =====================================================
            uuid          Globally unique ID for this record
            dataset_id    Dataset identifier (e.g. ``BLS-DATASET-001``)
            program_id    Program identifier (e.g. ``BLS-PROGRAM-001``)
            series_id     Series identifier
            collector     Collector name
            collector_version  Collector version string
            schema_version     Schema version string
            source_type   Must be ``PDF``
            collection_timestamp  ISO-8601 UTC timestamp
            normalization_timestamp  ISO-8601 UTC timestamp
            validation_status  ``PASS`` or ``FAIL``
            checksum      SHA-256 of the *original* raw payload
            source_url    URL the PDF was downloaded from
            filename      Original filename (e.g. ``2026-07-18_cpi.pdf``)
            ============  =====================================================

        Returns
        -------
        UnifiedObject
            Populated with ``metadata`` and ``pdf`` fields.

        Raises
        ------
        ValueError
            If ``raw_data`` is of an unsupported type, or if the PDF
            cannot be read.
        """
        pdf_bytes: Optional[bytes] = None
        text: str = ""
        pages: int = 0

        # ------------------------------------------------------------------
        # 1. Normalise input
        # ------------------------------------------------------------------
        if isinstance(raw_data, bytes):
            # Validate PDF signature (%PDF-…)
            if not raw_data.startswith(b"%PDF"):
                raise ValueError(
                    "raw_data bytes do not start with a valid PDF signature (%PDF)."
                )
            pdf_bytes = raw_data
            extraction = _extract_from_bytes(pdf_bytes)
            text = extraction["text"]
            pages = extraction["pages"]

        elif isinstance(raw_data, Path) or (
            isinstance(raw_data, str) and (
                raw_data.endswith(".pdf") or raw_data.endswith(".txt")
            )
        ):
            # Treat as filesystem path
            path = Path(raw_data)
            if not path.exists():
                raise ValueError(f"Path does not exist: {path}")

            if path.suffix.lower() == ".pdf":
                pdf_bytes = path.read_bytes()
                extraction = _extract_from_bytes(pdf_bytes)
                text = extraction["text"]
                pages = extraction["pages"]
            elif path.suffix.lower() == ".txt":
                text = path.read_text(encoding="utf-8")
                # Page count not available from pre-extracted text
                pages = 0
            else:
                raise ValueError(
                    f"Unsupported file extension: {path.suffix}. "
                    "Expected .pdf or .txt."
                )

        elif isinstance(raw_data, str):
            # Pre-extracted plain text
            text = raw_data
            pages = 0

        else:
            raise ValueError(
                f"Unsupported raw_data type: {type(raw_data).__name__}. "
                "Expected bytes, str, or Path."
            )

        # ------------------------------------------------------------------
        # 2. Compute SHA-256
        # ------------------------------------------------------------------
        if pdf_bytes is not None:
            sha256 = _sha256_bytes(pdf_bytes)
        else:
            # Fall back to checksum from metadata (set by collector), or
            # compute from text as a last resort.
            sha256 = (
                metadata.get("checksum")
                or _sha256_bytes(text.encode("utf-8"))
            )

        # ------------------------------------------------------------------
        # 3. Parse tables from extracted text
        # ------------------------------------------------------------------
        tables = _parse_tables_from_text(text)

        # ------------------------------------------------------------------
        # 4. Build MetadataSchema
        # ------------------------------------------------------------------
        meta = MetadataSchema(
            uuid=metadata.get("uuid", ""),
            dataset_id=metadata.get("dataset_id", ""),
            program_id=metadata.get("program_id", ""),
            series_id=metadata.get("series_id", ""),
            collector=metadata.get("collector", "pdf_parser"),
            collector_version=metadata.get("collector_version", "1.0"),
            schema_version=metadata.get("schema_version", "1.0"),
            source_type=metadata.get("source_type", "PDF"),
            collection_timestamp=metadata.get("collection_timestamp", ""),
            normalization_timestamp=metadata.get("normalization_timestamp", ""),
            validation_status=metadata.get("validation_status", "PASS"),
            checksum=sha256,
        )

        # ------------------------------------------------------------------
        # 5. Build PDFSchema
        # ------------------------------------------------------------------
        pdf_schema = PDFSchema(
            pdf_url=metadata.get("source_url", ""),
            filename=metadata.get("filename", ""),
            sha256=sha256,
            text=text,
            pages=pages,
            tables=tables,
            figures=[],  # Figure extraction requires image processing (out of scope for M13)
        )

        # ------------------------------------------------------------------
        # 6. Return UnifiedObject
        # ------------------------------------------------------------------
        return UnifiedObject(
            metadata=meta,
            pdf=pdf_schema,
        )
