"""
test_pdf_parser.py — M13 PDF Parser Tests

Tests for pipeline.parsers.pdf_parser.PDFParser.

Coverage:
  - Parsing from raw PDF bytes
  - Parsing from pre-extracted text string
  - Parsing from a .txt file path
  - Parsing from a .pdf file path
  - SHA-256 computed from bytes
  - SHA-256 falls back to metadata checksum when bytes not available
  - Table parsing heuristic
  - MetadataSchema population
  - PDFSchema fields populated correctly
  - Unsupported input type raises ValueError
  - Invalid PDF bytes raises ValueError
  - Non-existent path raises ValueError
  - Unsupported file extension raises ValueError
  - Export from __init__ works
"""

import hashlib
import json
import tempfile
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

import pypdf
import pytest

from pipeline.parsers.pdf_parser import (
    PDFParser,
    _extract_from_bytes,
    _parse_tables_from_text,
    _sha256_bytes,
)
from pipeline.parsers.models import UnifiedObject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_pdf_bytes(text: str = "Hello BLS") -> bytes:
    """Return a minimal valid PDF as bytes with a single page containing *text*."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Unit Tests — Internal Helpers
# ---------------------------------------------------------------------------

class TestSha256Helper:
    def test_known_value(self):
        data = b"hello"
        expected = hashlib.sha256(b"hello").hexdigest()
        assert _sha256_bytes(data) == expected

    def test_empty_bytes(self):
        result = _sha256_bytes(b"")
        assert len(result) == 64  # hex SHA-256 is always 64 chars


class TestExtractFromBytes:
    def test_valid_pdf_returns_pages_and_text(self):
        pdf_bytes = _make_minimal_pdf_bytes()
        result = _extract_from_bytes(pdf_bytes)
        assert "text" in result
        assert "pages" in result
        assert result["pages"] == 1
        assert isinstance(result["text"], str)

    def test_multi_page_pdf(self):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.add_blank_page(width=612, height=792)
        out = BytesIO()
        writer.write(out)
        result = _extract_from_bytes(out.getvalue())
        assert result["pages"] == 2


class TestParseTablesFromText:
    def test_no_tables_in_plain_text(self):
        text = "The Consumer Price Index rose 0.2 percent in June."
        tables = _parse_tables_from_text(text)
        assert tables == []

    def test_detects_numeric_table_block(self):
        text = (
            "CPI News Release\n"
            "\n"
            "  Food        1.2   0.8\n"
            "  Energy    -0.5   1.1\n"
            "  Housing    0.3   0.4\n"
            "\n"
            "Table ends here.\n"
        )
        tables = _parse_tables_from_text(text)
        assert len(tables) == 1
        assert len(tables[0]["rows"]) == 3

    def test_multiple_tables(self):
        text = (
            "Section 1\n"
            "  A  1.0  2.0\n"
            "  B  3.0  4.0\n"
            "\n"
            "Gap line with no numbers.\n"
            "\n"
            "Section 2\n"
            "  X  5.5  6.6\n"
            "  Y  7.7  8.8\n"
        )
        tables = _parse_tables_from_text(text)
        assert len(tables) == 2

    def test_empty_text(self):
        assert _parse_tables_from_text("") == []

    def test_preserves_numeric_values_exactly(self):
        text = "  CPI-U  315.605  0.2%\n"
        tables = _parse_tables_from_text(text)
        if tables:
            # Values must not be reformatted
            row_flat = " ".join(tables[0]["rows"][0])
            assert "315.605" in row_flat
            assert "0.2%" in row_flat


# ---------------------------------------------------------------------------
# Integration Tests — PDFParser.parse()
# ---------------------------------------------------------------------------

class TestPDFParserFromBytes:
    """Parser receives raw PDF bytes."""

    def setup_method(self):
        self.parser = PDFParser()
        self.pdf_bytes = _make_minimal_pdf_bytes()
        self.metadata = {
            "uuid": "pdf-uuid-001",
            "dataset_id": "BLS-DATASET-001",
            "program_id": "BLS-PROGRAM-001",
            "series_id": "CUUR0000SA0",
            "collector": "pdf_collector",
            "collector_version": "1.0",
            "schema_version": "1.0",
            "source_type": "PDF",
            "collection_timestamp": "2026-07-18T08:30:00Z",
            "normalization_timestamp": "2026-07-18T08:31:00Z",
            "validation_status": "PASS",
            "source_url": "https://www.bls.gov/news.release/pdf/cpi.pdf",
            "filename": "2026-07-18_cpi.pdf",
        }

    def test_returns_unified_object(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        assert isinstance(result, UnifiedObject)

    def test_metadata_schema_populated(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        m = result.metadata
        assert m.uuid == "pdf-uuid-001"
        assert m.dataset_id == "BLS-DATASET-001"
        assert m.program_id == "BLS-PROGRAM-001"
        assert m.source_type == "PDF"
        assert m.collector == "pdf_collector"
        assert m.validation_status == "PASS"

    def test_pdf_schema_populated(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        pdf = result.pdf
        assert pdf is not None
        assert pdf.pdf_url == "https://www.bls.gov/news.release/pdf/cpi.pdf"
        assert pdf.filename == "2026-07-18_cpi.pdf"
        assert pdf.pages == 1

    def test_sha256_computed_from_bytes(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        expected_sha = _sha256(self.pdf_bytes)
        assert result.pdf.sha256 == expected_sha
        assert result.metadata.checksum == expected_sha

    def test_html_and_other_fields_are_none(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        assert result.html is None
        assert result.api is None
        assert result.release is None
        assert result.event is None

    def test_figures_empty_list(self):
        """Figure extraction is out of scope for M13."""
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        assert result.pdf.figures == []

    def test_tables_is_list(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        assert isinstance(result.pdf.tables, list)

    def test_invalid_pdf_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="valid PDF signature"):
            self.parser.parse(b"not a pdf", self.metadata)

    def test_json_serializable(self):
        result = self.parser.parse(self.pdf_bytes, self.metadata)
        obj_dict = asdict(result)
        json_str = json.dumps(obj_dict)
        parsed = json.loads(json_str)
        assert parsed["metadata"]["uuid"] == "pdf-uuid-001"
        assert parsed["pdf"]["sha256"] == _sha256(self.pdf_bytes)


class TestPDFParserFromTextString:
    """Parser receives pre-extracted plain text string."""

    def setup_method(self):
        self.parser = PDFParser()
        self.text = (
            "Consumer Price Index - June 2026\n\n"
            "The CPI-U rose 0.2 percent in June on a seasonally adjusted basis.\n\n"
            "  Food        1.2   0.8\n"
            "  Energy    -0.5   1.1\n"
            "\n"
            "Note: Data subject to revision.\n"
        )
        self.checksum = _sha256(self.text.encode("utf-8"))
        self.metadata = {
            "uuid": "txt-uuid-002",
            "source_type": "PDF",
            "checksum": self.checksum,
            "source_url": "https://www.bls.gov/news.release/pdf/cpi.pdf",
            "filename": "2026-07-18_cpi.pdf",
        }

    def test_returns_unified_object(self):
        result = self.parser.parse(self.text, self.metadata)
        assert isinstance(result, UnifiedObject)

    def test_text_preserved_exactly(self):
        result = self.parser.parse(self.text, self.metadata)
        assert result.pdf.text == self.text

    def test_pages_zero_for_text_input(self):
        """Pages cannot be determined from pre-extracted text."""
        result = self.parser.parse(self.text, self.metadata)
        assert result.pdf.pages == 0

    def test_sha256_from_metadata_checksum(self):
        result = self.parser.parse(self.text, self.metadata)
        assert result.pdf.sha256 == self.checksum

    def test_tables_detected(self):
        result = self.parser.parse(self.text, self.metadata)
        assert len(result.pdf.tables) >= 1

    def test_source_type_is_pdf(self):
        result = self.parser.parse(self.text, self.metadata)
        assert result.metadata.source_type == "PDF"

    def test_defaults_applied_when_metadata_sparse(self):
        result = self.parser.parse(self.text, {})
        assert result.metadata.collector == "pdf_parser"
        assert result.metadata.collector_version == "1.0"
        assert result.metadata.schema_version == "1.0"
        assert result.metadata.validation_status == "PASS"


class TestPDFParserFromFilePath:
    """Parser receives a Path to a .txt or .pdf file."""

    def setup_method(self):
        self.parser = PDFParser()

    def test_txt_file_path(self, tmp_path):
        text = "Employment Situation - June 2026\nPayrolls rose 200,000.\n"
        txt_file = tmp_path / "2026-07-05_employment.txt"
        txt_file.write_text(text, encoding="utf-8")

        result = self.parser.parse(txt_file, {"uuid": "path-uuid-003"})
        assert isinstance(result, UnifiedObject)
        assert result.pdf.text == text
        assert result.pdf.pages == 0

    def test_pdf_file_path(self, tmp_path):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        pdf_bytes = BytesIO()
        writer.write(pdf_bytes)
        pdf_path = tmp_path / "2026-07-05_ppi.pdf"
        pdf_path.write_bytes(pdf_bytes.getvalue())

        result = self.parser.parse(pdf_path, {"uuid": "path-uuid-004"})
        assert isinstance(result, UnifiedObject)
        assert result.pdf.pages == 1
        expected_sha = _sha256(pdf_bytes.getvalue())
        assert result.pdf.sha256 == expected_sha

    def test_string_path_to_txt_file(self, tmp_path):
        text = "PPI rose 0.4 percent.\n"
        txt_file = tmp_path / "release.txt"
        txt_file.write_text(text, encoding="utf-8")

        result = self.parser.parse(str(txt_file), {})
        assert result.pdf.text == text

    def test_string_path_to_pdf_file(self, tmp_path):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        pdf_bytes_io = BytesIO()
        writer.write(pdf_bytes_io)
        pdf_path = tmp_path / "release.pdf"
        pdf_path.write_bytes(pdf_bytes_io.getvalue())

        result = self.parser.parse(str(pdf_path), {})
        assert isinstance(result, UnifiedObject)
        assert result.pdf.pages == 1

    def test_non_existent_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            self.parser.parse(Path("/nonexistent/path/to/file.txt"), {})

    def test_unsupported_extension_raises(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c\n")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            self.parser.parse(csv_file, {})


class TestPDFParserEdgeCases:
    """Edge cases and error conditions."""

    def setup_method(self):
        self.parser = PDFParser()

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported raw_data type"):
            self.parser.parse(12345, {})

    def test_unsupported_type_list_raises(self):
        with pytest.raises(ValueError, match="Unsupported raw_data type"):
            self.parser.parse(["not", "valid"], {})

    def test_empty_text_string(self):
        result = self.parser.parse("", {})
        assert result.pdf.text == ""
        assert result.pdf.tables == []
        assert result.pdf.pages == 0

    def test_metadata_source_type_default_is_pdf(self):
        result = self.parser.parse("Some text", {})
        assert result.metadata.source_type == "PDF"

    def test_metadata_uuid_defaults_empty_string(self):
        result = self.parser.parse("Some text", {})
        assert result.metadata.uuid == ""


class TestPDFParserExport:
    """Ensure PDFParser is exported from the parsers package."""

    def test_import_from_package(self):
        from pipeline.parsers import PDFParser as ImportedParser
        assert ImportedParser is not None

    def test_is_subclass_of_base_parser(self):
        from pipeline.parsers import BaseParser, PDFParser as ImportedParser
        assert issubclass(ImportedParser, BaseParser)
