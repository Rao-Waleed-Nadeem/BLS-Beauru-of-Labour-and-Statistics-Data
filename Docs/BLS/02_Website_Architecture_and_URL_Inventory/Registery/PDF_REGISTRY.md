# PDF_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS PDF Registry (Implementation Specification)

---

# Purpose

This registry defines how the AI agent discovers, downloads, validates, parses, versions, and archives **official BLS PDF news releases**.

PDF files are considered **immutable source artifacts**.

They must always be preserved exactly as downloaded.

PDF files are never edited.

Extracted text is stored separately.

---

# PDF Collection Pipeline

```text
Release Calendar / RSS / HTML

            │

            ▼

Discover PDF URL

            │

            ▼

Download PDF

            │

            ▼

Validate PDF

            │

            ▼

Store Original

            │

            ▼

Extract Text

            │

            ▼

Generate Metadata

            │

            ▼

Validate

            │

            ▼

Dataset Pipeline
```

---

# PDF Registry Schema

```json
{
  "pdf_id": "",
  "program_id": "",
  "dataset_id": "",
  "document_name": "",
  "pdf_url": "",
  "discovery_method": "",
  "enabled": true,
  "priority": "",
  "download_directory": "",
  "text_directory": "",
  "metadata_directory": "",
  "implementation_status": ""
}
```

---

# PDF Discovery Rules

The collector **must never guess** PDF URLs.

PDF URLs must be discovered only from:

1. Economic News Releases page
2. Archived News Releases page
3. Program release page
4. HTML release page
5. RSS item (if available)

Never build PDF URLs manually.

---

# PDF Registry

---

## PDF-001

Document ID

```text
BLS-PDF-001
```

Program

```text
BLS-PROGRAM-001
```

Dataset

```text
BLS-DATASET-001
```

Document

```text
Consumer Price Index
```

Discovery

```text
Economic News Releases

↓

HTML Release

↓

PDF Link
```

Priority

```text
Critical
```

---

## PDF-002

```text
Producer Price Index
```

Program

```text
BLS-PROGRAM-002
```

Priority

```text
Critical
```

---

## PDF-003

```text
Employment Situation
```

Program

```text
BLS-PROGRAM-003
```

Priority

```text
Critical
```

---

## PDF-004

```text
Job Openings and Labor Turnover Survey
```

Program

```text
BLS-PROGRAM-004
```

---

## PDF-005

```text
Employment Cost Index
```

Program

```text
BLS-PROGRAM-005
```

---

## PDF-006

```text
Real Earnings
```

Program

```text
BLS-PROGRAM-006
```

---

## PDF-007

```text
Import and Export Price Indexes
```

Program

```text
BLS-PROGRAM-007
```

---

## PDF-008

```text
Productivity and Costs
```

Program

```text
BLS-PROGRAM-008
```

---

# Download Workflow

```text
Load Registry

↓

Open HTML Release

↓

Locate PDF Link

↓

Resolve Absolute URL

↓

Download

↓

HTTP Status == 200

↓

Save Original PDF

↓

Generate SHA256

↓

Extract Metadata

↓

Extract Text

↓

Store
```

---

# HTTP Validation

Accept only:

```text
200 OK
```

Reject:

```text
301 (follow once then update URL)

404

403

500
```

Log every failure.

---

# File Naming Standard

Original PDF

```text
YYYY-MM-DD_<program>.pdf
```

Examples

```text
2024-07-11_cpi.pdf

2025-03-07_employment.pdf

2026-05-14_ppi.pdf
```

---

# Directory Structure

```text
raw/

└── bls/

    └── pdf/

        └── program/

            └── year/

                file.pdf
```

---

# Extracted Text

Never overwrite PDF.

Store separately.

```text
processed/

└── bls/

    └── pdf_text/

        └── program/

            release.txt
```

---

# Metadata File

Every PDF generates

```text
metadata.json
```

Schema

```json
{
  "pdf_id": "",
  "source_url": "",
  "download_timestamp": "",
  "http_status": 200,
  "sha256": "",
  "content_length": 0,
  "pages": 0,
  "filename": "",
  "mime_type": "application/pdf"
}
```

---

# Validation Rules

Validate

```text
HTTP Status

↓

PDF Signature

↓

File Size

↓

Page Count

↓

SHA256

↓

Metadata

↓

Extraction Success
```

If validation fails

```text
Reject PDF

Retry (network errors only)

Generate Validation Report
```

---

# Text Extraction Rules

Output

```text
UTF-8
```

Preserve

- Tables
- Paragraph order
- Numeric values
- Dates
- Time values

Do not

- Reformat numbers
- Translate text
- Remove whitespace that changes meaning
- Modify extracted values

---

# Output Files

Every download produces

```text
original.pdf

text.txt

metadata.json

validation.json

collector.log
```

---

# Duplicate Detection

Primary Key

```text
SHA256(original.pdf)
```

If duplicate

```text
Skip Download

Update Metadata

Log Event
```

---

# Agent Rules

1. Never construct PDF URLs manually.
2. Discover PDF links from official BLS pages only.
3. Save original PDF before extraction.
4. Never overwrite original files.
5. Validate every download.
6. Generate SHA256 for integrity.
7. Store extracted text separately.
8. Preserve publication timestamps.
9. Record every download in collector.log.
10. Continue pipeline only after successful validation.

---

# Dependencies

```text
URL_REGISTRY.md

↓

PROGRAM_REGISTRY.md

↓

HTML_REGISTRY.md

↓

RSS_REGISTRY.md

↓

PDF_REGISTRY.md

↓

DATASET_REGISTRY.md
```

---

# Official Discovery Sources

The implementation must discover PDF documents from the following official BLS resources:

- Economic News Releases (current releases with PDF links)
- Archived News Releases (historical PDF library)
- Program-specific release pages
- HTML release pages containing PDF references

Do not use third-party mirrors or reconstructed PDF URLs.

---

# Version History

| Version | Date      | Description                                                 |
| ------- | --------- | ----------------------------------------------------------- |
| 1.0     | July 2026 | Initial implementation specification for BLS PDF collection |
