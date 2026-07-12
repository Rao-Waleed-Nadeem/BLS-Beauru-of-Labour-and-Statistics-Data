# 02_DATASET_SPECIFICATIONS.md

# Bitcoin Market Intelligence Dataset

## BLS Dataset Specifications (Implementation Specification)

---

# Purpose

This document defines the **canonical specification for every BLS dataset** used by the Bitcoin Market Intelligence Dataset.

This is **not** a scraping guide.

This is **not** an API guide.

This document specifies exactly:

- what each dataset represents,
- what fields must be stored,
- how records are uniquely identified,
- how datasets relate to one another,
- how they are normalized after collection.

Every collector (API, HTML, PDF) must ultimately populate these dataset specifications.

---

# Standard Dataset Template

Every dataset in this document follows the same structure.

```text id="7md0ke"
Dataset Name

↓

Description

↓

Official Program

↓

Official Dataset

↓

Collection Sources

↓

Primary Keys

↓

Required Fields

↓

Optional Fields

↓

Relationships

↓

Release Frequency

↓

Market Impact

↓

Storage Location

↓

Validation Rules
```

---

# Dataset 01 — Consumer Price Index (CPI)

## Description

Measures changes in prices paid by consumers and is the primary inflation indicator watched by financial markets.

---

## Official Program

```text id="e6mxt8"
Consumer Price Index
```

---

## Collection Sources

```text id="nv9jfr"
API

HTML Release

PDF Release

Release Calendar

Archive
```

---

## Primary Key

```text id="jd2cqm"
series_id

+

year

+

period
```

---

## Required Fields

```json id="3y5mbn"
{
  "series_id": "",
  "year": "",
  "period": "",
  "period_name": "",
  "value": "",
  "publication_datetime": "",
  "reference_period": "",
  "seasonality": "",
  "footnotes": []
}
```

---

## Optional Fields

```text id="90vjlwm"
expected_value

previous_value

revised_value

surprise_value

revision_flag
```

If unavailable from official BLS sources, these fields must be stored as `null`.

---

## Relationships

```text id="tqkruw"
PROGRAM_REGISTRY

↓

DATASET_REGISTRY

↓

SERIES_REGISTRY

↓

Release Calendar

↓

Release Metadata
```

---

## Release Frequency

```text id="2bm0wk"
Monthly
```

---

## Market Impact

```text id="67g0a5"
Critical
```

---

## Storage

```text id="djlwmr"
processed/

bls/

datasets/

cpi/
```

---

## Validation Rules

- One record per series/year/period.
- Value must be numeric.
- Publication datetime required.
- Duplicate records are not allowed.

---

# Dataset 02 — Producer Price Index (PPI)

## Description

Measures changes in selling prices received by domestic producers.

---

## Collection Sources

```text id="r5w2g9"
API

HTML

PDF

Calendar

Archive
```

---

## Primary Key

```text id="ggrvmo"
series_id + year + period
```

---

## Required Fields

Same schema as CPI.

---

## Release Frequency

```text id="eckg1w"
Monthly
```

---

## Market Impact

```text id="kt1a5r"
Critical
```

---

## Storage

```text id="fxumg2"
processed/bls/datasets/ppi/
```

---

# Dataset 03 — Employment Situation

## Description

Official labor market release containing employment, unemployment and payroll statistics.

---

## Collection Sources

```text id="bb03a6"
API

HTML

PDF

Calendar

Archive
```

---

## Primary Key

```text id="95n7kv"
series_id + year + period
```

---

## Required Fields

```json id="bcdppn"
{
  "series_id": "",
  "year": "",
  "period": "",
  "value": "",
  "employment_type": "",
  "seasonality": "",
  "publication_datetime": ""
}
```

---

## Release Frequency

```text id="k3o4cl"
Monthly
```

---

## Market Impact

```text id="0vbmd2"
Critical
```

---

## Storage

```text id="u0tk9x"
processed/bls/datasets/employment/
```

---

# Dataset 04 — JOLTS

## Description

Job Openings and Labor Turnover Survey.

---

## Primary Key

```text id="bbtrg0"
series_id + year + period
```

---

## Required Fields

Same unified schema.

---

## Release Frequency

```text id="vrr5w8"
Monthly
```

---

## Market Impact

```text id="r0gf9m"
High
```

---

## Storage

```text id="ys5xgw"
processed/bls/datasets/jolts/
```

---

# Dataset 05 — Employment Cost Index (ECI)

## Description

Measures changes in labor costs independent of workforce composition.

---

## Primary Key

```text id="x1d0ew"
series_id + year + period
```

---

## Required Fields

Same unified schema.

---

## Release Frequency

```text id="3bty2e"
Quarterly
```

---

## Market Impact

```text id="8pxxjw"
High
```

---

## Storage

```text id="g2g9ha"
processed/bls/datasets/eci/
```

---

# Dataset 06 — Productivity and Costs

## Description

Measures labor productivity and unit labor costs.

---

## Primary Key

```text id="opkixl"
series_id + year + period
```

---

## Release Frequency

```text id="c6pk6q"
Quarterly
```

---

## Market Impact

```text id="r3zysr"
Medium
```

---

## Storage

```text id="r9odf2"
processed/bls/datasets/productivity/
```

---

# Dataset 07 — Real Earnings

## Description

Measures inflation-adjusted earnings of workers.

---

## Primary Key

```text id="d37ujb"
series_id + year + period
```

---

## Release Frequency

```text id="rqozsj"
Monthly
```

---

## Market Impact

```text id="88d1yf"
Medium
```

---

## Storage

```text id="3a6p5g"
processed/bls/datasets/real_earnings/
```

---

# Dataset 08 — Import / Export Price Indexes

## Description

Measures price changes for imported and exported goods and services.

---

## Primary Key

```text id="trtvt8"
series_id + year + period
```

---

## Release Frequency

```text id="rmng8q"
Monthly
```

---

## Market Impact

```text id="hgb3tb"
High
```

---

## Storage

```text id="40whr0"
processed/bls/datasets/import_export_prices/
```

---

# Common Dataset Relationships

```text id="e69lcw"
Program

↓

Dataset

↓

Series

↓

Release

↓

Calendar Event

↓

API Data

↓

HTML Data

↓

PDF Data

↓

Normalized Dataset

↓

Feature Engineering

↓

AI Model
```

---

# Common Validation Rules

Every dataset must satisfy:

```text id="gb74y5"
Primary Key Validation

↓

Schema Validation

↓

Numeric Validation

↓

Date Validation

↓

Duplicate Detection

↓

Relationship Validation

↓

Checksum Validation
```

If validation fails:

- Preserve raw source files.
- Reject normalization.
- Generate `validation.json`.
- Record the failure in `collector.log`.

---

# Dataset Output Standard

Every normalized dataset must produce:

```text id="s7lcq6"
dataset.json

metadata.json

validation.json

relationships.json
```

Optional outputs:

```text id="jyjlwm"
dataset.csv

dataset.parquet
```

These alternative formats must be generated from the canonical JSON dataset, not collected independently.

---

# AI Agent Rules

1. Never invent dataset fields.
2. Every dataset must follow the Unified Schema.
3. Preserve official BLS values exactly as published.
4. Store unavailable values as `null`.
5. Use the registered primary key for uniqueness.
6. Validate every dataset before persistence.
7. Keep dataset relationships synchronized with the registry.
8. Do not modify historical records after successful ingestion.
9. Store datasets only in the designated processed directory.
10. All downstream feature engineering must consume normalized datasets, never raw collector outputs.

---

# Dependencies

```text id="9o58sm"
01_UNIFIED_SCHEMA.md

↓

PROGRAM_REGISTRY.md

↓

DATASET_REGISTRY.md

↓

SERIES_REGISTRY.md

↓

Normalized Collectors

↓

Processed Dataset
```

---

# Version History

| Version | Date      | Description                                               |
| ------- | --------- | --------------------------------------------------------- |
| 1.0     | July 2026 | Initial implementation specification for all BLS datasets |
