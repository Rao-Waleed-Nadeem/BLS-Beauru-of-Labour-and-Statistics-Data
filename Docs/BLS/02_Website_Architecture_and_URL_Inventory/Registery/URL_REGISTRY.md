# URL_REGISTRY.md

# Bitcoin Market Intelligence Dataset

## BLS Master URL Registry

---

# Document Information

| Field         | Value                                                                  |
| ------------- | ---------------------------------------------------------------------- |
| Module        | U.S. Bureau of Labor Statistics (BLS)                                  |
| Document Type | Master URL Registry                                                    |
| Status        | Version 1.0                                                            |
| Depends On    | 01_System_Architecture.md, 02_Website_Architecture.md                  |
| Purpose       | Central registry of every official BLS URL used throughout the project |

---

# Purpose

The URL Registry serves as the authoritative inventory of all official
Bureau of Labor Statistics web resources used by this project.

Every URL referenced anywhere in the documentation must first appear
in this registry.

No implementation document should introduce new URLs that are not
registered here.

This registry becomes the single source of truth for:

- Developers
- Researchers
- AI Coding Agents
- Documentation Writers
- Future Maintainers

---

# Registry Design Principles

Every URL must satisfy at least one of the following:

✓ Official BLS webpage

✓ Official BLS publication

✓ Official archive

✓ Official API

✓ Official RSS feed

✓ Official calendar

✓ Official PDF resource

✓ Official machine-readable dataset

Third-party websites are never included.

---

# URL Classification

Every URL belongs to one category.

| Category | Description                |
| -------- | -------------------------- |
| ROOT     | Root website               |
| HUB      | Navigation hub             |
| PROGRAM  | Dataset landing page       |
| RELEASE  | Official news release      |
| CALENDAR | Release schedule           |
| ARCHIVE  | Historical releases        |
| API      | Machine-readable API       |
| RSS      | RSS feeds                  |
| PDF      | Official PDF documents     |
| DATA     | Downloadable datasets      |
| DOC      | Documentation              |
| SUPPORT  | Help / Developer resources |

---

# URL Priority Levels

| Priority | Meaning                 |
| -------- | ----------------------- |
| Critical | Required for production |
| High     | Frequently accessed     |
| Medium   | Supporting resource     |
| Low      | Optional reference      |

---

# Master URL Registry

| ID          | Category | Name                                           | Official URL                                         | Purpose                                                   | Priority | Status |
| ----------- | -------- | ---------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------- | -------- | ------ |
| BLS-URL-001 | ROOT     | BLS Homepage                                   | https://www.bls.gov/                                 | Root website for all Bureau of Labor Statistics resources | Critical | Active |
| BLS-URL-002 | HUB      | Economic News Releases                         | https://www.bls.gov/bls/newsrels.htm                 | Master index for all BLS economic news releases           | Critical | Active |
| BLS-URL-003 | HUB      | Release Schedules                              | https://www.bls.gov/schedule/news_release/           | Entry point for official release schedules                | Critical | Active |
| BLS-URL-004 | DOC      | Developer Portal                               | https://www.bls.gov/developers/                      | Public Data API documentation and developer resources     | Critical | Active |
| BLS-URL-005 | API      | Public Data API                                | https://api.bls.gov/                                 | Machine-readable access to BLS time-series data           | Critical | Active |
| BLS-URL-006 | HUB      | Inflation & Prices                             | https://www.bls.gov/bls/inflation.htm                | Navigation hub for inflation-related programs             | High     | Active |
| BLS-URL-007 | PROGRAM  | Consumer Price Index (CPI)                     | https://www.bls.gov/cpi/                             | CPI program landing page                                  | Critical | Active |
| BLS-URL-008 | PROGRAM  | Producer Price Index (PPI)                     | https://www.bls.gov/ppi/                             | PPI program landing page                                  | Critical | Active |
| BLS-URL-009 | PROGRAM  | Employment Situation                           | https://www.bls.gov/bls/newsrels.htm#latest-releases | Entry point to Employment Situation releases              | Critical | Active |
| BLS-URL-010 | PROGRAM  | Job Openings and Labor Turnover Survey (JOLTS) | https://www.bls.gov/jlt/                             | JOLTS program landing page                                | High     | Active |
| BLS-URL-011 | PROGRAM  | Employment Cost Index                          | https://www.bls.gov/eci/                             | ECI program landing page                                  | High     | Active |
| BLS-URL-012 | PROGRAM  | Real Earnings                                  | https://www.bls.gov/realearnings/                    | Real Earnings program                                     | High     | Active |
| BLS-URL-013 | PROGRAM  | Import and Export Price Indexes                | https://www.bls.gov/mxp/                             | Import/Export Prices program                              | High     | Active |
| BLS-URL-014 | PROGRAM  | Productivity                                   | https://www.bls.gov/productivity/                    | Productivity and Costs program                            | Medium   | Active |

---

# URL Identifier Rules

Every URL receives a permanent identifier.

Example:

BLS-URL-001

BLS-URL-002

BLS-URL-003

Identifiers must never change.

If a URL becomes obsolete:

Status → Deprecated

The identifier remains reserved forever.

---

# URL Lifecycle

Draft

↓

Verified

↓

Production

↓

Deprecated

↓

Archived

No URL should ever be removed from the registry.

Historical traceability must always be preserved.

---

# URL Ownership

Every registered URL should eventually be documented in exactly one of the
following registry files:

- DATASET_REGISTRY.md
- PROGRAM_REGISTRY.md
- API_REGISTRY.md
- RSS_REGISTRY.md
- PDF_REGISTRY.md
- HTML_REGISTRY.md
- ARCHIVE_REGISTRY.md
- CALENDAR_REGISTRY.md

The URL Registry acts as the central index linking all other registries.

---

# Change Management

Whenever BLS introduces:

- new datasets
- new programs
- new APIs
- new calendars
- new archives

the URL must first be added here before any implementation or documentation
is updated.

---

# Version History

| Version | Date      | Changes                              |
| ------- | --------- | ------------------------------------ |
| 1.0     | July 2026 | Initial Master URL Registry created. |
