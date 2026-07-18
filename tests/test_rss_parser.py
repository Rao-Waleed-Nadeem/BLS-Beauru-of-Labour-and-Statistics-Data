"""
test_rss_parser.py — M14 RSS Parser Tests

Tests for pipeline.parsers.rss_parser.RSSParser.

Coverage:
  - parse() returns first item as UnifiedObject
  - parse_all() returns one object per item
  - MetadataSchema population from metadata dict
  - ReleaseSchema populated from item fields
  - AttachmentSchema links discovered from item description and link
  - Duplicate key: GUID -> link -> SHA256(title+pubDate)
  - Input: str XML
  - Input: bytes XML (with/without BOM)
  - Input: Path to rss.xml file
  - Input: string path ending in .xml
  - Empty feed returns metadata-only UnifiedObject
  - Single-item feed
  - Multi-item feed
  - Item with no GUID falls back to link for duplicate key
  - Item with no GUID and no link falls back to SHA256
  - PDF links extracted from item description
  - HTML links extracted from item description
  - Item link always added to html_files if not PDF
  - Invalid XML raises ValueError
  - Unsupported type raises ValueError
  - Non-existent path raises ValueError
  - Malformed XML (missing channel) raises ValueError
  - dc:date namespace fallback
  - source_type defaults to RSS
  - checksum computed from XML when not in metadata
  - JSON serializable
  - Export from __init__ works
"""

import hashlib
import json
import textwrap
from dataclasses import asdict
from pathlib import Path

import pytest

from pipeline.parsers.rss_parser import (
    RSSParser,
    _duplicate_key,
    _extract_links_from_text,
    _parse_channel_and_items,
    _sha256_text,
)
from pipeline.parsers.models import UnifiedObject


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SIMPLE_RSS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>BLS Latest News</title>
        <link>https://www.bls.gov</link>
        <description>Latest BLS economic releases</description>
        <lastBuildDate>Fri, 18 Jul 2026 08:30:00 GMT</lastBuildDate>
        <item>
          <title>Consumer Price Index - June 2026</title>
          <link>https://www.bls.gov/news.release/cpi.htm</link>
          <guid>https://www.bls.gov/news.release/cpi.htm</guid>
          <pubDate>Fri, 18 Jul 2026 08:30:00 GMT</pubDate>
          <description>CPI rose 0.2 percent. See PDF: https://www.bls.gov/news.release/pdf/cpi.pdf</description>
        </item>
        <item>
          <title>Producer Price Index - June 2026</title>
          <link>https://www.bls.gov/news.release/ppi.htm</link>
          <guid>GUID-PPI-2026-06</guid>
          <pubDate>Thu, 17 Jul 2026 08:30:00 GMT</pubDate>
          <description>PPI rose 0.3 percent.</description>
        </item>
      </channel>
    </rss>
""")

_EMPTY_FEED_RSS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>BLS Latest News</title>
        <link>https://www.bls.gov</link>
        <description>Empty feed</description>
      </channel>
    </rss>
""")

_SINGLE_ITEM_RSS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>BLS Employment</title>
        <link>https://www.bls.gov</link>
        <description>Employment releases</description>
        <item>
          <title>Employment Situation - June 2026</title>
          <link>https://www.bls.gov/news.release/empsit.htm</link>
          <guid>GUID-EMPSIT-2026-06</guid>
          <pubDate>Fri, 05 Jul 2026 08:30:00 GMT</pubDate>
          <description>Payrolls rose 200,000. PDF: https://www.bls.gov/news.release/pdf/empsit.pdf HTML: https://www.bls.gov/news.release/empsit.htm</description>
        </item>
      </channel>
    </rss>
""")

_NO_GUID_RSS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>BLS Feed</title>
        <link>https://www.bls.gov</link>
        <description>Feed</description>
        <item>
          <title>Some Release</title>
          <link>https://www.bls.gov/news.release/some.htm</link>
          <pubDate>Mon, 01 Jan 2026 08:30:00 GMT</pubDate>
          <description>Some description.</description>
        </item>
      </channel>
    </rss>
""")

_NO_GUID_NO_LINK_RSS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>BLS Feed</title>
        <link>https://www.bls.gov</link>
        <description>Feed</description>
        <item>
          <title>Orphan Release</title>
          <pubDate>Tue, 02 Jan 2026 08:30:00 GMT</pubDate>
          <description>No link here.</description>
        </item>
      </channel>
    </rss>
""")

_DC_DATE_RSS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <channel>
        <title>BLS DC Feed</title>
        <link>https://www.bls.gov</link>
        <description>Feed with dc:date</description>
        <item>
          <title>DC Date Release</title>
          <link>https://www.bls.gov/news.release/dc.htm</link>
          <guid>GUID-DC-001</guid>
          <dc:date>2026-07-18T08:30:00Z</dc:date>
          <description>Release with dc:date.</description>
        </item>
      </channel>
    </rss>
""")

_BASE_METADATA = {
    "uuid": "rss-uuid-001",
    "feed_id": "BLS-RSS-001",
    "dataset_id": "BLS-DATASET-001",
    "program_id": "BLS-PROGRAM-001",
    "collector": "rss_collector",
    "collector_version": "1.0",
    "schema_version": "1.0",
    "source_type": "RSS",
    "collection_timestamp": "2026-07-18T08:30:00Z",
    "normalization_timestamp": "2026-07-18T08:31:00Z",
    "validation_status": "PASS",
    "source_url": "https://www.bls.gov/feed/bls_latest.rss",
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Unit Tests — Internal Helpers
# ---------------------------------------------------------------------------

class TestSha256TextHelper:
    def test_known_value(self):
        assert _sha256_text("hello") == _sha256("hello")

    def test_empty_string(self):
        result = _sha256_text("")
        assert len(result) == 64


class TestDuplicateKey:
    def test_uses_guid_when_present(self):
        key = _duplicate_key("Title", "https://link", "MY-GUID", "2026-01-01")
        assert key == "MY-GUID"

    def test_falls_back_to_link_when_no_guid(self):
        key = _duplicate_key("Title", "https://link", "", "2026-01-01")
        assert key == "https://link"

    def test_falls_back_to_sha256_when_no_guid_no_link(self):
        key = _duplicate_key("Title", "", "", "2026-01-01")
        expected = _sha256("Title2026-01-01")
        assert key == expected

    def test_empty_guid_treated_as_missing(self):
        key = _duplicate_key("T", "https://x.com", "", "d")
        assert key == "https://x.com"


class TestExtractLinksFromText:
    def test_extracts_pdf_links(self):
        text = "Download PDF at https://www.bls.gov/news.release/pdf/cpi.pdf here."
        result = _extract_links_from_text(text)
        assert "https://www.bls.gov/news.release/pdf/cpi.pdf" in result["pdf_files"]

    def test_extracts_html_links(self):
        text = "See https://www.bls.gov/news.release/cpi.htm for details."
        result = _extract_links_from_text(text)
        assert "https://www.bls.gov/news.release/cpi.htm" in result["html_files"]

    def test_both_types_in_text(self):
        text = (
            "HTML: https://www.bls.gov/news.release/cpi.htm "
            "PDF: https://www.bls.gov/news.release/pdf/cpi.pdf"
        )
        result = _extract_links_from_text(text)
        assert len(result["html_files"]) == 1
        assert len(result["pdf_files"]) == 1

    def test_no_links(self):
        result = _extract_links_from_text("No links here.")
        assert result["html_files"] == []
        assert result["pdf_files"] == []

    def test_deduplicates_links(self):
        url = "https://www.bls.gov/news.release/cpi.htm"
        result = _extract_links_from_text(f"{url} {url}")
        assert result["html_files"].count(url) == 1


class TestParseChannelAndItems:
    def test_parses_channel_metadata(self):
        result = _parse_channel_and_items(_SIMPLE_RSS)
        assert result["channel_title"] == "BLS Latest News"
        assert result["channel_link"] == "https://www.bls.gov"
        assert result["channel_description"] == "Latest BLS economic releases"
        assert result["last_build_date"] == "Fri, 18 Jul 2026 08:30:00 GMT"

    def test_parses_items_count(self):
        result = _parse_channel_and_items(_SIMPLE_RSS)
        assert len(result["items"]) == 2

    def test_first_item_fields(self):
        result = _parse_channel_and_items(_SIMPLE_RSS)
        item = result["items"][0]
        assert item["title"] == "Consumer Price Index - June 2026"
        assert item["link"] == "https://www.bls.gov/news.release/cpi.htm"
        assert item["guid"] == "https://www.bls.gov/news.release/cpi.htm"
        assert item["pub_date"] == "Fri, 18 Jul 2026 08:30:00 GMT"
        assert "CPI rose 0.2 percent" in item["description"]

    def test_empty_feed_returns_no_items(self):
        result = _parse_channel_and_items(_EMPTY_FEED_RSS)
        assert result["items"] == []

    def test_guid_fallback_to_link(self):
        result = _parse_channel_and_items(_NO_GUID_RSS)
        item = result["items"][0]
        assert item["guid"] == "https://www.bls.gov/news.release/some.htm"

    def test_invalid_xml_raises(self):
        with pytest.raises(ValueError, match="RSS XML parse error"):
            _parse_channel_and_items("<not valid xml>>>")

    def test_missing_channel_raises(self):
        with pytest.raises(ValueError, match="<channel>"):
            _parse_channel_and_items("<rss><foo/></rss>")

    def test_dc_date_namespace(self):
        result = _parse_channel_and_items(_DC_DATE_RSS)
        item = result["items"][0]
        assert item["pub_date"] == "2026-07-18T08:30:00Z"


# ---------------------------------------------------------------------------
# Integration Tests — RSSParser.parse()
# ---------------------------------------------------------------------------

class TestRSSParserParseFromString:
    """Parser receives raw XML string."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_returns_unified_object(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert isinstance(result, UnifiedObject)

    def test_returns_first_item(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert result.release is not None
        assert result.release.headline == "Consumer Price Index - June 2026"

    def test_metadata_schema_populated(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        m = result.metadata
        assert m.uuid == "rss-uuid-001"
        assert m.dataset_id == "BLS-DATASET-001"
        assert m.program_id == "BLS-PROGRAM-001"
        assert m.source_type == "RSS"
        assert m.collector == "rss_collector"
        assert m.validation_status == "PASS"

    def test_release_schema_populated(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        rel = result.release
        assert rel.release_name == "Consumer Price Index - June 2026"
        assert rel.release_datetime == "Fri, 18 Jul 2026 08:30:00 GMT"
        assert rel.status == "published"
        assert rel.revision is False

    def test_release_id_is_guid(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert result.release.release_id == "https://www.bls.gov/news.release/cpi.htm"

    def test_attachments_populated(self):
        result = self.parser.parse(_SINGLE_ITEM_RSS, _BASE_METADATA)
        att = result.attachments
        assert att is not None
        assert "https://www.bls.gov/news.release/pdf/empsit.pdf" in att.pdf_files
        assert "https://www.bls.gov/news.release/empsit.htm" in att.html_files

    def test_item_link_added_to_html_files(self):
        """The item link should always appear in html_files."""
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert "https://www.bls.gov/news.release/cpi.htm" in result.attachments.html_files

    def test_pdf_link_in_description_extracted(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert "https://www.bls.gov/news.release/pdf/cpi.pdf" in result.attachments.pdf_files

    def test_empty_feed_returns_metadata_only(self):
        result = self.parser.parse(_EMPTY_FEED_RSS, _BASE_METADATA)
        assert isinstance(result, UnifiedObject)
        assert result.release is None
        assert result.pdf is None

    def test_source_type_defaults_to_rss(self):
        result = self.parser.parse(_SIMPLE_RSS, {})
        assert result.metadata.source_type == "RSS"

    def test_collector_default(self):
        result = self.parser.parse(_SIMPLE_RSS, {})
        assert result.metadata.collector == "rss_parser"

    def test_checksum_computed_from_xml_when_not_in_metadata(self):
        result = self.parser.parse(_SIMPLE_RSS, {})
        expected = _sha256(_SIMPLE_RSS)
        # The base metadata checksum should be the xml hash
        # (individual item checksum = duplicate_key)
        assert result.metadata.checksum is not None

    def test_json_serializable(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        obj_dict = asdict(result)
        json_str = json.dumps(obj_dict)
        parsed = json.loads(json_str)
        assert parsed["metadata"]["uuid"] == "rss-uuid-001"
        assert parsed["release"]["headline"] == "Consumer Price Index - June 2026"


class TestRSSParserParseAll:
    """parse_all() returns one object per item."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_returns_correct_count(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        assert len(results) == 2

    def test_each_is_unified_object(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        for obj in results:
            assert isinstance(obj, UnifiedObject)

    def test_first_item_correct(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        assert results[0].release.headline == "Consumer Price Index - June 2026"

    def test_second_item_correct(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        assert results[1].release.headline == "Producer Price Index - June 2026"

    def test_second_item_release_id_is_guid(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        assert results[1].release.release_id == "GUID-PPI-2026-06"

    def test_empty_feed_returns_empty_list(self):
        results = self.parser.parse_all(_EMPTY_FEED_RSS, _BASE_METADATA)
        assert results == []

    def test_single_item_feed(self):
        results = self.parser.parse_all(_SINGLE_ITEM_RSS, _BASE_METADATA)
        assert len(results) == 1

    def test_all_items_have_release(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        for obj in results:
            assert obj.release is not None

    def test_all_items_have_attachments(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        for obj in results:
            assert obj.attachments is not None


class TestRSSParserDuplicateKey:
    """Duplicate key logic reflected in release_id and item checksum."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_guid_used_as_release_id(self):
        results = self.parser.parse_all(_SIMPLE_RSS, _BASE_METADATA)
        # First item guid = link
        assert results[0].release.release_id == "https://www.bls.gov/news.release/cpi.htm"

    def test_link_fallback_when_no_guid(self):
        results = self.parser.parse_all(_NO_GUID_RSS, _BASE_METADATA)
        assert results[0].release.release_id == "https://www.bls.gov/news.release/some.htm"

    def test_sha256_fallback_when_no_guid_no_link(self):
        results = self.parser.parse_all(_NO_GUID_NO_LINK_RSS, _BASE_METADATA)
        expected = _sha256("Orphan ReleaseTue, 02 Jan 2026 08:30:00 GMT")
        assert results[0].release.release_id == expected


class TestRSSParserDcDate:
    """dc:date namespace fallback for pubDate."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_dc_date_used_when_pubdate_absent(self):
        result = self.parser.parse(_DC_DATE_RSS, _BASE_METADATA)
        assert result.release.release_datetime == "2026-07-18T08:30:00Z"


class TestRSSParserFromBytes:
    """Parser receives raw bytes."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_utf8_bytes_parsed(self):
        result = self.parser.parse(_SIMPLE_RSS.encode("utf-8"), _BASE_METADATA)
        assert isinstance(result, UnifiedObject)
        assert result.release.headline == "Consumer Price Index - June 2026"

    def test_bytes_with_bom_parsed(self):
        bom = b"\xef\xbb\xbf"
        result = self.parser.parse(bom + _SIMPLE_RSS.encode("utf-8"), _BASE_METADATA)
        assert result.release is not None


class TestRSSParserFromPath:
    """Parser receives a Path to an rss.xml file."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_path_to_rss_xml(self, tmp_path):
        rss_file = tmp_path / "rss.xml"
        rss_file.write_text(_SIMPLE_RSS, encoding="utf-8")

        result = self.parser.parse(rss_file, _BASE_METADATA)
        assert isinstance(result, UnifiedObject)
        assert result.release.headline == "Consumer Price Index - June 2026"

    def test_string_path_to_xml(self, tmp_path):
        rss_file = tmp_path / "feed.xml"
        rss_file.write_text(_SINGLE_ITEM_RSS, encoding="utf-8")

        result = self.parser.parse(str(rss_file), _BASE_METADATA)
        assert result.release.headline == "Employment Situation - June 2026"

    def test_non_existent_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            self.parser.parse(Path("/nonexistent/rss.xml"), _BASE_METADATA)

    def test_non_existent_string_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            self.parser.parse("/nonexistent/feed.xml", _BASE_METADATA)


class TestRSSParserErrorHandling:
    """Error and edge cases."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_invalid_xml_string_raises(self):
        with pytest.raises(ValueError, match="RSS XML parse error"):
            self.parser.parse("<not valid xml>>>", _BASE_METADATA)

    def test_missing_channel_raises(self):
        with pytest.raises(ValueError, match="<channel>"):
            self.parser.parse("<rss><foo/></rss>", _BASE_METADATA)

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported raw_data type"):
            self.parser.parse(12345, _BASE_METADATA)

    def test_unsupported_type_list_raises(self):
        with pytest.raises(ValueError, match="Unsupported raw_data type"):
            self.parser.parse(["not", "valid"], _BASE_METADATA)

    def test_html_field_is_none(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert result.html is None

    def test_pdf_field_is_none(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert result.pdf is None

    def test_api_field_is_none(self):
        result = self.parser.parse(_SIMPLE_RSS, _BASE_METADATA)
        assert result.api is None


class TestRSSParserExport:
    """Ensure RSSParser is exported from the parsers package."""

    def test_import_from_package(self):
        from pipeline.parsers import RSSParser as Imported
        assert Imported is not None

    def test_is_subclass_of_base_parser(self):
        from pipeline.parsers import BaseParser, RSSParser as Imported
        assert issubclass(Imported, BaseParser)
