# 01_PIPELINE_IMPLEMENTATION.md

# Bitcoin Market Intelligence Dataset

## BLS Pipeline Implementation Guide

---

# Purpose

This document defines the complete implementation pipeline for the BLS module.

This is the execution blueprint that every AI coding agent must follow.

Do not invent workflows.

Do not change execution order.

Implement exactly as documented.

---

# Pipeline Architecture

```text id="m3g2qj"
Configuration

        │

        ▼

Registry Loader

        │

        ▼

Scheduler

        │

        ▼

Collector

        │

        ▼

Parser

        │

        ▼

Normalizer

        │

        ▼

Validator

        │

        ▼

Storage

        │

        ▼

Dataset Builder

        │

        ▼

Feature Engineering

        │

        ▼

AI Dataset
```

---

# Development Philosophy

The implementation must satisfy the following principles:

- Registry-driven.
- Configuration-first.
- Modular collectors.
- Idempotent execution.
- Immutable raw data.
- Reproducible datasets.
- Independent pipeline stages.
- Fail-safe execution.

Every stage must have a single responsibility.

---

# Pipeline Stages

```text id="8q1y0k"
Stage 1

Load Configuration

↓

Stage 2

Load Registry Files

↓

Stage 3

Generate Collection Queue

↓

Stage 4

Download Data

↓

Stage 5

Parse Source

↓

Stage 6

Normalize

↓

Stage 7

Validate

↓

Stage 8

Store

↓

Stage 9

Build Dataset

↓

Stage 10

Generate Features
```

---

# Module Layout

```text id="v3hks2"
pipeline/

├── config/

├── scheduler/

├── collectors/

├── parsers/

├── normalizers/

├── validators/

├── storage/

├── datasets/

├── features/

└── utils/
```

---

# Component Responsibilities

| Component       | Responsibility                 |
| --------------- | ------------------------------ |
| Scheduler       | Create collection jobs         |
| Collector       | Download raw data              |
| Parser          | Extract structured information |
| Normalizer      | Convert to unified schema      |
| Validator       | Verify correctness             |
| Storage         | Persist artifacts              |
| Dataset Builder | Merge normalized records       |
| Feature Builder | Produce ML-ready datasets      |

No component may perform another component's responsibility.

---

# Registry Loading

Pipeline startup sequence:

```text id="n7j3po"
Load PROJECT Configuration

↓

Load URL Registry

↓

Load Program Registry

↓

Load Dataset Registry

↓

Load Series Registry

↓

Load Calendar Registry

↓

Load Remaining Registries
```

Abort startup if any required registry cannot be loaded.

---

# Scheduler Workflow

The scheduler is responsible only for creating work items.

It must never download data.

Workflow

```text id="2n4y8r"
Read Calendar

↓

Read Archive

↓

Read RSS

↓

Generate Queue

↓

Assign Priority

↓

Dispatch Jobs
```

---

# Collection Workflow

Each work item executes independently.

```text id="g6p4zh"
Receive Job

↓

Resolve URL

↓

Download Resource

↓

Validate Response

↓

Store Raw File

↓

Forward To Parser
```

Collectors never parse downloaded content.

---

# Parsing Workflow

Each parser accepts exactly one input type.

```text id="vx9lq1"
HTML

↓

HTML Parser

↓

Normalized Object
```

```text id="5w2bmc"
PDF

↓

PDF Parser

↓

Normalized Object
```

```text id="q1z9na"
API JSON

↓

API Parser

↓

Normalized Object
```

```text id="90hwrx"
RSS XML

↓

RSS Parser

↓

Normalized Object
```

No parser may access storage directly.

---

# Normalization Workflow

Every parser output is converted into the Unified Schema.

```text id="a6u1ct"
Parser Output

↓

Schema Mapping

↓

Field Mapping

↓

Relationship Mapping

↓

Generate UUID

↓

Normalized Object
```

The normalized object must comply with `01_UNIFIED_SCHEMA.md`.

---

# Validation Workflow

Validation executes before persistence.

```text id="gh1m5d"
Schema Validation

↓

Required Fields

↓

Datatype Validation

↓

Duplicate Detection

↓

Relationship Validation

↓

Checksum Validation
```

If validation fails:

- Reject the object.
- Preserve raw artifacts.
- Generate `validation.json`.
- Write an error log.

---

# Storage Workflow

```text id="tb6p2y"
Raw

↓

Normalized

↓

Validated

↓

Processed

↓

Features
```

Each layer is write-once.

Historical files must never be overwritten.

---

# Dataset Build Workflow

```text id="j7n4ke"
Validated Objects

↓

Group By Dataset

↓

Sort Chronologically

↓

Merge

↓

Generate Dataset

↓

Export JSON

↓

Export CSV

↓

Export Parquet
```

---

# Milestones

## Milestone 1

Infrastructure

```text id="zt4fhs"
Configuration

Registry Loader

Logging

Storage
```

---

## Milestone 2

Collectors

```text id="0kq3mn"
API

HTML

PDF

RSS

Archive

Calendar
```

---

## Milestone 3

Parsers

```text id="d5v8pq"
API Parser

HTML Parser

PDF Parser

RSS Parser
```

---

## Milestone 4

Normalization

```text id="rx1j3o"
Unified Schema

Relationship Mapping

Metadata Generation
```

---

## Milestone 5

Validation

```text id="m4b9cy"
Schema

Integrity

Duplicates

Relationships
```

---

## Milestone 6

Dataset Builder

```text id="z6p2kl"
Dataset Generation

CSV Export

Parquet Export
```

---

## Milestone 7

Feature Engineering

```text id="e8q5wv"
Market Features

Time Features

Release Features
```

---

# Configuration Files

```text id="8f2kqp"
config/

settings.yaml

storage.yaml

pipeline.yaml

logging.yaml

scheduler.yaml
```

No values may be hardcoded in source code if they belong in configuration.

---

# Execution Rules

1. Load configuration first.
2. Load registries before starting the scheduler.
3. Execute collectors independently.
4. Parse only validated downloads.
5. Normalize every parser output.
6. Validate every normalized object.
7. Store only validated objects in processed datasets.
8. Generate datasets after all validation succeeds.
9. Build features only from processed datasets.
10. Preserve raw artifacts permanently.

---

# AI Agent Rules

1. Never bypass the registry.
2. Never skip validation.
3. Never modify raw files.
4. Never overwrite historical releases.
5. Keep pipeline stages independent.
6. Every stage must produce logs.
7. Every stage must be restartable.
8. Every collector must be idempotent.
9. Every parser must support deterministic output.
10. The pipeline must recover gracefully from partial failures.

---

# Pipeline Dependencies

```text id="r5d1xt"
Configuration

↓

Registry

↓

Scheduler

↓

Collectors

↓

Parsers

↓

Normalizers

↓

Validators

↓

Storage

↓

Dataset Builder

↓

Feature Engineering

↓

AI Model
```

---

# Implementation Checklist

| Component            | Status |
| -------------------- | ------ |
| Configuration Loader | ☐      |
| Registry Loader      | ☐      |
| Scheduler            | ☐      |
| API Collector        | ☐      |
| HTML Collector       | ☐      |
| PDF Collector        | ☐      |
| RSS Collector        | ☐      |
| Archive Collector    | ☐      |
| Calendar Collector   | ☐      |
| API Parser           | ☐      |
| HTML Parser          | ☐      |
| PDF Parser           | ☐      |
| RSS Parser           | ☐      |
| Normalizer           | ☐      |
| Validator            | ☐      |
| Storage Manager      | ☐      |
| Dataset Builder      | ☐      |
| Feature Builder      | ☐      |

---

# Version History

| Version | Date      | Description                                                                 |
| ------- | --------- | --------------------------------------------------------------------------- |
| 1.0     | July 2026 | Initial end-to-end pipeline implementation specification for the BLS module |
