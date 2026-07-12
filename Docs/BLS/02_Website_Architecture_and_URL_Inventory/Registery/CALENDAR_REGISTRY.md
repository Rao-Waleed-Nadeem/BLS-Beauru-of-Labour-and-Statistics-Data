# CALENDAR_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Release Calendar Registry (Implementation Specification)

---

# Purpose

This registry defines how the AI agent discovers, stores, validates and monitors all official **BLS release calendars**.

The Release Calendar is the **scheduler** of the entire BLS module.

No crawler should guess release dates.

No collector should run on fixed dates.

Every collection job must be triggered from the official BLS calendar.

---

# Calendar Architecture

```text
Official BLS Calendar

        │

        ▼

Calendar Collector

        │

        ▼

Calendar Parser

        │

        ▼

Release Events

        │

        ▼

Task Queue

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
  "calendar_id": "",
  "program_id": "",
  "calendar_name": "",
  "calendar_url": "",
  "calendar_type": "",
  "timezone": "",
  "release_time": "",
  "poll_interval_minutes": 60,
  "enabled": true,
  "implementation_status": ""
}
```

---

# Calendar Registry

---

## CAL-001

Calendar ID

```text
BLS-CALENDAR-001
```

Calendar Name

```text
Master Release Calendar
```

Calendar URL

```text
https://www.bls.gov/schedule/
```

Purpose

```text
Primary discovery page for all scheduled BLS releases.
```

Priority

```text
Critical
```

---

## CAL-002

Calendar ID

```text
BLS-CALENDAR-002
```

Calendar Name

```text
Consumer Price Index Schedule
```

Calendar URL

```text
https://www.bls.gov/schedule/news_release/cpi.htm
```

Program

```text
BLS-PROGRAM-001
```

Release Time

```text
08:30 America/New_York
```

---

## CAL-003

Calendar ID

```text
BLS-CALENDAR-003
```

Calendar Name

```text
Producer Price Index Schedule
```

Discovery

```text
Master Calendar

↓

Producer Price Index
```

Program

```text
BLS-PROGRAM-002
```

---

## CAL-004

Calendar ID

```text
BLS-CALENDAR-004
```

Calendar Name

```text
Employment Situation Schedule
```

Calendar URL

```text
https://www.bls.gov/schedule/news_release/empsit.htm
```

Program

```text
BLS-PROGRAM-003
```

Release Time

```text
08:30 America/New_York
```

---

## CAL-005

Calendar ID

```text
BLS-CALENDAR-005
```

Calendar Name

```text
JOLTS Schedule
```

Calendar URL

```text
https://www.bls.gov/schedule/news_release/jolts.htm
```

Program

```text
BLS-PROGRAM-004
```

Release Time

```text
10:00 America/New_York
```

---

## CAL-006

Calendar ID

```text
BLS-CALENDAR-006
```

Calendar Name

```text
Online Calendar (ICS)
```

Calendar URL

```text
https://www.bls.gov/schedule/news_release/bls.ics
```

Purpose

```text
Machine-readable release calendar.
```

Priority

```text
Critical
```

---

# Calendar Collection Flow

```text
Load Registry

↓

Download Calendar

↓

Validate

↓

Extract Events

↓

Normalize Timezone

↓

Store Raw Calendar

↓

Store Events

↓

Compare Previous Snapshot

↓

Detect Changes

↓

Update Scheduler
```

---

# Event Schema

Every calendar event becomes one JSON object.

```json
{
  "event_id": "",
  "program_id": "",
  "release_name": "",
  "reference_period": "",
  "release_date": "",
  "release_time": "",
  "timezone": "",
  "source_url": "",
  "status": "scheduled"
}
```

---

# Scheduler Rules

Every event creates one scheduled task.

```text
Release Event

↓

Generate Queue Item

↓

Wait Until Release Time

↓

HTML Collector

↓

PDF Collector

↓

API Collector

↓

Validation

↓

Complete
```

---

# Time Standard

Store every timestamp twice.

```text
Official Time

America/New_York

↓

Converted UTC
```

Never overwrite the official published time.

---

# Storage Structure

```text
raw/

└── bls/

    └── calendar/

        ├── calendar.html

        ├── calendar.ics

        └── events.json
```

Processed

```text
processed/

└── bls/

    └── calendar/

        normalized_events.json
```

---

# Change Detection

Compare every crawl against the previous snapshot.

Detect:

```text
New Release

Updated Date

Updated Time

Cancelled Release

Removed Release
```

Generate

```text
calendar_diff.json
```

Every detected change must update downstream schedules.

---

# Validation Rules

Validate:

```text
HTTP Status

↓

Calendar Download

↓

ICS Parse (if applicable)

↓

Release Date

↓

Release Time

↓

Program Mapping

↓

Duplicate Check
```

Reject invalid events.

---

# Duplicate Key

```text
Program ID

+

Reference Period

+

Release Date
```

---

# Output Files

Each calendar update generates:

```text
calendar.html

calendar.ics

events.json

normalized_events.json

calendar_diff.json

validation.json

collector.log
```

---

# Failure Handling

Retry only for:

- HTTP 429
- HTTP 500
- Timeout
- Temporary network failure

Do not retry:

- Invalid calendar format
- Missing required event fields
- Unsupported content type

If the HTML calendar fails but the ICS calendar succeeds, continue using the ICS data and record the HTML failure.

---

# AI Agent Rules

1. Never hardcode release dates.
2. Load all schedules from this registry.
3. Download both HTML and ICS when available.
4. Preserve raw calendar files.
5. Normalize timestamps to UTC while retaining the original timezone.
6. Generate one queue item per release event.
7. Detect schedule changes on every crawl.
8. Update downstream jobs automatically after schedule changes.
9. Keep historical calendar snapshots.
10. Never trigger collectors from local system dates.

---

# Dependencies

```text
URL_REGISTRY.md

↓

CALENDAR_REGISTRY.md

↓

RSS_REGISTRY.md

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

# Official Calendar Sources

| Purpose                       | URL                                                  |
| ----------------------------- | ---------------------------------------------------- |
| Master Release Calendar       | https://www.bls.gov/schedule/                        |
| CPI Release Schedule          | https://www.bls.gov/schedule/news_release/cpi.htm    |
| Employment Situation Schedule | https://www.bls.gov/schedule/news_release/empsit.htm |
| JOLTS Release Schedule        | https://www.bls.gov/schedule/news_release/jolts.htm  |
| Online ICS Calendar           | https://www.bls.gov/schedule/news_release/bls.ics    |

Program-specific schedules not explicitly listed above (such as PPI, ECI, Productivity, Real Earnings, and Import/Export Prices) should be discovered by traversing the Master Release Calendar instead of hardcoding additional URLs.

---

# Version History

| Version | Date      | Description                                                              |
| ------- | --------- | ------------------------------------------------------------------------ |
| 1.0     | July 2026 | Initial implementation specification for BLS release calendar collection |
