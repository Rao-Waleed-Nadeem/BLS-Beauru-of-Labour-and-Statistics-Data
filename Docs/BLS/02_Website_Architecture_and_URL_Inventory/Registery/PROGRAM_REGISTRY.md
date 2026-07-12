# PROGRAM_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Program Registry (Implementation Specification)

---

# Purpose

This registry defines every BLS program that will be implemented.

Each program acts as the parent object for:

- URLs
- Release Calendars
- HTML Pages
- PDF Files
- API Series
- Historical Archives
- Dataset Schemas
- JSON Records
- Validation Rules

Every scraper, parser and validator must reference a Program ID.

---

# Program Object Architecture

```text
Program

│

├── Program ID

├── Name

├── Base URL

├── Release Calendar

├── News Releases

├── Historical Archive

├── HTML Pages

├── PDF Documents

├── API Series

├── Dataset Registry

├── JSON Output

├── Validation Rules

└── Future Extensions
```

---

# Registry Schema

Every program object must follow this schema.

```json
{
  "program_id": "",
  "name": "",
  "base_url": "",
  "category": "",
  "priority": "",
  "frequency": "",
  "calendar_registry": "",
  "archive_registry": "",
  "api_registry": "",
  "html_registry": "",
  "pdf_registry": "",
  "rss_registry": "",
  "dataset_registry": "",
  "implementation_status": "",
  "last_verified": ""
}
```

---

# Program Registry

---

## BLS-PROGRAM-001

### Consumer Price Index

Program ID

```
BLS-PROGRAM-001
```

Base URL

```
https://www.bls.gov/cpi/
```

Primary Release Page

```
https://www.bls.gov/bls/newsrels.htm
```

Release Schedule

```
https://www.bls.gov/schedule/
```

Related Registries

```
CALENDAR_REGISTRY

API_REGISTRY

HTML_REGISTRY

PDF_REGISTRY

ARCHIVE_REGISTRY

DATASET_REGISTRY
```

Primary Content

```
HTML

PDF

Tables

Charts

Historical Releases

Time Series
```

Expected Output

```
Dataset

Release Metadata

Publication Timestamp

Release URL

Historical Records
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-002

### Producer Price Index

Program ID

```
BLS-PROGRAM-002
```

Base URL

```
https://www.bls.gov/ppi/
```

Release Page

```
https://www.bls.gov/bls/newsrels.htm
```

Release Schedule

```
https://www.bls.gov/schedule/
```

Output Types

```
HTML

PDF

Tables

Charts

Historical Releases

Time Series
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-003

### Employment Situation

Program ID

```
BLS-PROGRAM-003
```

Program URL

```
https://www.bls.gov/bls/newsrels.htm
```

Release Schedule

```
https://www.bls.gov/schedule/
```

Outputs

```
Employment Report

HTML

PDF

Historical Releases

Tables

Charts
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-004

### JOLTS

Program ID

```
BLS-PROGRAM-004
```

Base URL

```
https://www.bls.gov/jlt/
```

Outputs

```
HTML

PDF

Historical Tables

Charts
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-005

### Employment Cost Index

Program ID

```
BLS-PROGRAM-005
```

Base URL

```
https://www.bls.gov/eci/
```

Outputs

```
HTML

PDF

Tables

Charts
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-006

### Real Earnings

Program ID

```
BLS-PROGRAM-006
```

Base URL

```
https://www.bls.gov/realearnings/
```

Outputs

```
HTML

PDF

Tables
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-007

### Import & Export Price Indexes

Program ID

```
BLS-PROGRAM-007
```

Base URL

```
https://www.bls.gov/mxp/
```

Outputs

```
HTML

PDF

Charts

Historical Tables
```

Implementation Status

```
Pending
```

---

## BLS-PROGRAM-008

### Productivity and Costs

Program ID

```
BLS-PROGRAM-008
```

Base URL

```
https://www.bls.gov/productivity/
```

Outputs

```
HTML

PDF

Tables

Historical Data
```

Implementation Status

```
Pending
```

---

# Common Output Directory

```text
bls/

programs/

├── cpi/

├── ppi/

├── employment/

├── jolts/

├── eci/

├── real_earnings/

├── import_export/

└── productivity/
```

---

# Expected JSON Directory

```text
data/

bls/

program_name/

year/

month/

release.json
```

---

# Standard JSON Filename

```text
YYYY-MM-DD_release.json
```

Example

```text
2024-07-11_release.json
```

---

# Registry Dependency Graph

```text
PROGRAM_REGISTRY

↓

URL_REGISTRY

↓

CALENDAR_REGISTRY

↓

HTML_REGISTRY

↓

PDF_REGISTRY

↓

API_REGISTRY

↓

ARCHIVE_REGISTRY

↓

DATASET_REGISTRY

↓

Implementation Guide
```

---

# AI Agent Rules

Before implementing any program:

1. Verify the Program ID.
2. Read URL_REGISTRY.md.
3. Load related CALENDAR_REGISTRY.md.
4. Load HTML_REGISTRY.md and PDF_REGISTRY.md.
5. Load API_REGISTRY.md if an API exists.
6. Do not hardcode undocumented URLs.
7. Every discovered URL must be added to URL_REGISTRY.md before use.
8. Every output JSON must conform to DATASET_REGISTRY.md.

---

# Version History

| Version | Date      | Description                                      |
| ------- | --------- | ------------------------------------------------ |
| 1.0     | July 2026 | Initial implementation-oriented Program Registry |
