# 03_OPERATIONS_AND_DEPLOYMENT.md

# Bitcoin Market Intelligence Dataset

## BLS Operations & Deployment Guide (Implementation Specification)

---

# Purpose

This document defines how the BLS pipeline operates after implementation.

It covers:

- Pipeline execution
- Monitoring
- Logging
- Error handling
- Retry policies
- Validation
- Testing
- Deployment
- Maintenance

This document does **not** describe scraping logic.

It describes how to operate the completed system reliably.

---

# Operational Architecture

```text
Configuration

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

Monitoring

↓

Logs

↓

Alerts
```

Every component must operate independently.

---

# Pipeline Execution Modes

The pipeline supports three execution modes.

---

## Mode 1

Historical Backfill

```text
Start

↓

Calendar Discovery

↓

Archive Discovery

↓

Historical Collection

↓

Normalization

↓

Validation

↓

Dataset Generation

↓

Completed
```

Used only once to build the historical dataset (2020 → Current).

---

## Mode 2

Incremental Update

```text
Scheduler

↓

Calendar Check

↓

RSS Check

↓

New Release

↓

Collection

↓

Processing

↓

Dataset Update
```

Runs automatically after the historical backfill is complete.

---

## Mode 3

Recovery

```text
Read Failed Jobs

↓

Retry Queue

↓

Reprocess

↓

Validation

↓

Complete
```

Used only for failed jobs.

---

# Scheduler Operations

The scheduler is the only component responsible for starting collection jobs.

Responsibilities

- Read release calendar.
- Check RSS feeds.
- Check archive updates.
- Generate collection jobs.
- Dispatch jobs.
- Monitor job completion.

The scheduler must never parse or normalize data.

---

# Job Lifecycle

```text
Pending

↓

Queued

↓

Running

↓

Downloaded

↓

Parsed

↓

Normalized

↓

Validated

↓

Stored

↓

Completed
```

Failure path

```text
Running

↓

Failed

↓

Retry Queue

↓

Running
```

---

# Logging

Every pipeline stage must create logs.

Directory

```text
logs/

├── scheduler/

├── collectors/

├── parsers/

├── normalizers/

├── validators/

├── storage/

├── datasets/

└── pipeline/
```

Each log entry must contain

```text
Timestamp

Component

Job ID

Program ID

Dataset ID

Series ID

Source URL

Execution Time

Status

Message
```

---

# Error Classification

Errors are divided into four categories.

## Category 1

Network Errors

Examples

```text
Timeout

Connection Reset

DNS Failure

Temporary Network Failure
```

Action

Retry.

---

## Category 2

HTTP Errors

Retry

```text
429

500

502

503

504
```

Do Not Retry

```text
400

401

403

404

415
```

The BLS API documents common HTTP responses, including `429 Too Many Requests` and `500` server errors, which should be handled through controlled retry logic rather than immediate repeated requests.

---

## Category 3

Data Errors

Examples

```text
Invalid JSON

Missing Fields

Invalid HTML

Corrupted PDF

Schema Failure
```

Action

Reject the object.

Keep the original raw file.

Generate validation report.

---

## Category 4

Configuration Errors

Examples

```text
Missing Registry

Missing Configuration

Invalid Path

Invalid Dataset ID
```

Action

Abort startup.

Do not continue.

---

# Retry Strategy

Retry only transient failures.

Policy

```text
Attempt 1

↓

30 seconds

↓

Attempt 2

↓

60 seconds

↓

Attempt 3

↓

120 seconds

↓

Failed
```

Maximum retries

```text
3
```

After three failures

```text
Move Job

↓

Failed Queue

↓

Manual Review
```

The implementation should respect BLS API usage limits (including request-rate limits and daily quotas) and use exponential backoff when throttled instead of aggressive retries.

---

# Validation Operations

Validation occurs after normalization.

Pipeline

```text
Schema

↓

Datatype

↓

Relationships

↓

Duplicate Detection

↓

Checksum

↓

Complete
```

Invalid objects must never enter the processed dataset.

---

# Health Monitoring

Every component must expose its operational status.

Monitor

```text
Collector Status

Parser Status

Queue Size

Jobs Running

Jobs Failed

Validation Success

Storage Usage

Pipeline Duration
```

Generate a health report after every execution cycle.

---

# Testing Strategy

The implementation must include the following test categories.

## Unit Tests

Test

- Collector
- Parser
- Normalizer
- Validator
- Storage Manager

---

## Integration Tests

Verify

```text
Collector

↓

Parser

↓

Normalizer

↓

Validator

↓

Storage
```

---

## End-to-End Tests

Verify

```text
Calendar

↓

Collection

↓

Normalization

↓

Validation

↓

Dataset

↓

Feature Generation
```

The pipeline is considered successful only if the complete workflow finishes without validation failures.

---

# Deployment Architecture

```text
config/

↓

pipeline/

↓

storage/

↓

logs/

↓

scheduler/

↓

run_pipeline
```

Deployment must be configuration-driven.

No environment-specific values may be hardcoded.

---

# Startup Sequence

```text
Load Configuration

↓

Load Registries

↓

Validate Configuration

↓

Initialize Scheduler

↓

Initialize Storage

↓

Start Collectors

↓

Wait For Jobs
```

Abort startup immediately if required registries cannot be loaded.

---

# Shutdown Procedure

```text
Stop Scheduler

↓

Complete Running Jobs

↓

Flush Logs

↓

Write Metadata

↓

Close Storage

↓

Shutdown
```

Never terminate a running download without recording its state.

---

# Maintenance Tasks

Run periodically:

- Verify registry consistency.
- Verify storage integrity.
- Verify checksums.
- Rebuild metadata index if required.
- Archive completed logs.
- Remove expired temporary files only.

Raw BLS data must never be deleted.

---

# Disaster Recovery

Recovery sequence

```text
Load Metadata

↓

Load Failed Queue

↓

Restore Scheduler

↓

Resume Jobs

↓

Validate Outputs
```

Recovery must resume from the last successful checkpoint.

---

# Operational Checklist

| Component       | Verify |
| --------------- | ------ |
| Configuration   | ☐      |
| Registries      | ☐      |
| Scheduler       | ☐      |
| Collectors      | ☐      |
| Parsers         | ☐      |
| Normalizers     | ☐      |
| Validators      | ☐      |
| Storage         | ☐      |
| Dataset Builder | ☐      |
| Logs            | ☐      |
| Monitoring      | ☐      |
| Backups         | ☐      |

Pipeline deployment is complete only when every checklist item passes.

---

# AI Agent Rules

1. Never start collectors before registries are validated.
2. Never bypass validation.
3. Never overwrite historical datasets.
4. Retry only transient failures.
5. Preserve every raw artifact.
6. Write logs for every pipeline stage.
7. Stop the pipeline immediately on configuration errors.
8. Generate health reports after every execution.
9. Resume from checkpoints after failures.
10. Keep every pipeline stage isolated and independently testable.

---

# Dependencies

```text
01_PIPELINE_IMPLEMENTATION.md

↓

02_DATA_COLLECTION.md

↓

03_OPERATIONS_AND_DEPLOYMENT.md

↓

Production Pipeline
```

---

# Version History

| Version | Date      | Description                                                           |
| ------- | --------- | --------------------------------------------------------------------- |
| 1.0     | July 2026 | Initial operational and deployment specification for the BLS pipeline |
