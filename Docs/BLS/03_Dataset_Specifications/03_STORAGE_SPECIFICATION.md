# 03_STORAGE_SPECIFICATION.md

# Bitcoin Market Intelligence Dataset

## BLS Storage Specification (Implementation Specification)

---

# Purpose

This document defines the **official storage architecture** for the entire BLS module.

Every collector, parser, normalizer, validator and downstream AI pipeline **must** follow this storage specification.

No component may create its own folder structure.

No component may store files outside the directories defined in this document.

---

# Storage Architecture

```text id="q7n9xk"
Official Source

        │

        ▼

Collector

        │

        ▼

Raw Zone

        │

        ▼

Normalization

        │

        ▼

Validated Zone

        │

        ▼

Processed Zone

        │

        ▼

Feature Engineering

        │

        ▼

AI Dataset
```

---

# Storage Layers

| Layer      | Purpose                       | Editable |
| ---------- | ----------------------------- | -------- |
| Raw        | Original downloaded files     | No       |
| Normalized | Unified schema objects        | Yes      |
| Validated  | Verified normalized data      | Yes      |
| Processed  | Final datasets for AI         | Yes      |
| Features   | Model-ready features          | Yes      |
| Logs       | Collector and validation logs | Yes      |
| Metadata   | File metadata and lineage     | Yes      |

---

# Root Directory Structure

```text id="rsy8dq"
storage/

├── raw/

├── normalized/

├── validated/

├── processed/

├── features/

├── metadata/

├── logs/

└── backups/
```

---

# Raw Storage

Purpose

Store every downloaded file exactly as received.

Never modify raw files.

Structure

```text id="a4ckkb"
raw/

└── bls/

    ├── api/

    ├── html/

    ├── pdf/

    ├── rss/

    ├── archive/

    └── calendar/
```

---

# API Storage

```text id="z1zry0"
raw/

└── bls/

    └── api/

        └── dataset/

            └── year/

                response.json
```

Store the original JSON response returned by the BLS API before any transformation. The BLS API natively returns JSON (and Excel for some endpoints), so JSON is the canonical raw API format.

---

# HTML Storage

```text id="6e8hzb"
raw/

└── bls/

    └── html/

        └── program/

            └── year/

                release.html
```

---

# PDF Storage

```text id="pgw9zt"
raw/

└── bls/

    └── pdf/

        └── program/

            └── year/

                release.pdf
```

---

# RSS Storage

```text id="0aq31y"
raw/

└── bls/

    └── rss/

        └── feed/

            └── year/

                feed.xml
```

---

# Archive Storage

```text id="5kq5q0"
raw/

└── bls/

    └── archive/

        └── program/

            └── year/

                archive.html
```

---

# Calendar Storage

```text id="l0glqu"
raw/

└── bls/

    └── calendar/

        ├── calendar.html

        ├── calendar.ics

        └── events.json
```

---

# Normalized Storage

Purpose

Store unified schema objects after parsing.

```text id="jlwmu4"
normalized/

└── bls/

    └── dataset/

        └── year/

            normalized.json
```

---

# Validated Storage

Only validated data may enter this layer.

```text id="s79bhw"
validated/

└── bls/

    └── dataset/

        └── year/

            validated.json
```

---

# Processed Storage

Purpose

Final datasets consumed by feature engineering and machine learning.

```text id="2epofn"
processed/

└── bls/

    ├── cpi/

    ├── ppi/

    ├── employment/

    ├── jolts/

    ├── eci/

    ├── productivity/

    ├── real_earnings/

    └── import_export_prices/
```

Each dataset directory contains:

```text id="h5op0m"
dataset.json

dataset.csv

dataset.parquet

metadata.json

relationships.json

validation.json
```

The canonical processed object is JSON. CSV and Parquet are generated from the validated dataset, not collected directly. JSON preserves the full normalized schema, while Parquet is intended for efficient analytical workloads.

---

# Feature Storage

```text id="9m7k3v"
features/

└── bls/

    └── dataset/

        feature_set.parquet
```

---

# Metadata Storage

Every collected file generates metadata.

```text id="mxjlwm"
metadata/

└── bls/

    └── dataset/

        metadata.json
```

Schema

```json id="wqruhm"
{
  "uuid": "",
  "dataset_id": "",
  "program_id": "",
  "collector": "",
  "source_url": "",
  "download_timestamp": "",
  "checksum": "",
  "schema_version": ""
}
```

---

# Log Storage

```text id="1p9itq"
logs/

├── collector/

├── validator/

├── normalizer/

├── scheduler/

└── pipeline/
```

Each log file must include:

- Timestamp
- Component
- Status
- Duration
- Error message (if any)

---

# Backup Storage

```text id="y7kv2n"
backups/

└── YYYY/

    └── MM/

        └── DD/
```

Backups must never overwrite previous snapshots.

---

# File Naming Convention

Raw API

```text id="rv6cd5"
YYYY-MM-DD_api.json
```

Raw HTML

```text id="hhfjlwm"
YYYY-MM-DD_release.html
```

Raw PDF

```text id="3j0q2q"
YYYY-MM-DD_release.pdf
```

Raw RSS

```text id="mjlwm8"
YYYY-MM-DD_feed.xml
```

Normalized

```text id="tzr9zq"
normalized.json
```

Validated

```text id="vsjlwm"
validated.json
```

Processed

```text id="kpjlwm"
dataset.parquet
```

---

# File Formats

| Layer      | Format             |
| ---------- | ------------------ |
| Raw API    | JSON               |
| Raw HTML   | HTML               |
| Raw PDF    | PDF                |
| Raw RSS    | XML                |
| Calendar   | HTML / ICS / JSON  |
| Normalized | JSON               |
| Validated  | JSON               |
| Processed  | JSON, CSV, Parquet |
| Features   | Parquet            |
| Logs       | LOG / TXT          |
| Metadata   | JSON               |

---

# Compression Policy

| Layer      | Compression         |
| ---------- | ------------------- |
| Raw        | None                |
| Normalized | Optional GZIP       |
| Validated  | Optional GZIP       |
| Processed  | Parquet Compression |
| Backups    | ZIP                 |

---

# Versioning

Every stored object must include:

```json id="sjjlwm"
{
  "schema_version": "1.0.0",
  "collector_version": "1.0.0",
  "pipeline_version": "1.0.0"
}
```

Historical files must never be overwritten.

New versions create new files.

---

# Data Lifecycle

```text id="9ph1zt"
Download

↓

Raw

↓

Normalize

↓

Validate

↓

Process

↓

Generate Features

↓

Model Training

↓

Archive
```

---

# Retention Policy

| Layer      | Retention     |
| ---------- | ------------- |
| Raw        | Permanent     |
| Normalized | Permanent     |
| Validated  | Permanent     |
| Processed  | Permanent     |
| Features   | Regeneratable |
| Logs       | Permanent     |
| Metadata   | Permanent     |
| Backups    | Permanent     |

Historical BLS releases should always remain reproducible from the stored raw artifacts.

---

# Integrity Rules

Every stored file must generate:

```text id="jlwm7a"
SHA256

↓

Metadata

↓

Validation Report

↓

Relationship Index
```

---

# AI Agent Rules

1. Never modify files in the Raw layer.
2. Always preserve the original file exactly as downloaded.
3. Write only validated data to the Processed layer.
4. Generate metadata for every stored object.
5. Compute SHA256 for every downloaded file.
6. Keep raw, normalized, validated and processed data in separate directories.
7. Generate CSV and Parquet only from validated JSON.
8. Never overwrite historical releases.
9. Store timestamps in UTC while preserving the official publication timezone.
10. Follow this directory structure exactly.

---

# Dependencies

```text id="0jlwm8"
01_UNIFIED_SCHEMA.md

↓

02_DATASET_SPECIFICATIONS.md

↓

Collector

↓

Normalizer

↓

Validator

↓

03_STORAGE_SPECIFICATION.md

↓

Feature Engineering

↓

AI Model
```

---

# Version History

| Version | Date      | Description                                      |
| ------- | --------- | ------------------------------------------------ |
| 1.0     | July 2026 | Initial storage specification for the BLS module |
