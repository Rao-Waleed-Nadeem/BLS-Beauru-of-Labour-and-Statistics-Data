# ARCHIVE_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Archive Registry (Implementation Specification)

---

# Purpose

This registry defines how AI agents must discover, traverse, download, validate, and maintain **historical BLS news releases**.

The archive collector is responsible for **historical backfill (2020 → Current)**.

It must never rely on RSS.

It must never guess archive URLs.

It must always discover historical releases from official BLS archive pages.

---

# Historical Collection Pipeline

```text
Archive Registry

        │

        ▼

Archive Index

        │

        ▼

Program Archive

        │

        ▼

Year Page

        │

        ▼

Release Page

        │

        ▼

HTML Collector

        │

        ▼

PDF Collector

        │

        ▼

API Collector

        │

        ▼

Dataset Pipeline
```

---

# Registry Schema

```json
{
  "archive_id": "",
  "program_id": "",
  "dataset_id": "",
  "archive_name": "",
  "archive_url": "",
  "archive_type": "",
  "supported_years": [],
  "priority": "",
  "crawler": "",
  "output_directory": "",
  "enabled": true,
  "implementation_status": ""
}
```

---

# Archive Registry

---

## ARCHIVE-001

Archive ID

```text
BLS-ARCHIVE-001
```

Archive Name

```text
Archived News Releases (Master Index)
```

Archive URL

```text
https://www.bls.gov/bls/news-release/
```

Archive Type

```text
MASTER_ARCHIVE
```

Purpose

```text
Primary entry point for all archived BLS news releases.
```

Crawler

```text
master_archive_crawler
```

Priority

```text
Critical
```

---

## ARCHIVE-002

Archive ID

```text
BLS-ARCHIVE-002
```

Program

```text
BLS-PROGRAM-001
```

Archive

```text
Consumer Price Index Archive
```

Archive URL

```text
https://www.bls.gov/bls/news-release/cpi.htm
```

Supported Years

```text
2020 → Current
```

Crawler

```text
program_archive_crawler
```

---

## ARCHIVE-003

Program

```text
BLS-PROGRAM-002
```

Archive

```text
Producer Price Index Archive
```

Discovery

```text
Resolve from Master Archive
```

---

## ARCHIVE-004

Program

```text
BLS-PROGRAM-003
```

Archive

```text
Employment Situation Archive
```

Archive URL

```text
https://www.bls.gov/bls/news-release/empsit.htm
```

Supported Years

```text
2020 → Current
```

---

## ARCHIVE-005

Program

```text
BLS-PROGRAM-004
```

Archive

```text
JOLTS Archive
```

Discovery

```text
Resolve from Master Archive
```

---

## ARCHIVE-006

Program

```text
BLS-PROGRAM-005
```

Archive

```text
Employment Cost Index Archive
```

Discovery

```text
Resolve from Master Archive
```

---

## ARCHIVE-007

Program

```text
BLS-PROGRAM-006
```

Archive

```text
Real Earnings Archive
```

Discovery

```text
Resolve from Master Archive
```

---

## ARCHIVE-008

Program

```text
BLS-PROGRAM-007
```

Archive

```text
Import & Export Price Index Archive
```

Discovery

```text
Resolve from Master Archive
```

---

## ARCHIVE-009

Program

```text
BLS-PROGRAM-008
```

Archive

```text
Productivity and Costs Archive
```

Discovery

```text
Resolve from Master Archive
```

---

# Archive Discovery Rules

The collector must follow this sequence only.

```text
Master Archive

↓

Program Archive

↓

Year Section

↓

Monthly Release

↓

Release HTML

↓

PDF

↓

Charts
```

Never enumerate URLs by pattern.

Always traverse hyperlinks published by BLS.

---

# Historical Coverage

Initial backfill target

```text
2020

↓

2021

↓

2022

↓

2023

↓

2024

↓

2025

↓

Current Year
```

If earlier years are required later,

extend the registry,

not the crawler logic.

---

# Crawl Algorithm

```text
Load ARCHIVE_REGISTRY

↓

Open Master Archive

↓

Locate Registered Program

↓

Open Program Archive

↓

Enumerate Available Years

↓

Open Year

↓

Enumerate Releases

↓

Queue Release URLs

↓

Pass URLs to HTML Collector
```

---

# Queue Policy

Every discovered release generates one work item.

```json
{
  "program_id": "",
  "release_url": "",
  "release_year": "",
  "collector": "html"
}
```

Workers consume the queue asynchronously.

---

# Storage Structure

```text
raw/

└── bls/

    └── archive/

        └── program/

            └── year/

                archive_index.html

                release_urls.json
```

---

# Metadata

Each archive crawl creates

```text
metadata.json
```

Schema

```json
{
  "archive_id": "",
  "crawl_timestamp": "",
  "years_discovered": 0,
  "releases_discovered": 0,
  "new_releases": 0,
  "updated_releases": 0,
  "crawler_version": ""
}
```

---

# Validation Rules

Validate

```text
Archive URL

↓

HTTP 200

↓

HTML Available

↓

Year Links

↓

Release Links

↓

Duplicate Check
```

Stop processing if the archive index cannot be validated.

---

# Duplicate Detection

Unique Key

```text
Program ID

+

Release URL
```

If already indexed

```text
Skip

Update Metadata

Continue
```

---

# Failure Handling

Retry only for

- HTTP 429
- HTTP 500
- Network timeout
- Temporary DNS failure

Do not retry

- HTTP 404
- Invalid HTML
- Missing archive page

Generate a validation report for every failed crawl.

---

# Output Files

Each archive crawl produces

```text
archive_index.html

release_urls.json

metadata.json

validation.json

collector.log
```

---

# AI Agent Rules

1. Never generate archive URLs manually.
2. Start from the registered master archive only.
3. Traverse hyperlinks; do not brute-force years or filenames.
4. Save every archive index before parsing.
5. Queue discovered release pages for the HTML collector.
6. Preserve raw HTML.
7. Maintain idempotent crawls using duplicate detection.
8. Log every discovered release.
9. Keep archive crawling separate from content extraction.
10. Update metadata after every successful crawl.

---

# Dependencies

```text
URL_REGISTRY.md

↓

PROGRAM_REGISTRY.md

↓

ARCHIVE_REGISTRY.md

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

# Official Archive Sources

The archive crawler may use only the following official entry points:

| Purpose                       | URL                                             |
| ----------------------------- | ----------------------------------------------- |
| Master Archived News Releases | https://www.bls.gov/bls/news-release/           |
| CPI Archive                   | https://www.bls.gov/bls/news-release/cpi.htm    |
| Employment Situation Archive  | https://www.bls.gov/bls/news-release/empsit.htm |
| Historical Release Schedules  | https://www.bls.gov/bls/archived_sched.htm      |

All additional program archives (PPI, JOLTS, ECI, Real Earnings, Productivity, Import/Export Prices, etc.) must be discovered by traversing links from the **Master Archived News Releases** page rather than hardcoding URLs.

---

# Version History

| Version | Date      | Description                                                                |
| ------- | --------- | -------------------------------------------------------------------------- |
| 1.0     | July 2026 | Initial implementation specification for BLS historical archive collection |
