# 05_VALIDATION_AND_MAINTENANCE.md

# Bitcoin Market Intelligence Dataset

## BLS Validation & Maintenance Guide (Implementation Specification)

---

# Purpose

This document defines the quality assurance framework for the entire BLS module.

Its objectives are to:

- Ensure data integrity.
- Detect incomplete collections.
- Detect missing releases.
- Detect website changes.
- Detect broken URLs.
- Prevent duplicate records.
- Monitor long-term pipeline health.

This document applies to every collector, parser, normalizer, validator and storage component.

---

# Validation Pipeline

```text
Collection

↓

Parsing

↓

Normalization

↓

Validation

↓

Quality Checks

↓

Storage

↓

Monitoring

↓

Maintenance
```

Validation is mandatory.

No dataset may bypass this pipeline.

---

# Validation Categories

| Category                | Purpose                          |
| ----------------------- | -------------------------------- |
| Schema Validation       | Verify Unified Schema            |
| Metadata Validation     | Verify metadata completeness     |
| Release Validation      | Verify release information       |
| Timestamp Validation    | Verify official publication time |
| Relationship Validation | Verify foreign keys              |
| Duplicate Validation    | Prevent duplicate records        |
| URL Validation          | Verify source URLs               |
| Archive Validation      | Verify historical completeness   |
| Storage Validation      | Verify stored artifacts          |

---

# Validation Workflow

```text
Receive Object

↓

Schema Validation

↓

Required Fields

↓

Data Types

↓

Relationships

↓

Duplicate Detection

↓

Completeness Check

↓

Timestamp Verification

↓

Checksum Verification

↓

Storage Validation

↓

Accepted
```

Failure at any stage rejects the object.

---

# Required Field Validation

Every normalized object must contain all required fields defined in:

```text
01_UNIFIED_SCHEMA.md

↓

02_DATASET_SPECIFICATIONS.md
```

Missing required fields immediately invalidate the object.

---

# Data Type Validation

Validate:

```text
String

↓

Number

↓

Boolean

↓

DateTime

↓

Array

↓

Object
```

Automatic type conversion is prohibited.

---

# Completeness Checks

Every supported dataset must be checked against the expected publication schedule.

Example

```text
Expected Releases

↓

Collected Releases

↓

Difference

↓

Missing Releases
```

Generate:

```text
missing_releases.json
```

---

# Timestamp Verification

Every release timestamp must include:

```text
Official Time

America/New_York

↓

UTC Conversion
```

Validation Rules

- Publication timestamp exists.
- UTC conversion is correct.
- Timestamp format is ISO-8601.
- Original publication time is preserved.

---

# Duplicate Detection

Duplicate detection operates at four levels.

Level 1

```text
URL
```

Level 2

```text
Release ID
```

Level 3

```text
Series ID

+

Year

+

Period
```

Level 4

```text
SHA256
```

If any duplicate exists:

```text
Reject

↓

Log

↓

Skip Storage
```

---

# Missing Release Detection

Purpose

Ensure every official BLS publication is collected.

Workflow

```text
Calendar

↓

Expected Releases

↓

Collected Releases

↓

Compare

↓

Generate Report
```

Output

```text
missing_releases.json
```

---

# URL Monitoring

Monitor every registered URL.

Validation

```text
HTTP Status

↓

Redirect

↓

Content Type

↓

Availability

↓

Response Time
```

Record results in:

```text
url_health.json
```

Any permanent URL failure must be reported for manual review.

---

# Website Change Detection

The BLS website may change page layouts while keeping the same URL.

The pipeline must detect structural changes before parsing.

Workflow

```text
Download HTML

↓

DOM Snapshot

↓

Compare Previous Snapshot

↓

Layout Changed?

↓

YES

↓

Generate Alert

↓

Manual Review

↓

Parser Update
```

Generate:

```text
website_change_report.json
```

HTML parser updates should be driven by detected structural changes rather than parser failures alone.

---

# Regression Testing

Run after every pipeline modification.

Test:

```text
Calendar

↓

API

↓

RSS

↓

HTML

↓

PDF

↓

Normalization

↓

Validation

↓

Storage
```

Regression succeeds only if:

- No existing dataset changes unexpectedly.
- Historical outputs remain reproducible.
- Validation results remain consistent.

---

# Manual Review Queue

Objects requiring human review:

- Invalid schema
- Missing release
- Broken URL
- Corrupted PDF
- Unexpected HTML structure
- Unknown dataset
- Registry inconsistency

Generate:

```text
manual_review_queue.json
```

---

# Future Updates

Whenever BLS introduces:

- New datasets
- New programs
- New APIs
- New calendars
- New RSS feeds
- New archive layouts

The implementation must:

```text
Update Registry

↓

Update Unified Schema

↓

Update Dataset Specification

↓

Run Regression Tests

↓

Deploy
```

No implementation changes may bypass regression testing.

---

# Known Limitations

Current implementation assumes:

- Official BLS website remains publicly accessible.
- Official release calendar remains authoritative.
- API availability follows documented limits.
- Historical archives remain available.

Temporary outages should be handled through retry logic rather than modifying datasets. The BLS API documents request limits, HTTP status codes (including `429`), and service availability expectations that should be incorporated into monitoring.

---

# Quality Reports

Generate after every execution.

```text
validation_report.json

completeness_report.json

duplicate_report.json

timestamp_report.json

url_health.json

website_change_report.json

manual_review_queue.json

pipeline_health.json
```

---

# Maintenance Schedule

| Task                          | Frequency               |
| ----------------------------- | ----------------------- |
| URL Health Check              | Daily                   |
| Calendar Validation           | Daily                   |
| RSS Validation                | Daily                   |
| Historical Completeness Check | Weekly                  |
| Duplicate Scan                | Weekly                  |
| Storage Integrity Check       | Weekly                  |
| Checksum Verification         | Monthly                 |
| Regression Test               | Before every deployment |
| Registry Review               | Monthly                 |

---

# AI Agent Rules

1. Never bypass validation.
2. Reject invalid objects before storage.
3. Preserve all raw artifacts.
4. Detect duplicates before persistence.
5. Verify every timestamp.
6. Compare collected releases against the official calendar.
7. Monitor every registered URL.
8. Detect HTML structure changes before updating parsers.
9. Generate quality reports after every execution.
10. Run regression tests before deploying any pipeline modification.

---

# Dependencies

```text
01_UNIFIED_SCHEMA.md

↓

02_DATASET_SPECIFICATIONS.md

↓

03_STORAGE_SPECIFICATION.md

↓

Pipeline

↓

Validation

↓

Monitoring

↓

Maintenance
```

---

# Version History

| Version | Date      | Description                                                         |
| ------- | --------- | ------------------------------------------------------------------- |
| 1.0     | July 2026 | Initial validation and maintenance specification for the BLS module |
