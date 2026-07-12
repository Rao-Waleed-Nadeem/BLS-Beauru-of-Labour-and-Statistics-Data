# RSS_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS RSS Registry (Implementation Specification)

---

# Purpose

This registry defines how AI agents must discover, monitor, download, validate, and archive **official BLS RSS feeds**.

RSS is **not** the primary historical data source.

RSS is used for:

- New release detection
- Incremental updates
- Scheduler triggers
- Change detection
- Zero-delay notification
- Release URL discovery

Historical backfill must **never** rely on RSS.

Use:

- API
- HTML Archive
- PDF Archive

for historical collection.

---

# RSS Pipeline

```text
Scheduler

↓

Load RSS_REGISTRY

↓

Download RSS XML

↓

Validate XML

↓

Extract Items

↓

Compare With Database

↓

New Item?

↓

YES

↓

Download HTML

↓

Download PDF

↓

API Collection

↓

Store Raw XML

↓

Store Metadata

↓

Trigger Dataset Pipeline
```

---

# RSS Collection Priority

| Usage                 | Allowed |
| --------------------- | ------- |
| Historical Collection | ❌ No   |
| Daily Monitoring      | ✅ Yes  |
| Release Detection     | ✅ Yes  |
| Incremental Updates   | ✅ Yes  |
| Scheduler Trigger     | ✅ Yes  |
| Event Notification    | ✅ Yes  |

---

# RSS Feed Registry Schema

```json
{
  "feed_id": "",
  "feed_name": "",
  "feed_url": "",
  "program_id": "",
  "dataset_id": "",
  "priority": "",
  "poll_interval_minutes": 5,
  "enabled": true,
  "output_directory": "",
  "implementation_status": ""
}
```

---

# RSS Feed Registry

---

## RSS-001

Feed ID

```text
BLS-RSS-001
```

Feed Name

```text
BLS Latest News
```

Feed URL

```text
https://www.bls.gov/feed/bls_latest.rss
```

Purpose

```text
Detect newly published BLS economic releases.
```

Priority

```text
Critical
```

Polling Interval

```text
5 Minutes
```

Output Directory

```text
raw/bls/rss/latest/
```

---

## RSS-002

Feed ID

```text
BLS-RSS-002
```

Feed Name

```text
Consumer Price Index
```

Feed Source

```text
Locate from the official BLS RSS feed index before enabling.
```

Program

```text
BLS-PROGRAM-001
```

Priority

```text
Critical
```

Status

```text
Disabled Until Feed URL Verified
```

---

## RSS-003

Feed ID

```text
BLS-RSS-003
```

Feed Name

```text
Producer Price Index
```

Status

```text
Disabled Until Feed URL Verified
```

---

## RSS-004

Feed ID

```text
BLS-RSS-004
```

Feed Name

```text
Employment Situation
```

Priority

```text
Critical
```

Status

```text
Disabled Until Feed URL Verified
```

---

## RSS-005

Feed ID

```text
BLS-RSS-005
```

Feed Name

```text
Job Openings and Labor Turnover Survey
```

Status

```text
Disabled Until Feed URL Verified
```

---

## RSS Download Flow

```text
Load Feed URL

↓

HTTP GET

↓

HTTP Status = 200 ?

↓

Parse XML

↓

Validate

↓

Extract Channel

↓

Extract Items

↓

Save XML

↓

Generate Metadata

↓

Trigger Pipeline
```

---

# Expected RSS XML Structure

The parser must support RSS 2.0 and extract the following elements when present:

```text
channel

title

link

description

lastBuildDate

item

title

link

pubDate

description

guid
```

---

# Raw Storage

```text
raw/

bls/

rss/

feed_name/

YYYY/

MM/

rss.xml
```

---

# Metadata Storage

```text
metadata.json
```

Schema

```json
{
  "feed_id": "",
  "download_timestamp": "",
  "http_status": 200,
  "etag": "",
  "last_modified": "",
  "item_count": 0,
  "new_items": 0,
  "feed_hash": ""
}
```

---

# Duplicate Detection

For every RSS item compute a unique key using:

```text
GUID

↓

Else Link

↓

Else SHA256(title + pubDate)
```

If the key already exists:

```text
Ignore Item
```

Do not trigger downstream collection.

---

# Trigger Rules

Every new RSS item must trigger:

```text
HTML Collector

↓

PDF Collector

↓

API Collector

↓

Validation

↓

Normalization
```

The RSS collector must never attempt to build the final dataset by itself.

---

# Polling Policy

| Feed Priority | Poll Interval |
| ------------- | ------------- |
| Critical      | 5 Minutes     |
| High          | 15 Minutes    |
| Medium        | 30 Minutes    |

Do not poll more frequently than configured.

---

# Failure Handling

Retry only when:

- Network timeout
- HTTP 429
- HTTP 500
- Temporary DNS failure

Do not retry:

- Invalid XML
- HTTP 404
- Feed removed

Record all failures in:

```text
logs/rss/
```

---

# AI Agent Rules

1. Load feed URLs only from this registry.
2. Always save the original XML before parsing.
3. Validate XML before extraction.
4. Preserve all timestamps exactly as published.
5. Never modify RSS content.
6. Trigger downstream collectors only for new items.
7. Maintain a persistent duplicate index.
8. Archive every downloaded XML snapshot.
9. Log every polling cycle, even when no new items are found.
10. Never use RSS for historical backfill.

---

# Dependencies

```text
URL_REGISTRY.md

↓

RSS_REGISTRY.md

↓

HTML_REGISTRY.md

↓

PDF_REGISTRY.md

↓

API_REGISTRY.md

↓

DATASET_REGISTRY.md
```

---

# Version History

| Version | Date      | Description                                                 |
| ------- | --------- | ----------------------------------------------------------- |
| 1.0     | July 2026 | Initial implementation specification for BLS RSS collection |
