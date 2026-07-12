# 02_Website_Architecture_and_URL_Inventory.md

# Table of Contents

1. Purpose

2. Website Overview

3. Website Architecture

4. Navigation Hierarchy

5. Domain Structure

6. Official Entry Points

7. Website Components

8. URL Registry

9. Release Calendar Architecture

10. Dataset Landing Pages

11. Historical Archives

12. News Release Pages

13. Machine Readable Sources

14. PDF Resources

15. HTML Resources

16. RSS Resources

17. Developer Resources

18. URL Priority Classification

19. URL Relationships

20. Dataset Dependency Map

21. URL Validation Rules

22. Future Expansion

23. Version History

```

---

# Why I changed it

Instead of immediately listing URLs,

we first explain

> How the website itself works.

Only then do we document every URL.

This makes implementation much easier.

---

# Section 1

## Purpose

Explain that this document defines the official website architecture of BLS.

It does **not** describe scraping.

It only documents where information exists.

---

# Section 2

## Website Overview

Here explain

```

BLS

↓

Official Government Website

↓

Economic Programs

↓

Economic News Releases

↓

Historical Archives

↓

Developer APIs

↓

Statistics Databases

````

No URLs yet.

Only concepts.

---

# Section 3

## Website Architecture

Create a complete hierarchy.

Example

```text
bls.gov

│

├── About BLS

├── Economic News Releases

├── Release Schedules

├── Databases

├── Developers

├── Surveys

├── Inflation

├── Employment

├── Productivity

├── Pay

├── Regions

├── Publications

└── Archives
````

This becomes the first map an AI agent sees.

---

# Section 4

## Navigation Hierarchy

Explain how users actually navigate.

Example

```
Home

↓

Economic News Releases

↓

Inflation

↓

Consumer Price Index

↓

Latest Release

↓

Archive

↓

PDF

↓

HTML

↓

Charts
```

Repeat later for every dataset.

---

# Section 5

# Domain Structure

This is extremely important.

Most people ignore it.

Document every major domain.

| Domain           | Purpose            | Priority |
| ---------------- | ------------------ | -------- |
| `/`              | Homepage           | High     |
| `/bls/`          | Organization       | Medium   |
| `/schedule/`     | Official schedules | Critical |
| `/news.release/` | Release documents  | Critical |
| `/cpi/`          | CPI program        | Critical |
| `/ppi/`          | PPI program        | Critical |
| `/developers/`   | API documentation  | Critical |

The BLS uses consistent URL namespaces—for example, `/schedule/` for official release schedules, `/bls/newsrels.htm` for the central Economic News Releases hub, `/developers/` for API documentation, and program-specific directories such as `/ppi/` for Producer Price Index content. ([Bureau of Labor Statistics][2])

---

# Section 6

# Official Entry Points

Now we begin URLs.

For every URL:

| URL | Purpose | Use |
| --- | ------- | --- |

Start with

---

## Main Website

Purpose

Official homepage

---

## Economic News Releases

Purpose

Master page.

Every important release starts here.

This is probably your first crawling point. ([Bureau of Labor Statistics][1])

---

## Release Calendar

Purpose

Official release times.

Never estimate timestamps.

Always trust this page. ([Bureau of Labor Statistics][2])

---

## Developer Portal

Purpose

Public Data API.

API documentation.

Version history.

Developer resources. ([Bureau of Labor Statistics][3])

---

# Section 7

## Website Components

Instead of URLs,

list components.

Example

```
Release Calendar

↓

Program Page

↓

News Release

↓

PDF

↓

Charts

↓

Historical Archive

↓

Methodology

↓

API
```

---

# Section 8

# URL Registry

Now begins the real inventory.

Every URL gets its own block.

Example

---

## URL-001

Name

Economic News Releases

Purpose

Master page.

Priority

Critical

Contains

Latest releases

Archives

Release schedules

Program links

Formats

HTML

---

## URL-002

Release Calendar

Purpose

Official timestamps.

Priority

Critical

---

## URL-003

Developer Portal

Purpose

Public API.

Machine-readable data.

---

Continue until every important BLS URL is documented.

---

# Section 9

# Release Calendar Architecture

This deserves its own section.

Document

Monthly calendar

By release

Current year

Previous years

ICS calendar

Holiday handling

The BLS publishes release schedules by indicator (such as CPI and PPI), maintains current and prior-year calendars, and provides a subscription calendar in ICS format for automatic updates. ([Bureau of Labor Statistics][2])

---

# Section 10 onward

After the foundation is complete,

we dedicate one section to every dataset.

Example

```
Consumer Price Index

↓

Landing page

↓

Latest release

↓

Archive

↓

PDF

↓

HTML

↓

Charts

↓

RSS

↓

API
```

Repeat for

- CPI
- PPI
- Employment Situation
- JOLTS
- Employment Cost Index
- Real Earnings
- Productivity
- Import/Export Prices

The **Economic News Releases** page confirms these as the primary market-moving BLS programs and links each to its official release pages, PDFs, charts, schedules, and archives. ([Bureau of Labor Statistics][1])

---

## I have one recommendation that will significantly improve the entire project

Instead of embedding all URLs directly into Chapter 2, create a dedicated machine-readable registry:

```text
docs/
└── bls/
    ├── 02_Website_Architecture_and_URL_Inventory.md
    └── registry/
        ├── URL_REGISTRY.md
        ├── DATASET_REGISTRY.md
        ├── API_REGISTRY.md
        ├── RSS_REGISTRY.md
        ├── PDF_REGISTRY.md
        ├── HTML_REGISTRY.md
        └── ARCHIVE_REGISTRY.md
```

Then Chapter 2 explains the architecture and references these registries. This separation has three major advantages:

1. **Humans** can understand the website from the narrative architecture document.
2. **AI coding agents** can use the registry files as authoritative inventories without parsing long prose.
3. **Future maintenance** becomes simple—if BLS changes a URL or adds a dataset, you update a single registry file instead of editing multiple documents.

[1]: https://www.bls.gov/bls/newsrels.htm?utm_source=chatgpt.com "Economic News Releases : U.S. Bureau of Labor Statistics"
[2]: https://www.bls.gov/schedule/news_release/ppi.htm?utm_source=chatgpt.com "Schedule of Releases for the Producer Price Index"
[3]: https://www.bls.gov/developers/?utm_source=chatgpt.com "Getting Started : U.S. Bureau of Labor Statistics"
