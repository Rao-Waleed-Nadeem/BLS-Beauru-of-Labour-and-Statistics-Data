# HTML_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS HTML Registry (Implementation Specification)

---

# Purpose

This registry defines how the AI agent must discover, download, parse, validate, version and archive **official BLS HTML pages**.

HTML is the primary source for:

- Release metadata
- Publication timestamps
- Headlines
- Summary paragraphs
- PDF discovery
- Chart discovery
- Related links
- Release navigation

The HTML collector is the entry point for every BLS release pipeline.

---

# Collection Pipeline

```text
Release Calendar / RSS

        │

        ▼

HTML Discovery

        │

        ▼

Download HTML

        │

        ▼

Validate HTTP Response

        │

        ▼

Save Original HTML

        │

        ▼

Extract Metadata

        │

        ▼

Extract Release Links

        │

        ▼

Discover PDF

        │

        ▼

Discover Charts

        │

        ▼

Discover Archives

        │

        ▼

Trigger Remaining Collectors
```

---

# HTML Registry Schema

```json
{
  "html_id": "",
  "program_id": "",
  "dataset_id": "",
  "page_name": "",
  "page_url": "",
  "page_type": "",
  "priority": "",
  "discovery_source": "",
  "parser": "",
  "output_directory": "",
  "enabled": true,
  "implementation_status": ""
}
```

---

# Supported HTML Page Types

| Page Type    | Purpose                             |
| ------------ | ----------------------------------- |
| NEWS_HOME    | Economic News Releases landing page |
| PROGRAM_HOME | Program homepage                    |
| RELEASE_PAGE | Individual release page             |
| ARCHIVE      | Historical releases                 |
| CALENDAR     | Release schedules                   |
| CHART_PAGE   | Charts page                         |
| RELATED_PAGE | Supporting pages                    |

---

# HTML Registry

---

## HTML-001

HTML ID

```text
BLS-HTML-001
```

Page

```text
Economic News Releases
```

URL

```text
https://www.bls.gov/bls/newsrels.htm
```

Type

```text
NEWS_HOME
```

Purpose

```text
Primary discovery page for all current BLS economic releases.
```

Parser

```text
news_release_index_parser
```

Priority

```text
Critical
```

---

## HTML-002

HTML ID

```text
BLS-HTML-002
```

Page

```text
Consumer Price Index
```

Discovery

```text
Program Homepage
```

Parser

```text
program_release_parser
```

Program

```text
BLS-PROGRAM-001
```

---

## HTML-003

```text
Producer Price Index
```

Program

```text
BLS-PROGRAM-002
```

Parser

```text
program_release_parser
```

---

## HTML-004

```text
Employment Situation
```

Program

```text
BLS-PROGRAM-003
```

Parser

```text
employment_parser
```

---

## HTML-005

```text
JOLTS
```

Program

```text
BLS-PROGRAM-004
```

---

## HTML-006

```text
Employment Cost Index
```

Program

```text
BLS-PROGRAM-005
```

---

## HTML-007

```text
Real Earnings
```

Program

```text
BLS-PROGRAM-006
```

---

## HTML-008

```text
Import & Export Price Indexes
```

Program

```text
BLS-PROGRAM-007
```

---

## HTML-009

```text
Productivity and Costs
```

Program

```text
BLS-PROGRAM-008
```

---

# HTML Discovery Rules

The collector may discover HTML pages only from:

```text
Release Calendar

↓

RSS Feed

↓

Economic News Releases

↓

Program Homepage

↓

Historical Archive
```

Never crawl outside the official BLS domain.

Never follow third-party links.

---

# HTTP Request Rules

Method

```http
GET
```

Headers

```http
User-Agent: Bitcoin-Market-Intelligence-Dataset
Accept: text/html
Accept-Encoding: gzip
```

Follow redirects only when the destination remains within `bls.gov`.

---

# HTML Validation

Validate:

```text
HTTP Status

↓

Content-Type = text/html

↓

Document Encoding

↓

DOCTYPE

↓

HTML Size

↓

Title Exists

↓

Main Content Exists
```

Reject pages that fail validation.

---

# Required Extraction Fields

Every parser must extract:

```text
page_title

page_url

publication_date

publication_time

timezone

headline

summary

program_name

pdf_links

chart_links

related_links

archive_links

last_modified
```

If a field is absent, record `null`.

Never invent values.

---

# HTML Output Structure

```text
raw/

└── bls/

    └── html/

        └── program/

            └── YYYY/

                release.html
```

Processed

```text
processed/

└── bls/

    └── html/

        └── program/

            metadata.json
```

---

# Metadata Schema

```json
{
  "html_id": "",
  "source_url": "",
  "download_timestamp": "",
  "http_status": 200,
  "content_type": "text/html",
  "page_title": "",
  "publication_datetime": "",
  "last_modified": "",
  "sha256": ""
}
```

---

# Link Discovery

The parser must identify and classify:

```text
PDF Links

Chart Links

Archive Links

Program Links

Calendar Links

RSS Links
```

Each discovered link must be passed to the appropriate collector.

---

# Duplicate Detection

Primary Key

```text
SHA256(HTML)
```

Secondary Key

```text
Canonical URL
```

If duplicate:

- Skip parsing.
- Update metadata.
- Log the event.

---

# Failure Handling

Retry only for:

- HTTP 429
- HTTP 500
- Timeout
- Network interruption

Do not retry:

- HTTP 404
- Invalid HTML
- Unsupported Content-Type

---

# Output Files

Each successful collection must produce:

```text
release.html

metadata.json

validation.json

discovered_links.json

collector.log
```

---

# AI Agent Rules

1. Never construct release URLs manually.
2. Discover release pages only from registered BLS sources.
3. Save the original HTML before parsing.
4. Preserve publication timestamps exactly as published.
5. Extract only documented fields.
6. Record missing fields as `null`.
7. Forward discovered PDF, chart and archive links to their respective collectors.
8. Compute SHA256 for every HTML document.
9. Keep raw and processed data in separate directories.
10. Log every collection attempt.

---

# Dependencies

```text
URL_REGISTRY.md

↓

RSS_REGISTRY.md

↓

CALENDAR_REGISTRY.md

↓

HTML_REGISTRY.md

↓

PDF_REGISTRY.md

↓

DATASET_REGISTRY.md
```

---

# Implementation Notes

The HTML collector must treat the **Economic News Releases** page as the primary discovery index. From there, it should enumerate current releases, locate individual release pages, identify linked PDF and Charts resources, and hand those URLs to the appropriate downstream collectors. Historical releases must be discovered through the official archive navigation rather than URL guessing.

---

# Version History

| Version | Date      | Description                                                  |
| ------- | --------- | ------------------------------------------------------------ |
| 1.0     | July 2026 | Initial implementation specification for BLS HTML collection |
