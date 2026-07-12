# 02_DATA_COLLECTION.md

# Bitcoin Market Intelligence Dataset

## BLS Data Collection Guide (Implementation Specification)

---

# Purpose

This document defines **how the AI agent collects data** from the official Bureau of Labor Statistics (BLS) sources.

This document is **implementation only**.

It defines:

- Discovery
- Crawling
- Downloading
- Historical Backfill
- Incremental Updates
- Queue Generation

It does **not** define parsing, normalization or storage.

---

# Collection Pipeline

```text
Configuration

↓

Registry Loader

↓

Calendar Discovery

↓

Task Queue

↓

Collector Dispatcher

↓

API Collector

↓

HTML Collector

↓

PDF Collector

↓

RSS Collector

↓

Archive Collector

↓

Raw Storage

↓

Parser Queue
```

---

# Collection Order

The pipeline **must always** execute in this order.

```text
1

Calendar

↓

2

Archive Discovery

↓

3

RSS Discovery

↓

4

HTML Releases

↓

5

PDF Releases

↓

6

API Data

↓

7

Validation

↓

8

Raw Storage

↓

Parser Queue
```

Never change this order.

---

# Collector Architecture

```text
Collector Manager

│

├── Calendar Collector

├── Archive Collector

├── RSS Collector

├── HTML Collector

├── PDF Collector

└── API Collector
```

Each collector is completely independent.

No collector may call another collector directly.

Communication occurs only through the scheduler.

---

# Collection Configuration

```yaml
collection:
  start_year: 2020
  end_year: current

scheduler:
  timezone: America/New_York

retry:
  max_attempts: 3

validation:
  enabled: true

storage:
  raw_only: true
```

---

# Calendar Collection

Purpose

Discover official release dates before downloading any data.

Workflow

```text
Load Calendar Registry

↓

Download Calendar

↓

Extract Events

↓

Generate Collection Queue

↓

Store Calendar Snapshot
```

Input

```text
Calendar Registry
```

Output

```text
events.json
```

The scheduler must use the official BLS release calendar (HTML and ICS where available) as the authoritative source of release timing.

---

# Archive Collection

Purpose

Discover historical releases.

Workflow

```text
Archive Registry

↓

Download Archive Page

↓

Extract Release Links

↓

Remove Duplicates

↓

Queue HTML

↓

Queue PDF
```

Archive discovery must never assume release URLs. It must discover them from the official archive pages.

---

# RSS Collection

Purpose

Discover newly published releases.

Workflow

```text
RSS Feed

↓

Download XML

↓

Parse Items

↓

Extract URLs

↓

Remove Existing URLs

↓

Queue Collection
```

Only new items should create queue entries.

Previously collected URLs must be skipped.

---

# HTML Collection

Purpose

Download official release pages.

Workflow

```text
Receive Queue Item

↓

Resolve URL

↓

HTTP Request

↓

Validate Response

↓

Save HTML

↓

Generate Metadata

↓

Parser Queue
```

Download only after the release has been officially published.

---

# PDF Collection

Purpose

Download official PDF publications.

Workflow

```text
Receive Queue Item

↓

Resolve PDF URL

↓

Download PDF

↓

SHA256

↓

Save File

↓

Metadata

↓

Parser Queue
```

The original PDF must never be modified.

---

# API Collection

Purpose

Download official BLS time-series data.

Workflow

```text
Receive Queue

↓

Resolve Series IDs

↓

Generate Request

↓

Call API

↓

Validate JSON

↓

Save Response

↓

Parser Queue
```

API requests should use the registered Series IDs and appropriate GET or POST signatures depending on the number of series and historical range required. Registered API access supports larger requests (up to 50 series and 20 years per request). Unregistered access has lower limits. The agent should batch requests accordingly and never exceed documented limits.

---

# Historical Backfill

Objective

Download every supported BLS release from **2020 through the current release**.

Workflow

```text
Select Program

↓

Discover Archives

↓

Generate Historical Queue

↓

Download HTML

↓

Download PDF

↓

Download API Data

↓

Verify Completeness
```

Backfill completes one program before moving to the next.

Recommended order:

```text
CPI

↓

PPI

↓

Employment

↓

JOLTS

↓

ECI

↓

Productivity

↓

Real Earnings

↓

Import / Export Prices
```

---

# Incremental Updates

Purpose

Collect only newly published data.

Workflow

```text
Scheduler Starts

↓

Check Calendar

↓

Check RSS

↓

Check Latest Release

↓

Compare Metadata

↓

Generate New Jobs

↓

Download New Data
```

Incremental mode must never redownload unchanged releases.

---

# Queue Management

Queue Object

```json
{
  "job_id": "",
  "collector": "api",
  "program_id": "",
  "dataset_id": "",
  "series_id": "",
  "source_url": "",
  "priority": "",
  "scheduled_time": "",
  "status": "pending"
}
```

Job States

```text
Pending

↓

Running

↓

Completed

↓

Validated

↓

Archived
```

Failure state

```text
Failed
```

---

# Duplicate Detection

Before downloading any resource:

```text
Generate Source Hash

↓

Check Metadata Index

↓

Already Exists?

↓

YES

Skip

↓

NO

Download
```

Duplicate detection should use:

- Source URL
- SHA256 checksum
- Release ID
- Publication date

---

# Collector Validation

Validate before saving:

```text
HTTP Status

↓

Content Type

↓

File Size

↓

Checksum

↓

Source URL

↓

Timestamp
```

Reject downloads that fail validation.

---

# Retry Strategy

Retry only for transient failures:

- HTTP 429
- HTTP 500
- HTTP 502
- HTTP 503
- HTTP 504
- Network timeout
- Temporary connection errors

Use exponential backoff.

Do **not** retry:

- HTTP 404
- Invalid URL
- Unsupported content type
- Corrupted registry configuration

The BLS API documents rate limits and HTTP response codes, including `429 Too Many Requests`, which should be handled with delayed retries rather than immediate repetition.

---

# Collection Logging

Every collection job must generate:

```text
collector.log
```

Each log entry contains:

```text
Timestamp

Collector

Program

Dataset

Series

URL

Status

Duration

File Size

Retry Count

Checksum
```

---

# Completion Criteria

A collection job is complete only when:

```text
Download Successful

↓

Validation Passed

↓

Raw File Saved

↓

Metadata Generated

↓

Parser Job Created
```

---

# AI Agent Rules

1. Never crawl unknown URLs.
2. Use only URLs defined in the registry.
3. Always start from the official calendar.
4. Complete historical backfill before enabling incremental updates.
5. Download raw files before any parsing.
6. Preserve every original response exactly as received.
7. Generate one metadata record per downloaded file.
8. Never overwrite an existing raw artifact.
9. Skip duplicate releases using metadata validation.
10. Do not pass data to parsers until collection validation succeeds.

---

# Dependencies

```text
URL_REGISTRY.md

↓

PROGRAM_REGISTRY.md

↓

DATASET_REGISTRY.md

↓

SERIES_REGISTRY.md

↓

CALENDAR_REGISTRY.md

↓

Collector Manager

↓

Raw Storage

↓

Parser
```

---

# Version History

| Version | Date      | Description                                                           |
| ------- | --------- | --------------------------------------------------------------------- |
| 1.0     | July 2026 | Initial implementation specification for BLS data collection pipeline |
