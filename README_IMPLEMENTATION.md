# README_IMPLEMENTATION.md

# Bitcoin Market Intelligence Dataset

## BLS Module Implementation Master Guide

---

# Purpose

This document is the **master implementation guide** for the BLS module.

It defines:

- implementation roadmap
- milestone order
- development workflow
- AI agent workflow
- testing workflow
- validation workflow
- coding standards
- completion criteria

This document **must always be read before any implementation begins**.

It is the entry point for every developer and every AI coding agent.

---

# Golden Rule

The AI agent must never attempt to implement the entire project in one conversation.

Implementation is milestone-driven.

Each conversation implements exactly one milestone.

---

# Implementation Workflow

```text
Read README_IMPLEMENTATION.md

↓

Select Current Milestone

↓

Read Required Documentation

↓

Understand Scope

↓

Implement

↓

Run Tests

↓

Fix Issues

↓

Validate

↓

Commit

↓

Update Milestone Status

↓

Move To Next Milestone
```

Never skip a step.

---

# Documentation Reading Policy

The AI agent should never load the complete documentation.

Maximum documents per conversation:

```
1–3 markdown files
```

Only load documents required for the current milestone.

---

# Project Directory

```text
Docs/

00_Project_Governance.md

01_System_Architecture.md

02_Website_Architecture_and_URL_Inventory/

03_Dataset_Specifications/

04_Implementation_Guide/

05_Validation_And_Maintenance.md
```

---

# Development Principles

The implementation must always follow these principles.

- Registry-driven
- Configuration-first
- Modular
- Testable
- Reusable
- Deterministic
- Idempotent
- Immutable Raw Data
- Schema-first
- Fail-safe

---

# High Level Development Roadmap

```text
Foundation

↓

Infrastructure

↓

Registry Loader

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

Testing

↓

Production Ready
```

---

# Milestone Overview

| ID  | Milestone              | Status |
| --- | ---------------------- | ------ |
| M01 | Project Infrastructure | [x]    |
| M02 | Configuration System   | [x]    |
| M03 | Registry Loader        | [x]    |
| M04 | Scheduler              | [x]    |
| M05 | Calendar Collector     | ☑      |

| M06 | Archive Collector | ☐ |
| M07 | RSS Collector | ☐ |
| M08 | HTML Collector | ☐ |
| M09 | PDF Collector | ☐ |
| M10 | API Collector | ☐ |
| M11 | Parser Framework | ☐ |
| M12 | HTML Parser | ☐ |
| M13 | PDF Parser | ☐ |
| M14 | RSS Parser | ☐ |
| M15 | API Parser | ☐ |
| M16 | Unified Normalizer | ☐ |
| M17 | Validation Engine | ☐ |
| M18 | Storage Manager | ☐ |
| M19 | Dataset Builder | ☐ |
| M20 | Feature Engineering | ☐ |
| M21 | Historical Backfill | ☐ |
| M22 | Incremental Updates | ☐ |
| M23 | End-to-End Testing | ☐ |
| M24 | Production Deployment | ☐ |

---

# Milestone Template

Every milestone follows the same structure.

---

## Objective

What needs to be implemented.

---

## Required Documentation

Exactly which markdown files must be read.

Maximum:

```
3 files
```

---

## Expected Output

Files that must be created.

---

## Acceptance Criteria

Conditions required before the milestone is complete.

---

## Tests

Required tests.

---

## Completion

Mark milestone completed.

Proceed to the next milestone.

---

# Detailed Milestones

---

# M01 — Project Infrastructure

## Read

```
00_Project_Governance.md

01_PIPELINE_IMPLEMENTATION.md

03_STORAGE_SPECIFICATION.md
```

## Implement

- Project folder structure
- Python package structure
- Config folder
- Logging folder
- Storage folders
- Environment setup
- Base utilities

## Do Not Implement

- Collectors
- Parsers
- API logic

## Output

Working project skeleton.

---

# M02 — Configuration System

## Read

```
00_Project_Governance.md

01_PIPELINE_IMPLEMENTATION.md
```

Implement

- settings.yaml
- pipeline.yaml
- storage.yaml
- scheduler.yaml
- logging.yaml

---

# M03 — Registry Loader

## Read

```
URL_REGISTRY.md

PROGRAM_REGISTRY.md

DATASET_REGISTRY.md
```

Implement

Registry reader.

Validation.

Registry models.

Registry cache.

---

# M04 — Scheduler

## Read

```
CALENDAR_REGISTRY.md

01_PIPELINE_IMPLEMENTATION.md

02_DATA_COLLECTION.md
```

Implement

Job queue.

Task scheduler.

Priority system.

---

# M05 — Calendar Collector

## Read

```
CALENDAR_REGISTRY.md

02_DATA_COLLECTION.md

05_Validation_And_Maintenance.md
```

Implement

Calendar downloader.

Calendar parser.

Queue generation.

---

# M06 — Archive Collector

## Read

```
ARCHIVE_REGISTRY.md

02_DATA_COLLECTION.md

05_Validation_And_Maintenance.md
```

---

# M07 — RSS Collector

## Read

```
RSS_REGISTRY.md

02_DATA_COLLECTION.md

05_Validation_And_Maintenance.md
```

---

# M08 — HTML Collector

## Read

```
HTML_REGISTRY.md

02_DATA_COLLECTION.md

05_Validation_And_Maintenance.md
```

---

# M09 — PDF Collector

## Read

```
PDF_REGISTRY.md

02_DATA_COLLECTION.md

05_Validation_And_Maintenance.md
```

---

# M10 — API Collector

## Read

```
API_REGISTRY.md

SERIES_REGISTRY.md

02_DATA_COLLECTION.md
```

---

# M11–M15 — Parsers

Read only the registry relevant to the parser plus:

```
01_UNIFIED_SCHEMA.md

02_DATASET_SPECIFICATIONS.md
```

---

# M16 — Normalizer

Read

```
01_UNIFIED_SCHEMA.md

02_DATASET_SPECIFICATIONS.md

01_PIPELINE_IMPLEMENTATION.md
```

---

# M17 — Validator

Read

```
05_Validation_And_Maintenance.md

01_UNIFIED_SCHEMA.md

02_DATASET_SPECIFICATIONS.md
```

---

# M18 — Storage Manager

Read

```
03_STORAGE_SPECIFICATION.md

01_PIPELINE_IMPLEMENTATION.md
```

---

# M19 — Dataset Builder

Read

```
02_DATASET_SPECIFICATIONS.md

03_STORAGE_SPECIFICATION.md

01_PIPELINE_IMPLEMENTATION.md
```

---

# M20 — Feature Engineering

Read

```
02_DATASET_SPECIFICATIONS.md

03_STORAGE_SPECIFICATION.md
```

---

# M21 — Historical Backfill

Read

```
02_DATA_COLLECTION.md

05_Validation_And_Maintenance.md
```

Run complete collection from:

```
2020 → Current
```

---

# M22 — Incremental Updates

Enable scheduler.

Daily update mode.

---

# M23 — End-to-End Testing

Verify:

- Complete pipeline
- Storage
- Dataset generation
- Validation
- Duplicate detection
- Missing release detection

---

# M24 — Production Deployment

Prepare production configuration.

Enable monitoring.

Enable backups.

Freeze schema version.

---

# AI Agent Conversation Rules

Before writing any code, the AI agent must:

1. Read this README.
2. Determine the active milestone.
3. Read only the required documentation.
4. Ask for clarification if documentation conflicts.
5. Implement only the current milestone.
6. Do not continue to the next milestone unless instructed.

---

# Definition of Done (Per Milestone)

A milestone is complete only if:

- All required functionality is implemented.
- Code follows project structure.
- Unit tests pass.
- Integration tests (if applicable) pass.
- No linting or type-checking errors.
- Documentation remains consistent.
- No regression is introduced.

---

# Testing Strategy

Each milestone must include:

1. Unit Tests
2. Integration Tests (where applicable)
3. Manual Verification
4. Regression Check (for modified components)

No milestone is considered complete without testing.

---

# Version Control Workflow

For each milestone:

```text
Create Branch

↓

Implement

↓

Run Tests

↓

Fix Issues

↓

Commit

↓

Merge

↓

Tag Milestone
```

Suggested commit format:

```
feat(bls): implement M05 calendar collector

fix(bls): resolve validator schema issue

refactor(bls): improve registry loader
```

---

# Change Management

If documentation changes:

1. Update documentation first.
2. Review impacted milestones.
3. Re-run affected tests.
4. Continue implementation.

Never change code first and documentation later.

---

# Project Completion Checklist

- [ ] All milestones completed
- [ ] All tests passing
- [ ] Historical backfill completed
- [ ] Incremental updates working
- [ ] Validation reports generated
- [ ] Monitoring enabled
- [ ] Production configuration complete
- [ ] Documentation synchronized

---

# Future Modules

This implementation workflow is reusable.

The same roadmap can be used for:

- Federal Reserve
- SEC
- Binance
- Coinbase
- Other Tier-1 sources

Only the registry files, schemas, and source-specific collectors need to change.

---

# Version History

| Version | Date      | Description                                            |
| ------- | --------- | ------------------------------------------------------ |
| 1.0     | July 2026 | Initial master implementation guide for the BLS module |
