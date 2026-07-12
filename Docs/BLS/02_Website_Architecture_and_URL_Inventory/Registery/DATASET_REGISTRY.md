# DATASET_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Dataset Registry (Implementation Specification)

---

# Purpose

This registry is the master implementation specification for every dataset
that will be collected from the Bureau of Labor Statistics (BLS).

AI coding agents **must not discover datasets dynamically**.

Every dataset to be collected must first be registered here.

This registry tells the implementation:

- what to collect
- where to collect it
- which program owns it
- which registry files must be loaded
- what output files to create
- what pipeline to execute

---

# Dataset Processing Pipeline

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

API / HTML / PDF

        │

        ▼

Raw Dataset

        │

        ▼

Validation

        │

        ▼

Normalization

        │

        ▼

Processed Dataset
```

---

# Dataset Object Schema

Every dataset must follow the schema below.

```json
{
  "dataset_id": "",
  "program_id": "",
  "dataset_name": "",
  "enabled": true,
  "priority": "",
  "collection_method": [],
  "series_registry": "",
  "calendar_registry": "",
  "html_registry": "",
  "pdf_registry": "",
  "archive_registry": "",
  "output_directory": "",
  "raw_directory": "",
  "implementation_status": "",
  "last_verified": ""
}
```

---

# Dataset Registry

---

## DATASET-001

Dataset Name

```text
Consumer Price Index
```

Dataset ID

```text
BLS-DATASET-001
```

Program

```text
BLS-PROGRAM-001
```

Collection Methods

```text
API
HTML
PDF
```

Load Registries

```text
SERIES_REGISTRY.md

API_REGISTRY.md

HTML_REGISTRY.md

PDF_REGISTRY.md

CALENDAR_REGISTRY.md

ARCHIVE_REGISTRY.md
```

Raw Storage

```text
raw/bls/cpi/
```

Processed Storage

```text
processed/bls/cpi/
```

Output Files

```text
metadata.json

release.json

dataset.parquet

validation.json
```

Pipeline

```text
Read Registry

↓

Load Series IDs

↓

Download API Data

↓

Download HTML Release

↓

Download PDF Release

↓

Validate

↓

Normalize

↓

Store
```

Implementation

```text
Pending
```

---

## DATASET-002

Dataset

```text
Producer Price Index
```

Program

```text
BLS-PROGRAM-002
```

Methods

```text
API

HTML

PDF
```

Output

```text
processed/bls/ppi/
```

Implementation

```text
Pending
```

---

## DATASET-003

Dataset

```text
Employment Situation
```

Program

```text
BLS-PROGRAM-003
```

Methods

```text
HTML

PDF

API
```

Output

```text
processed/bls/employment/
```

Implementation

```text
Pending
```

---

## DATASET-004

Dataset

```text
Job Openings and Labor Turnover Survey
```

Program

```text
BLS-PROGRAM-004
```

Methods

```text
API

HTML

PDF
```

Output

```text
processed/bls/jolts/
```

---

## DATASET-005

Dataset

```text
Employment Cost Index
```

Program

```text
BLS-PROGRAM-005
```

Methods

```text
API

HTML

PDF
```

---

## DATASET-006

Dataset

```text
Real Earnings
```

Program

```text
BLS-PROGRAM-006
```

Methods

```text
API

HTML

PDF
```

---

## DATASET-007

Dataset

```text
Import and Export Price Indexes
```

Program

```text
BLS-PROGRAM-007
```

Methods

```text
API

HTML

PDF
```

---

## DATASET-008

Dataset

```text
Productivity and Costs
```

Program

```text
BLS-PROGRAM-008
```

Methods

```text
API

HTML

PDF
```

---

# Collection Method Rules

## API

Load

```text
API_REGISTRY.md
```

Read

```text
SERIES_REGISTRY.md
```

Build POST request.

Download raw JSON.

Save without modification.

---

## HTML

Load

```text
HTML_REGISTRY.md
```

Download page.

Save original HTML.

Extract only documented fields.

Do not infer missing values.

---

## PDF

Load

```text
PDF_REGISTRY.md
```

Download official PDF.

Preserve original file.

Generate extracted text separately.

Never overwrite the original PDF.

---

# Output Directory Standard

```text
data/

├── raw/

│   └── bls/

│       └── dataset_name/

│

└── processed/

    └── bls/

        └── dataset_name/
```

---

# Output File Standard

Every dataset collection must produce:

```text
request.json

response.json

release.html

release.pdf

metadata.json

normalized.json

validation.json

collector.log
```

If a source is not available (for example, no PDF for a specific release), record the missing artifact in `validation.json` instead of failing the entire pipeline.

---

# Dataset Execution Order

AI agents must process datasets in this order.

```text
1

Consumer Price Index

↓

2

Producer Price Index

↓

3

Employment Situation

↓

4

JOLTS

↓

5

Employment Cost Index

↓

6

Real Earnings

↓

7

Import Export Prices

↓

8

Productivity
```

Higher-priority datasets should complete before lower-priority ones.

---

# Agent Workflow

```text
Load DATASET_REGISTRY

↓

Select Dataset

↓

Load PROGRAM_REGISTRY

↓

Load SERIES_REGISTRY

↓

Load API / HTML / PDF Registry

↓

Download

↓

Save Raw

↓

Validate

↓

Normalize

↓

Save Processed

↓

Generate Validation Report
```

The BLS API supports JSON and XLSX outputs, GET for simple requests, and POST for production requests with one or more series and optional metadata. All historical requests are driven by **series IDs**, not dataset names.

---

# Failure Rules

Stop processing immediately if:

- Dataset ID is not registered.
- Program ID is missing.
- Required registry file cannot be loaded.
- Required Series ID is missing.
- API response validation fails.
- Output directory cannot be created.

Do **not** substitute undocumented URLs or guessed Series IDs.

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

HTML_REGISTRY.md

↓

PDF_REGISTRY.md

↓

ARCHIVE_REGISTRY.md

↓

CALENDAR_REGISTRY.md

↓

DATASET_REGISTRY.md

↓

Implementation Guide
```

---

# Version History

| Version | Date      | Description                                           |
| ------- | --------- | ----------------------------------------------------- |
| 1.0     | July 2026 | Initial implementation specification for BLS datasets |
