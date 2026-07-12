# 01_UNIFIED_SCHEMA.md

# Bitcoin Market Intelligence Dataset

## BLS Unified Data Schema (Implementation Specification)

---

# Purpose

This document defines the **canonical data model** used throughout the BLS module.

Every collector (API, HTML, PDF, RSS, Archive) must normalize its output into this schema before the data enters the dataset pipeline.

No collector may define its own output format.

No AI model will consume raw HTML, raw PDF, raw RSS, or raw API responses directly.

Instead:

```text
Raw Source

↓

Collector

↓

Normalizer

↓

Unified Schema

↓

Validation

↓

Processed Dataset

↓

Feature Engineering

↓

AI Model
```

---

# Design Principles

Every dataset in the BLS module must satisfy the following principles:

- One canonical schema.
- Source-independent.
- Backward compatible.
- Extensible without breaking previous versions.
- Immutable raw data.
- Normalized processed data.
- Version controlled.

---

# Unified Object

Every normalized release must produce one object.

```json
{
  "metadata": {},
  "release": {},
  "event": {},
  "api": {},
  "html": {},
  "pdf": {},
  "attachments": {},
  "relationships": {}
}
```

---

# Root Schema

| Field         | Type   | Required | Description                     |
| ------------- | ------ | -------- | ------------------------------- |
| metadata      | object | Yes      | System metadata                 |
| release       | object | Yes      | Official release information    |
| event         | object | Yes      | Economic event information      |
| api           | object | Yes      | Normalized API data             |
| html          | object | Yes      | HTML extracted content          |
| pdf           | object | Yes      | PDF metadata and extracted text |
| attachments   | object | Yes      | Additional resources            |
| relationships | object | Yes      | Links to related entities       |

---

# Metadata Schema

Purpose

Store collection metadata.

Schema

```json
{
  "uuid": "",
  "dataset_id": "",
  "program_id": "",
  "series_id": "",
  "collector": "",
  "collector_version": "",
  "schema_version": "",
  "source_type": "",
  "collection_timestamp": "",
  "normalization_timestamp": "",
  "validation_status": "",
  "checksum": ""
}
```

Rules

- UUID must be globally unique.
- Collection timestamps must be UTC.
- Source type must be API, HTML, PDF, RSS or ARCHIVE.
- Validation status must be PASS or FAIL.

---

# Release Schema

Purpose

Represents one official BLS publication.

```json
{
  "release_id": "",
  "release_name": "",
  "program_name": "",
  "dataset_name": "",
  "reference_period": "",
  "release_datetime": "",
  "timezone": "",
  "headline": "",
  "summary": "",
  "revision": false,
  "status": "published"
}
```

Required Fields

- release_name
- release_datetime
- program_name
- dataset_name

---

# Event Schema

Purpose

Represents the market-moving economic event.

```json
{
  "event_id": "",
  "event_type": "",
  "importance": "",
  "country": "United States",
  "currency": "USD",
  "asset_class": "Macro",
  "expected_value": "",
  "actual_value": "",
  "previous_value": "",
  "revised_value": "",
  "surprise_value": "",
  "surprise_percent": ""
}
```

The BLS API provides historical observations by series, while values such as "expected" are not supplied by BLS and should remain null unless populated from another approved data source.

---

# API Schema

Purpose

Normalized API payload.

```json
{
  "series_id": "",
  "series_title": "",
  "frequency": "",
  "year": "",
  "period": "",
  "period_name": "",
  "value": "",
  "latest": false,
  "footnotes": []
}
```

This schema maps directly from BLS API responses, which include fields such as `seriesID`, `year`, `period`, `periodName`, `value`, and `footnotes`.

---

# HTML Schema

Purpose

Normalized HTML extraction.

```json
{
  "page_url": "",
  "page_title": "",
  "publication_datetime": "",
  "headline": "",
  "summary": "",
  "main_content": "",
  "tables": [],
  "charts": [],
  "links": []
}
```

---

# PDF Schema

Purpose

Normalized PDF information.

```json
{
  "pdf_url": "",
  "filename": "",
  "pages": 0,
  "sha256": "",
  "text": "",
  "tables": [],
  "figures": []
}
```

---

# Attachment Schema

```json
{
  "pdf_files": [],
  "html_files": [],
  "charts": [],
  "images": [],
  "spreadsheets": []
}
```

---

# Relationship Schema

Purpose

Connect releases to other project objects.

```json
{
  "program_id": "",
  "dataset_id": "",
  "series_id": "",
  "calendar_id": "",
  "archive_id": "",
  "rss_feed_id": ""
}
```

---

# Primary Keys

| Object   | Primary Key               |
| -------- | ------------------------- |
| Metadata | uuid                      |
| Release  | release_id                |
| Event    | event_id                  |
| API      | series_id + year + period |
| HTML     | page_url                  |
| PDF      | sha256                    |

---

# Foreign Keys

```text
Program_ID

↓

Dataset_ID

↓

Series_ID

↓

Release_ID

↓

Event_ID
```

Every relationship must be traceable.

---

# Validation Rules

Every normalized object must satisfy:

```text
Schema Validation

↓

Required Field Validation

↓

Data Type Validation

↓

Duplicate Detection

↓

Relationship Validation

↓

Checksum Validation
```

If any validation step fails:

- Reject normalization.
- Preserve raw files.
- Generate `validation.json`.
- Record the failure in `collector.log`.

---

# Null Handling

Missing data must be represented as:

```json
null
```

Do not use:

- Empty string
- "N/A"
- "-"
- "Unknown"

---

# Time Standard

Store every timestamp in two formats.

```text
Official Publication Time

America/New_York

↓

UTC
```

Never overwrite the original published time.

---

# Encoding Standard

All normalized files must use:

```text
UTF-8
```

---

# Versioning

Every normalized object must include:

```json
{
  "schema_version": "1.0.0"
}
```

Schema changes must increment the version without breaking previous datasets.

---

# Output Standard

Every collector must produce:

```text
raw/

↓

normalized/

↓

validated/

↓

processed/
```

Collectors never write directly into processed datasets.

---

# AI Agent Rules

1. Never create custom schemas.
2. Always normalize to this document.
3. Preserve raw values exactly.
4. Do not infer missing fields.
5. Use null for unavailable values.
6. Validate before storage.
7. Preserve source timestamps.
8. Keep relationships intact.
9. Never modify historical records.
10. Increment schema version when introducing breaking changes.

---

# Dependencies

```text
PROGRAM_REGISTRY.md

↓

DATASET_REGISTRY.md

↓

SERIES_REGISTRY.md

↓

UNIFIED_SCHEMA.md

↓

Collector

↓

Normalizer

↓

Storage
```

---

# Version History

| Version | Date      | Description                                                |
| ------- | --------- | ---------------------------------------------------------- |
| 1.0     | July 2026 | Initial unified schema for all BLS collectors and datasets |
