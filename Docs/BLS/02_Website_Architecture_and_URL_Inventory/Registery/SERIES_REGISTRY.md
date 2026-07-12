# SERIES_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Series Registry (Implementation Specification)

---

# Purpose

This registry is the **master source of truth** for every BLS Series ID used by this project.

The AI agent **must never hardcode Series IDs inside source code**.

Every API request must load Series IDs from this registry.

This registry controls:

- API Requests
- Historical Backfill
- Incremental Updates
- Validation
- Dataset Mapping
- Feature Engineering

---

# Dependency Flow

```text
PROGRAM_REGISTRY

        │

        ▼

DATASET_REGISTRY

        │

        ▼

SERIES_REGISTRY

        │

        ▼

API Request Builder

        │

        ▼

Raw JSON

        │

        ▼

Normalizer

        │

        ▼

Processed Dataset
```

---

# Registry Schema

Every series must follow this schema.

```json
{
  "series_id": "",
  "program_id": "",
  "dataset_id": "",
  "title": "",
  "survey": "",
  "frequency": "",
  "seasonal_adjustment": "",
  "units": "",
  "collection_method": "API",
  "enabled": true,
  "priority": "",
  "storage_path": "",
  "implementation_status": ""
}
```

---

# Agent Workflow

```text
Load PROGRAM_REGISTRY

↓

Load DATASET_REGISTRY

↓

Load SERIES_REGISTRY

↓

Build POST Request

↓

Call BLS API

↓

Validate JSON

↓

Store Raw Response

↓

Normalize

↓

Store Final Dataset
```

---

# API Endpoint

Always use

```text
https://api.bls.gov/publicAPI/v2/timeseries/data/
```

Method

```text
POST
```

Headers

```http
Content-Type: application/json
Accept: application/json
```

---

# Series Registry

---

## SERIES-001

Series ID

```text
CUUR0000SA0
```

Title

```text
Consumer Price Index for All Urban Consumers (CPI-U): All Items
```

Program

```text
BLS-PROGRAM-001
```

Dataset

```text
BLS-DATASET-001
```

Priority

```text
Critical
```

Collection Method

```text
API
```

Storage

```text
raw/bls/cpi/

processed/bls/cpi/
```

API Payload

```json
{
  "seriesid": ["CUUR0000SA0"],
  "startyear": "2020",
  "endyear": "2026"
}
```

---

## SERIES-002

Series ID

```text
CUSR0000SA0
```

Title

```text
Consumer Price Index (Seasonally Adjusted)
```

Program

```text
BLS-PROGRAM-001
```

Priority

```text
High
```

---

## SERIES-003

Series ID

```text
LNS14000000
```

Title

```text
Unemployment Rate
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

## SERIES-004

Series ID

```text
CES0000000001
```

Title

```text
Total Nonfarm Employment
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

# Request Builder Rules

For every request

```text
Load Series

↓

Validate Series

↓

Group Series

↓

Create POST Payload

↓

Send Request

↓

Save Raw JSON
```

Never manually type Series IDs inside Python code.

Always load them from this registry.

---

# Batch Rules

Maximum batch size must follow BLS API limits.

```text
Batch

↓

Series 1

Series 2

Series 3

...

Series N
```

If the registry exceeds one request,

split into multiple requests automatically.

Registered API users may request up to **50 series IDs per request**, while historical requests have year limits that should be respected by the request builder.

---

# JSON Validation

Every returned series must match

```text
Requested Series ID

↓

Returned Series ID
```

If mismatch

```text
Reject Response
```

Never continue processing.

---

# Required JSON Keys

Validate

```text
status

Results

series

seriesID

data
```

If any key is missing

```text
Validation Failed
```

---

# Storage Standard

Raw

```text
raw/

bls/

series/

SERIES_ID/

YYYY/

response.json
```

Processed

```text
processed/

bls/

series/

SERIES_ID/

dataset.parquet
```

---

# Series Update Policy

Historical Collection

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

Incremental Updates

```text
Release Calendar

↓

Release Detected

↓

API Request

↓

Store

↓

Validate
```

---

# Error Handling

Stop processing if

- Series ID is missing.
- Series ID is duplicated.
- API returns "Series does not exist".
- API returns empty dataset.
- Returned Series ID differs from requested Series ID.

Do not substitute another Series ID.

---

# AI Agent Rules

1. Never hardcode Series IDs.
2. Load only from SERIES_REGISTRY.md.
3. Use POST requests.
4. Save original JSON.
5. Validate returned Series ID.
6. Split large requests automatically.
7. Store raw and processed data separately.
8. Log every request.
9. Retry only transient failures.
10. Never modify original API values.

---

# Future Expansion

Future versions of this registry should include:

- Additional CPI component Series IDs
- Additional PPI Series IDs
- JOLTS Series IDs
- Employment Cost Index Series IDs
- Productivity Series IDs
- Import/Export Price Series IDs
- Series metadata cache
- Automatic Series validation

---

# Version History

| Version | Date      | Description                                                  |
| ------- | --------- | ------------------------------------------------------------ |
| 1.0     | July 2026 | Initial implementation specification for BLS Series Registry |
