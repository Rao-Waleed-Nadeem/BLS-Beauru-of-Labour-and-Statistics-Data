import json
from typing import Any, Dict, List
from bs4 import BeautifulSoup

from pipeline.parsers.base_parser import BaseParser
from pipeline.parsers.models import (
    HTMLSchema,
    MetadataSchema,
    UnifiedObject,
)

class HTMLParser(BaseParser):
    """
    Parser for BLS HTML pages.
    Extracts structured content from raw HTML and populates a UnifiedObject.
    """

    def parse(self, raw_data: Any, metadata: Dict[str, Any]) -> UnifiedObject:
        """
        Parses BLS HTML content into a UnifiedObject.
        """
        if isinstance(raw_data, bytes):
            # Attempt to decode, fallback to bs4's own encoding detection
            try:
                html_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                html_str = raw_data
        else:
            html_str = str(raw_data)

        soup = BeautifulSoup(html_str, "html.parser")
        
        # 1. Metadata Schema
        meta = MetadataSchema(
            uuid=metadata.get("uuid", ""),
            dataset_id=metadata.get("dataset_id", ""),
            program_id=metadata.get("program_id", ""),
            series_id=metadata.get("series_id", ""),
            collector=metadata.get("collector", "html_parser"),
            collector_version=metadata.get("collector_version", "1.0"),
            schema_version=metadata.get("schema_version", "1.0"),
            source_type=metadata.get("source_type", "HTML"),
            collection_timestamp=metadata.get("collection_timestamp", ""),
            validation_status=metadata.get("validation_status", "PASS"),
            checksum=metadata.get("checksum", ""),
            normalization_timestamp=metadata.get("normalization_timestamp", "")
        )
        
        # 2. HTML Extraction
        page_title = soup.title.string.strip() if soup.title and soup.title.string else None
        
        # publication_datetime: Try meta tags first, fallback to time elements
        publication_datetime = None
        pub_meta = soup.find("meta", {"name": "DC.date"}) or soup.find("meta", {"property": "article:published_time"})
        if pub_meta and pub_meta.get("content"):
            publication_datetime = pub_meta["content"]
        if not publication_datetime:
            time_tag = soup.find("time")
            if time_tag and time_tag.get("datetime"):
                publication_datetime = time_tag["datetime"]
        
        # headline: H1 is generally the headline
        headline = None
        h1_tag = soup.find("h1")
        if h1_tag:
            headline = h1_tag.get_text(separator=" ", strip=True)
            
        # summary: first substantive paragraph
        summary = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 50:  # arbitrary length to skip UI snippets
                summary = text
                break
                
        # main_content: the bulk text, stripped of UI
        main_content_div = soup.find("div", id="bodytext") or soup.find("main") or soup.body
        main_content = main_content_div.get_text(separator="\n", strip=True) if main_content_div else None
        
        # links
        links = []
        for a in soup.find_all("a", href=True):
            links.append(a["href"])
            
        # tables
        tables = []
        for table in soup.find_all("table"):
            table_data = {"headers": [], "rows": []}
            # Headers
            thead = table.find("thead")
            if thead:
                headers = [th.get_text(strip=True) for th in thead.find_all("th")]
                table_data["headers"] = headers
            elif table.find("th"):
                 # Fallback if no thead
                 headers = [th.get_text(strip=True) for th in table.find_all("th")]
                 table_data["headers"] = headers
                 
            # Rows
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                # Skip header rows in body
                if tr.find("th") and not tr.find("td"):
                    continue
                row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if row:
                    table_data["rows"].append(row)
            tables.append(table_data)
            
        # charts
        charts = []
        for img in soup.find_all("img"):
            src = img.get("src")
            alt = img.get("alt", "")
            if src and ("chart" in src.lower() or "graph" in src.lower()):
                charts.append({"src": src, "alt": alt})

        html_schema = HTMLSchema(
            page_url=metadata.get("source_url", ""),
            page_title=page_title,
            publication_datetime=publication_datetime,
            headline=headline,
            summary=summary,
            main_content=main_content,
            tables=tables,
            charts=charts,
            links=list(set(links))  # Deduplicate links
        )
        
        return UnifiedObject(
            metadata=meta,
            html=html_schema
        )
