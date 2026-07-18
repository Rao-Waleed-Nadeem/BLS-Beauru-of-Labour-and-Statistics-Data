"""
rss_parser.py — M14 RSS Parser

Converts raw RSS 2.0 XML into one or more UnifiedObjects.

Each RSS <item> becomes one UnifiedObject populated with:
  - MetadataSchema  — collection provenance
  - ReleaseSchema   — title, link (as release URL), pubDate, channel headline
  - AttachmentSchema — discovered HTML and PDF links within the item

The parser does NOT trigger downstream collectors.
Downstream triggering is the responsibility of the RSS Collector (M07).

Input contract (raw_data):
    str   — RSS 2.0 XML string (UTF-8)
    bytes — RSS 2.0 XML bytes (decoded as UTF-8, with BOM stripped)
    Path  — filesystem path to a saved rss.xml file

Duplicate key (per RSS_REGISTRY.md):
    GUID → else Link → else SHA256(title + pubDate)

Rules (from RSS_REGISTRY.md):
  - Preserve all timestamps exactly as published.
  - Never modify RSS content.
  - Parse RSS 2.0 channel/item structure.
  - Extract: title, link, pubDate, description, guid.
"""

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.parsers.base_parser import BaseParser
from pipeline.parsers.models import (
    AttachmentSchema,
    MetadataSchema,
    ReleaseSchema,
    UnifiedObject,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PDF_PATTERN = re.compile(r'https?://[^\s"\'<>]+\.pdf', re.IGNORECASE)
_HTML_PATTERN = re.compile(r'https?://[^\s"\'<>]+\.htm[l]?', re.IGNORECASE)

# RSS 2.0 namespace (some feeds use dc: namespace for dates)
_DC_NS = "http://purl.org/dc/elements/1.1/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_text(text: str) -> str:
    """Return hex SHA-256 of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _duplicate_key(title: str, link: str, guid: str, pub_date: str) -> str:
    """
    Compute the deduplication key per RSS_REGISTRY.md:
        GUID → else Link → else SHA256(title + pubDate)
    """
    if guid:
        return guid
    if link:
        return link
    return _sha256_text(f"{title}{pub_date}")


def _text(element: Optional[ET.Element]) -> str:
    """Safely get stripped text from an XML element; returns '' if None."""
    if element is None:
        return ""
    return (element.text or "").strip()


def _extract_links_from_text(text: str) -> Dict[str, List[str]]:
    """
    Scan *text* for HTML and PDF URLs.

    Returns
    -------
    dict with keys 'html_files' (list[str]) and 'pdf_files' (list[str]).
    """
    pdf_links = list(dict.fromkeys(_PDF_PATTERN.findall(text)))
    html_links = list(dict.fromkeys(_HTML_PATTERN.findall(text)))
    return {"pdf_files": pdf_links, "html_files": html_links}


def _parse_channel_and_items(
    xml_text: str,
) -> Dict[str, Any]:
    """
    Parse RSS 2.0 XML and return channel metadata plus item list.

    Returns
    -------
    dict with keys:
        channel_title       : str
        channel_link        : str
        channel_description : str
        last_build_date     : str
        items               : list of dicts, each with keys:
                              title, link, guid, pub_date, description
    Raises
    ------
    ValueError
        If the XML is not parseable or lacks required RSS structure.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"RSS XML parse error: {exc}") from exc

    # Support both plain <rss> and namespaced variants
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Invalid RSS XML: <channel> element not found.")

    channel_title = _text(channel.find("title"))
    channel_link = _text(channel.find("link"))
    channel_desc = _text(channel.find("description"))
    last_build = _text(channel.find("lastBuildDate"))

    items: List[Dict[str, str]] = []
    for item_el in channel.findall("item"):
        title = _text(item_el.find("title"))
        link = _text(item_el.find("link"))
        guid_el = item_el.find("guid")
        guid = _text(guid_el) if guid_el is not None else ""
        pub_date = _text(item_el.find("pubDate"))
        # Fallback: dc:date
        if not pub_date:
            dc_date = item_el.find(f"{{{_DC_NS}}}date")
            pub_date = _text(dc_date)
        description = _text(item_el.find("description"))

        if not guid:
            guid = link

        if title or link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "guid": guid,
                    "pub_date": pub_date,
                    "description": description,
                }
            )

    return {
        "channel_title": channel_title,
        "channel_link": channel_link,
        "channel_description": channel_desc,
        "last_build_date": last_build,
        "items": items,
    }


# ---------------------------------------------------------------------------
# RSSParser
# ---------------------------------------------------------------------------

class RSSParser(BaseParser):
    """
    Parser for BLS RSS 2.0 feeds (M14).

    Accepts raw RSS XML as a string, bytes, or a filesystem Path.
    Produces **one UnifiedObject per RSS <item>**.

    Each UnifiedObject is populated with:
      - ``metadata``    — collection provenance
      - ``release``     — item title, link, pubDate mapped to release fields
      - ``attachments`` — HTML and PDF links discovered in the item description

    Usage::

        parser = RSSParser()

        # From raw XML string
        objects = parser.parse(xml_string, metadata)

        # From a saved rss.xml file
        from pathlib import Path
        objects = parser.parse(Path("/storage/raw/bls/rss/latest/2026/07/rss.xml"), metadata)

    .. note::
        The ``parse()`` method signature matches ``BaseParser`` (single return value).
        It returns a ``UnifiedObject`` whose ``release`` field contains the *first*
        item found.  Use ``parse_all()`` to get one object per item.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, raw_data: Any, metadata: Dict[str, Any]) -> UnifiedObject:
        """
        Parse raw RSS XML and return a UnifiedObject for the **first** item.

        Satisfies the ``BaseParser`` contract.  For feeds with multiple items
        use :meth:`parse_all` instead.

        Parameters
        ----------
        raw_data : str | bytes | Path
            RSS 2.0 XML content or path to an rss.xml file.
        metadata : dict
            Collection metadata.  Expected keys (all optional):

            ================  ============================================
            Key               Description
            ================  ============================================
            uuid              Unique ID for this record
            feed_id           RSS feed identifier (e.g. ``BLS-RSS-001``)
            dataset_id        Dataset identifier
            program_id        Program identifier
            collector         Collector name
            collector_version Collector version string
            schema_version    Schema version string
            source_type       Must be ``RSS``
            collection_timestamp  ISO-8601 UTC timestamp
            normalization_timestamp  ISO-8601 UTC timestamp
            validation_status ``PASS`` or ``FAIL``
            checksum          SHA-256 of the raw XML
            source_url        Feed URL
            ================  ============================================

        Returns
        -------
        UnifiedObject
            Populated for the first RSS item found.  If the feed contains no
            items a ``UnifiedObject`` with only ``metadata`` is returned.

        Raises
        ------
        ValueError
            If ``raw_data`` is of an unsupported type or the XML cannot be
            parsed.
        """
        objects = self.parse_all(raw_data, metadata)
        if objects:
            return objects[0]
        # Empty feed — return a metadata-only object
        xml_text = self._normalise_input(raw_data)
        meta = self._build_metadata(metadata, xml_text)
        return UnifiedObject(metadata=meta)

    def parse_all(
        self, raw_data: Any, metadata: Dict[str, Any]
    ) -> List[UnifiedObject]:
        """
        Parse raw RSS XML and return **one UnifiedObject per <item>**.

        Parameters
        ----------
        raw_data : str | bytes | Path
            See :meth:`parse`.
        metadata : dict
            See :meth:`parse`.

        Returns
        -------
        list[UnifiedObject]
            One object per RSS item.  Empty list if the feed has no items.

        Raises
        ------
        ValueError
            Same conditions as :meth:`parse`.
        """
        xml_text = self._normalise_input(raw_data)
        parsed = _parse_channel_and_items(xml_text)

        meta_base = self._build_metadata(metadata, xml_text)

        objects: List[UnifiedObject] = []
        for idx, item in enumerate(parsed["items"]):
            # Build a per-item metadata (UUID may be overridden by caller)
            item_meta = MetadataSchema(
                uuid=metadata.get("uuid", "") if idx == 0 else "",
                dataset_id=meta_base.dataset_id,
                program_id=meta_base.program_id,
                series_id=meta_base.series_id,
                collector=meta_base.collector,
                collector_version=meta_base.collector_version,
                schema_version=meta_base.schema_version,
                source_type=meta_base.source_type,
                collection_timestamp=meta_base.collection_timestamp,
                normalization_timestamp=meta_base.normalization_timestamp,
                validation_status=meta_base.validation_status,
                checksum=_duplicate_key(
                    item["title"],
                    item["link"],
                    item["guid"],
                    item["pub_date"],
                ),
            )

            release = self._build_release(item, parsed, metadata)
            attachments = self._build_attachments(item)

            objects.append(
                UnifiedObject(
                    metadata=item_meta,
                    release=release,
                    attachments=attachments,
                )
            )

        return objects

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_input(raw_data: Any) -> str:
        """
        Convert *raw_data* to a clean UTF-8 XML string.

        Accepts str, bytes, or Path.
        Raises ValueError for unsupported types.
        """
        if isinstance(raw_data, bytes):
            # Strip UTF-8 BOM if present
            data = raw_data.lstrip(b"\xef\xbb\xbf")
            return data.decode("utf-8", errors="replace")

        if isinstance(raw_data, Path):
            if not raw_data.exists():
                raise ValueError(f"Path does not exist: {raw_data}")
            return raw_data.read_text(encoding="utf-8")

        if isinstance(raw_data, str):
            # Could be a path string ending in .xml
            if raw_data.endswith(".xml"):
                p = Path(raw_data)
                if not p.exists():
                    raise ValueError(f"Path does not exist: {raw_data}")
                return p.read_text(encoding="utf-8")
            return raw_data

        raise ValueError(
            f"Unsupported raw_data type: {type(raw_data).__name__}. "
            "Expected str, bytes, or Path."
        )

    @staticmethod
    def _build_metadata(
        metadata: Dict[str, Any], xml_text: str
    ) -> MetadataSchema:
        """Build MetadataSchema from the caller-supplied metadata dict."""
        checksum = metadata.get("checksum") or _sha256_text(xml_text)
        return MetadataSchema(
            uuid=metadata.get("uuid", ""),
            dataset_id=metadata.get("dataset_id", ""),
            program_id=metadata.get("program_id", ""),
            series_id=metadata.get("series_id", ""),
            collector=metadata.get("collector", "rss_parser"),
            collector_version=metadata.get("collector_version", "1.0"),
            schema_version=metadata.get("schema_version", "1.0"),
            source_type=metadata.get("source_type", "RSS"),
            collection_timestamp=metadata.get("collection_timestamp", ""),
            normalization_timestamp=metadata.get("normalization_timestamp", ""),
            validation_status=metadata.get("validation_status", "PASS"),
            checksum=checksum,
        )

    @staticmethod
    def _build_release(
        item: Dict[str, str],
        channel: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> ReleaseSchema:
        """Map a single RSS item to ReleaseSchema."""
        return ReleaseSchema(
            release_id=_duplicate_key(
                item["title"],
                item["link"],
                item["guid"],
                item["pub_date"],
            ),
            release_name=item["title"] or channel.get("channel_title", ""),
            program_name=metadata.get("program_id", ""),
            dataset_name=metadata.get("dataset_id", ""),
            release_datetime=item["pub_date"],
            reference_period="",
            timezone="",
            headline=item["title"],
            summary=item["description"],
            revision=False,
            status="published",
        )

    @staticmethod
    def _build_attachments(item: Dict[str, str]) -> AttachmentSchema:
        """
        Scan item link + description for HTML and PDF URLs.
        The item link itself is always included in html_files if it looks like
        an HTML page.
        """
        search_text = f"{item['link']} {item['description']}"
        found = _extract_links_from_text(search_text)

        # Ensure the item link is in the list (if it is an HTML URL)
        if item["link"] and item["link"] not in found["html_files"]:
            if not item["link"].lower().endswith(".pdf"):
                found["html_files"].insert(0, item["link"])

        return AttachmentSchema(
            pdf_files=found["pdf_files"],
            html_files=found["html_files"],
            charts=[],
            images=[],
            spreadsheets=[],
        )
