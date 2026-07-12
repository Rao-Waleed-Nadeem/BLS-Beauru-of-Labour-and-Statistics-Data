# API_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Public Data API Registry (Implementation Specification)

---

# Purpose

This document defines how AI coding agents must interact with the official BLS Public Data API.

This is **not** API documentation copied from BLS.

This is the implementation specification for this project.

Every API request, response parser, validator, and updater must follow this document.

---

# API Architecture

```text
BLS Public API

        │

        ▼

HTTP Client

        │

        ▼

Request Builder

        │

        ▼

Response Validator

        │

        ▼

JSON Parser

        │

        ▼

Normalizer

        │

        ▼

Dataset Storage

        │

        ▼

Validation Pipeline
```

---

# API Information

| Property          | Value                                  |
| ----------------- | -------------------------------------- |
| API Name          | BLS Public Data API                    |
| Protocol          | HTTPS                                  |
| Architecture      | REST                                   |
| Response Format   | JSON, XLSX                             |
| Supported Methods | GET, POST                              |
| Authentication    | API Key (Version 2) / None (Version 1) |
| Preferred Version | Version 2                              |
| Preferred Method  | POST                                   |

The BLS recommends Version 2 because it supports larger queries, catalog information, calculations, and extended year ranges.

---

# Base Endpoint

```text
https://api.bls.gov/publicAPI/v2/timeseries/data/
```

---

# API Version Policy

Always use:

```text
/publicAPI/v2/
```

Never implement Version 1 unless Version 2 becomes unavailable.

---

# HTTP Method Rules

## GET

Allowed only for:

- Single series
- Quick verification
- Debugging

Do not use GET for production historical collection.

---

## POST

Mandatory for:

- Historical backfill
- Multiple series
- Production pipeline
- Scheduled updates
- Incremental updates

All production collectors must use POST.

---

# Required Headers

```http
Content-Type: application/json
Accept: application/json
```

Never send form data.

Never send XML.

---

# Request Body Schema

```json
{
  "seriesid": [],
  "startyear": "",
  "endyear": "",
  "catalog": true,
  "calculations": true,
  "annualaverage": true,
  "registrationkey": ""
}
```

The optional fields (`catalog`, `calculations`, `annualaverage`) are Version 2 capabilities.

---

# Required Fields

| Field           | Required    |
| --------------- | ----------- |
| seriesid        | Yes         |
| startyear       | Yes         |
| endyear         | Yes         |
| registrationkey | Recommended |

---

# API Request Flow

```text
Read Series IDs

↓

Group Series

↓

Build POST Request

↓

Send HTTPS Request

↓

Receive JSON

↓

Validate

↓

Normalize

↓

Save Raw JSON

↓

Transform

↓

Save Clean Dataset
```

---

# JSON Response Pipeline

Never parse JSON directly into the database.

Pipeline must be:

```text
API

↓

raw_response.json

↓

Validator

↓

Parser

↓

Normalizer

↓

Final Dataset
```

Always preserve the raw response.

Never overwrite it.

---

# Raw Storage

```text
raw/

bls/

api/

year/

request_timestamp/

response.json
```

Example

```text
raw/bls/api/2024/2024-07-11T13-30-05Z/response.json
```

---

# Clean Storage

```text
processed/

bls/

api/

series_id/

year/

dataset.json
```

---

# Series Strategy

Never hardcode series IDs.

Series IDs must be loaded dynamically from:

```text
SERIES_REGISTRY.md
```

If a series is missing:

- Stop processing.
- Log the error.
- Do not guess.
- Do not construct IDs manually.

---

# Batch Strategy

Historical collection:

```text
Series

↓

Group into batches

↓

POST Request

↓

Receive JSON

↓

Repeat
```

Batch sizes must respect BLS Version 2 limits. Registered users can query up to **50 series per request** and **20 years per request**.

---

# Retry Strategy

Retry only for:

- HTTP 429
- HTTP 500
- Connection timeout
- Temporary network failure

Never retry:

- Invalid Series
- Bad Request
- Unauthorized

---

# Expected HTTP Status

| Code | Action              |
| ---- | ------------------- |
| 200  | Continue            |
| 202  | Retry Later         |
| 400  | Stop                |
| 401  | Configuration Error |
| 404  | Log Error           |
| 429  | Exponential Backoff |
| 500  | Retry               |

These status codes are documented by the BLS FAQ.

---

# JSON Validation Rules

Every response must contain:

```text
status

responseTime

Results

series
```

Reject the response if any required key is missing.

---

# Output Files

For every successful request save:

```text
request.json

response.json

normalized.json

validation_report.json

request.log
```

Never discard intermediate files.

---

# Logging

Every request must log:

```text
Request Timestamp

Series IDs

Endpoint

HTTP Status

Response Time

Retry Count

File Path

Validation Status
```

---

# AI Agent Rules

1. Use Version 2 only.
2. Use HTTPS.
3. Use POST for production.
4. Never hardcode Series IDs.
5. Save every raw JSON response.
6. Validate before parsing.
7. Normalize after validation.
8. Preserve original numeric values.
9. Never modify source JSON.
10. Store raw and processed data separately.
11. Respect API limits.
12. Retry only on transient failures.

---

# Dependencies

```text
URL_REGISTRY.md

↓

PROGRAM_REGISTRY.md

↓

SERIES_REGISTRY.md

↓

API_REGISTRY.md

↓

DATASET_REGISTRY.md
```

---

# Future Extensions

- Automatic Series Discovery
- Parallel Request Queue
- Incremental Update Worker
- Metadata Cache
- API Health Monitoring
- Change Detection
- Response Schema Versioning

---

# Version History

| Version | Date      | Description                                                  |
| ------- | --------- | ------------------------------------------------------------ |
| 1.0     | July 2026 | Initial implementation specification for BLS Public Data API |
