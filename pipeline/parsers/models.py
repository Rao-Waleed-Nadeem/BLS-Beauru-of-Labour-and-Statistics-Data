from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

@dataclass
class MetadataSchema:
    uuid: str
    dataset_id: str
    program_id: str
    series_id: str
    collector: str
    collector_version: str
    schema_version: str
    source_type: str
    collection_timestamp: str
    validation_status: str
    checksum: str
    normalization_timestamp: str = ""

@dataclass
class ReleaseSchema:
    release_id: str
    release_name: str
    program_name: str
    dataset_name: str
    release_datetime: str
    reference_period: str = ""
    timezone: str = ""
    headline: str = ""
    summary: str = ""
    revision: bool = False
    status: str = "published"

@dataclass
class EventSchema:
    event_id: str
    event_type: str
    importance: str
    country: str = "United States"
    currency: str = "USD"
    asset_class: str = "Macro"
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    previous_value: Optional[str] = None
    revised_value: Optional[str] = None
    surprise_value: Optional[str] = None
    surprise_percent: Optional[str] = None

@dataclass
class APISchema:
    series_id: str
    series_title: str
    frequency: str
    year: str
    period: str
    period_name: str
    value: str
    latest: bool = False
    footnotes: List[str] = field(default_factory=list)

@dataclass
class HTMLSchema:
    page_url: str
    page_title: str
    publication_datetime: str
    headline: str
    summary: str
    main_content: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    links: List[str] = field(default_factory=list)

@dataclass
class PDFSchema:
    pdf_url: str
    filename: str
    sha256: str
    text: str
    pages: int = 0
    tables: List[Dict[str, Any]] = field(default_factory=list)
    figures: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AttachmentSchema:
    pdf_files: List[str] = field(default_factory=list)
    html_files: List[str] = field(default_factory=list)
    charts: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    spreadsheets: List[str] = field(default_factory=list)

@dataclass
class RelationshipSchema:
    program_id: str = ""
    dataset_id: str = ""
    series_id: str = ""
    calendar_id: str = ""
    archive_id: str = ""
    rss_feed_id: str = ""

@dataclass
class UnifiedObject:
    metadata: MetadataSchema
    release: Optional[ReleaseSchema] = None
    event: Optional[EventSchema] = None
    api: Optional[APISchema] = None
    html: Optional[HTMLSchema] = None
    pdf: Optional[PDFSchema] = None
    attachments: Optional[AttachmentSchema] = None
    relationships: Optional[RelationshipSchema] = None

