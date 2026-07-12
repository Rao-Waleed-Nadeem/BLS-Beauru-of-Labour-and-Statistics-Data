# AGENT_GUIDE.md

# Bitcoin Market Intelligence Dataset
## AI Agent Operating Manual

---

# Purpose

This document defines the **standard operating procedure (SOP)** for every AI coding agent working on this project.

It is **generic** and reusable across all milestones.

Every milestone must follow the exact same workflow.

This document is **NOT** project documentation.

This document explains **how implementation is performed**.

---

# Golden Rules

The AI agent MUST follow these rules throughout the project.

1. Never implement more than one milestone in a single conversation.
2. Never read more than the documentation required for the current milestone.
3. Never assume undocumented behavior.
4. Never modify completed milestones unless explicitly instructed.
5. Never skip testing.
6. Never skip self-review.
7. Never continue to the next milestone automatically.
8. Never change project architecture without approval.
9. Never delete existing functionality.
10. Stop immediately after completing the assigned milestone.

---

# Standard Workflow

Every milestone follows this workflow.

```text
Read README_IMPLEMENTATION.md

↓

Identify Current Milestone

↓

Read Required Documents

↓

Understand Requirements

↓

Implementation Plan

↓

Wait For Approval

↓

Implement

↓

Self Review

↓

Testing

↓

Bug Fixes

↓

Final Review

↓

Update Documentation

↓

Commit

↓

Stop
```

Never change this workflow.

---

# Standard Conversation Flow

Each milestone consists of **eight phases**.

---

# Phase 1 — Planning

## User Command

```text
Current Milestone:

<Milestone Name>

Read ONLY:

1.
2.
3.

Do not read any other files.

Do not write code.

Study the documentation.

Understand the architecture.

Prepare a complete implementation plan.

Your response must include:

• Understanding of the milestone

• Components involved

• Dependencies

• Files to create

• Files to modify

• Folder structure

• Risks

• Assumptions

Wait for my approval before writing code.
```

Expected Output

- Implementation plan
- Architecture understanding
- File list
- No code

---

# Phase 2 — Approval

User reviews the implementation plan.

If approved:

```text
Implementation Approved.

Proceed with coding.

Implement ONLY this milestone.

Do not implement future milestones.

Stop immediately after completion.
```

---

# Phase 3 — Implementation

During implementation the AI agent must:

- Follow documentation exactly.
- Keep code modular.
- Use Python typing.
- Use logging.
- Follow project structure.
- Use configuration files.
- Avoid hardcoded values.
- Keep components independent.

Expected Output

Working implementation.

---

# Phase 4 — Self Review

## User Command

```text
Review your implementation.

Check:

Architecture

Documentation Compliance

Folder Structure

Naming Convention

Coding Standards

Missing Files

Extra Files

Possible Bugs

Future Milestone Leakage

Generate a review report.

Do not modify code.
```

Expected Output

Self-review report.

---

# Phase 5 — Bug Fixing

## User Command

```text
Fix ONLY the issues identified during review.

Do not refactor unrelated code.

Do not improve code outside the current milestone.

Explain every modification.
```

Expected Output

Updated implementation.

---

# Phase 6 — Testing

## User Command

```text
Create and execute tests for the current milestone.

Verify:

Functionality

Imports

Configuration

Logging

Storage

Validation

Summarize the test results.

Stop after testing.
```

Expected Output

Test report.

---

# Phase 7 — Final Validation

## User Command

```text
Verify that the milestone satisfies every requirement.

Check:

Documentation Compliance

Acceptance Criteria

Tests

Architecture

Project Standards

Generate a completion report.

Do not modify code.
```

Expected Output

Completion report.

---

# Phase 8 — Documentation Update

After every completed milestone the documentation must be updated.

The AI agent must update:

README_IMPLEMENTATION.md

Only the milestone status section.

Example

Before

```text
M05 Calendar Collector      ☐
```

After

```text
M05 Calendar Collector      ☑ Completed
```

If progress tracking exists:

```text
Progress

Completed: 5 / 24

Remaining: 19

Completion

20.8%
```

---

# Milestone Update Rules

After completing every milestone:

Update:

- Status
- Completion Date
- Version
- Notes
- Next Milestone

Example

```text
Milestone

M05

Status

Completed

Completion Date

YYYY-MM-DD

Version

1.0

Notes

Calendar collector implemented successfully.

Next

M06 Archive Collector
```

---

# Version Update Rules

Every completed milestone increases the internal version.

Example

```text
0.1

↓

0.2

↓

0.3

↓

...

↓

1.0
```

Major version changes occur only after production deployment.

---

# Git Workflow

Every milestone follows:

```text
Create Branch

↓

Implement

↓

Review

↓

Testing

↓

Fixes

↓

Documentation Update

↓

Commit

↓

Merge
```

Commit message format

```text
feat(bls): implement M05 calendar collector

fix(bls): resolve validator issue

refactor(bls): improve storage manager

docs(bls): update implementation progress

test(bls): add parser tests
```

---

# Definition of Done

A milestone is complete only if:

☐ Documentation followed

☐ Code implemented

☐ Tests passing

☐ No lint errors

☐ No type errors

☐ Self-review completed

☐ Documentation updated

☐ README updated

☐ Progress updated

☐ Ready for next milestone

---

# Progress Tracker

Example

```text
Milestone

M01 Infrastructure

Status

Completed

Date

2026-07-12

Progress

1 / 24

4.2%

Version

0.1
```

---

# Milestone Summary Template

After every milestone generate:

```text
Milestone Summary

Name

Status

Files Created

Files Modified

Components Implemented

Tests Executed

Known Issues

Future Improvements

Documentation Updated

Next Milestone
```

---

# Generic Completion Prompt

Use this after every milestone.

```text
The milestone implementation is complete.

Perform a complete verification.

Tasks

1. Review implementation.

2. Verify documentation compliance.

3. Verify architecture.

4. Verify coding standards.

5. Verify testing.

6. Verify project structure.

7. Verify configuration.

8. Verify logging.

9. Verify storage.

10. Verify acceptance criteria.

Generate a final completion report.

Update README_IMPLEMENTATION.md progress.

Update milestone status.

Update version.

Suggest the next milestone.

Stop after completion.
```

---

# Generic Bug Fix Prompt

```text
Fix only the reported issues.

Do not change architecture.

Do not refactor unrelated modules.

Do not implement future milestones.

Explain every change.

Run affected tests again.

Update documentation if required.

Stop after fixing.
```

---

# Generic Documentation Update Prompt

```text
Update project documentation after completing the milestone.

Update only:

README_IMPLEMENTATION.md

Update:

Completed milestone

Progress percentage

Completed count

Remaining count

Completion date

Version

Next milestone

Do not modify any other documentation unless implementation changed its behavior.

Generate a documentation update summary.
```

---

# Generic Review Checklist

Every milestone must satisfy:

- Documentation followed
- Architecture preserved
- Folder structure correct
- Registry driven
- Configuration driven
- Logging enabled
- Type hints used
- Error handling implemented
- Tests passing
- Documentation updated

---

# AI Agent Stop Rule

After completing the milestone:

DO NOT

- Start another milestone.
- Refactor unrelated modules.
- Optimize future code.
- Add extra features.
- Read additional documentation.

Instead:

1. Produce completion report.
2. Update documentation.
3. Wait for the next instruction.

---

# Next Milestone Rule

The next milestone begins only when the user explicitly provides:

- Milestone ID
- Required documentation
- Approval to proceed

Until then, no further implementation may occur.

---

# End of Guide

This guide is the **standard operating procedure** for every milestone in the Bitcoin Market Intelligence Dataset project.

It is reusable across all modules (BLS, Federal Reserve, SEC, Binance, Coinbase, etc.) and ensures a consistent implementation, review, testing, and documentation process from project start to production deployment.