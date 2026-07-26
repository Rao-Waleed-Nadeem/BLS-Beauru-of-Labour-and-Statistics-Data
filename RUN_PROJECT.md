# BLS Project Run Guide

This guide explains how to run the project, collect BLS data, find the output
files, understand what the data means, and decide which files to use in a
machine learning or NLP workflow.

It is written for two audiences:

- Common users who want to know what the data means.
- Developers who want to understand how the pipeline works.

Run all commands from PowerShell.

---

# 1. What This Project Does

This project collects economic data from the U.S. Bureau of Labor Statistics
(BLS).

BLS publishes official U.S. labor and inflation data. Examples:

- Consumer Price Index (CPI): inflation / price level data.
- Unemployment Rate: percentage of people unemployed.
- Total Nonfarm Employment: number of jobs in the U.S. economy.

The project stores the data in multiple stages:

```text
Raw BLS response
-> parsed records
-> normalized records
-> validated records
-> processed datasets
-> model-ready feature files
```

For model training, you normally use:

```text
storage/features/bls/<DATASET_ID>/feature_set.csv
```

or:

```text
storage/processed/bls/<DATASET_ID>/dataset.csv
```

Do not train directly on `storage/raw/...` unless you specifically want raw
BLS API responses.

---

# 2. What Data Is Currently Registered

The project is registry-driven. That means it only collects series listed in:

```text
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/SERIES_REGISTRY.md
```

Current registered API series:

| Series ID | Human Meaning | Dataset | Plain English Meaning |
| --- | --- | --- | --- |
| `CUUR0000SA0` | Consumer Price Index for All Urban Consumers (CPI-U): All Items | `BLS-DATASET-001` | Overall inflation index before seasonal adjustment |
| `CUSR0000SA0` | Consumer Price Index, Seasonally Adjusted | `BLS-DATASET-001` | Inflation index adjusted for seasonal patterns |
| `LNS14000000` | Unemployment Rate | `BLS-DATASET-003` | Percent of labor force unemployed |
| `CES0000000001` | Total Nonfarm Employment | `BLS-DATASET-003` | Number of U.S. nonfarm payroll jobs, usually in thousands |

Dataset IDs:

| Dataset ID | Meaning | Example Use |
| --- | --- | --- |
| `BLS-DATASET-001` | CPI / inflation data | Inflation modeling, macro signals, BTC inflation reaction studies |
| `BLS-DATASET-003` | Employment / unemployment data | Labor market modeling, macro signals, BTC jobs-report reaction studies |

Important: "all data" means all data for the registered series above. To collect
more BLS indicators, add more official BLS series IDs to the registry.

---

# 3. Install And Prepare Environment

Go to the project root:

```powershell
cd "D:\Tier 1\BLS"
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Set Python import path:

```powershell
$env:PYTHONPATH="D:\Tier 1;D:\Tier 1\BLS"
```

Why this is needed:

The current codebase uses both import styles:

```text
pipeline...
BLS.pipeline...
```

So PowerShell needs `PYTHONPATH` set before running the pipeline.

Optional BLS API key:

```powershell
$env:BLS_API_KEY="your_bls_api_key"
```

You can run without a key, but BLS may disable some metadata like catalog
titles. The project fills some human-readable titles from the local registry.

---

# 4. First-Time Full Historical Run

Use this command to collect historical data from 2020 to the current year:

```powershell
python -c "from pipeline.backfill import run_backfill; run_backfill(dry_run=False)"
```

This command does:

```text
1. Load registries
2. Request BLS API data from 2020 to current year
3. Save raw API responses
4. Parse API observations
5. Normalize records
6. Validate records
7. Save validated yearly records
8. Build processed datasets
9. Build model-ready feature files
```

Use this backfill command when:

- You are running the project for the first time.
- You want to rebuild 2020-current historical files.
- You changed registered series and need the historical dataset again.

---

# 5. Daily Or Current Incremental Run

After historical backfill has completed once, use:

```powershell
python -m pipeline.incremental
```

Normal sequence:

```text
First time:
1. Run historical backfill
2. Run incremental update

Future daily use:
1. Run incremental update only
```

---

# 6. Safe Dry Run

To test pipeline behavior without live BLS collection:

```powershell
python -m pipeline.incremental --dry-run
```

Use dry run when:

- You are checking setup.
- You do not want network calls.
- You want sample local outputs.

---

# 7. Full Command Sequence

With BLS API key:

```powershell
cd "D:\Tier 1\BLS"
$env:PYTHONPATH="D:\Tier 1;D:\Tier 1\BLS"
$env:BLS_API_KEY="your_bls_api_key"
python -c "from pipeline.backfill import run_backfill; run_backfill(dry_run=False)"
python -m pipeline.incremental
```

Without BLS API key:

```powershell
cd "D:\Tier 1\BLS"
$env:PYTHONPATH="D:\Tier 1;D:\Tier 1\BLS"
python -c "from pipeline.backfill import run_backfill; run_backfill(dry_run=False)"
python -m pipeline.incremental
```

Run tests:

```powershell
python -m pytest -q
```

---

# 8. Output Folder Overview

The storage folder has multiple layers:

```text
storage/raw/          official source data and collector artifacts
storage/validated/    records that passed validation
storage/processed/    cleaned datasets for analysis/modeling
storage/features/     engineered model-ready features
storage/metadata/     metadata sidecars
storage/logs/         logs
```

Simple rule:

```text
Common user/model training:
Use storage/processed or storage/features

Developer/debugging:
Inspect storage/raw and storage/validated
```

---

# 9. Raw Data Files

Raw batch API responses:

```text
storage/raw/bls/api/<RUN_YEAR>/<TIMESTAMP>/response.json
```

Example:

```text
storage/raw/bls/api/2026/2026-07-26T18-14-28Z/response.json
```

Raw per-series, per-year API responses:

```text
storage/raw/bls/api/series/<SERIES_ID>/<YEAR>/response.json
```

Examples:

```text
storage/raw/bls/api/series/CUUR0000SA0/2020/response.json
storage/raw/bls/api/series/CUUR0000SA0/2026/response.json
storage/raw/bls/api/series/CES0000000001/2020/response.json
storage/raw/bls/api/series/CES0000000001/2026/response.json
```

What raw files contain:

```json
{
  "seriesID": "CES0000000001",
  "data": [
    {
      "year": "2020",
      "period": "M12",
      "periodName": "December",
      "value": "142548",
      "footnotes": [{}]
    }
  ]
}
```

Plain meaning:

```text
Series ID: CES0000000001
Series meaning: Total Nonfarm Employment
Year: 2020
Month: December
Value: 142548
Unit: thousands of employees
Human meaning: about 142.548 million nonfarm jobs
```

Raw files are useful for audit/debugging. They are not the best direct model
input because they are nested JSON and may not include local enrichment.

---

# 10. Processed Dataset Files

Use these for cleaned observations:

```text
storage/processed/bls/BLS-DATASET-001/dataset.csv
storage/processed/bls/BLS-DATASET-003/dataset.csv
```

JSON versions:

```text
storage/processed/bls/BLS-DATASET-001/dataset.json
storage/processed/bls/BLS-DATASET-003/dataset.json
```

What `dataset.csv` contains:

```text
uuid
series_id
series_title
frequency
year
period
period_name
value
latest
footnotes
source_type
collection_timestamp
normalization_timestamp
checksum
```

Important fields:

| Field | Meaning | Example |
| --- | --- | --- |
| `series_id` | Official BLS series identifier | `CES0000000001` |
| `series_title` | Human-readable series name | `Total Nonfarm Employment` |
| `frequency` | How often data is published | `Monthly` |
| `year` | Observation year | `2020` |
| `period` | BLS period code | `M12` |
| `period_name` | Human-readable period | `December` |
| `value` | Official BLS numeric value | `142548` |
| `latest` | Whether BLS marked it as latest | `False` |
| `footnotes` | Notes from BLS, if any | `Revised.` or empty |

Use `dataset.csv` if:

- You want clean official values.
- You want to make your own features.
- You want simple tabular data.

---

# 11. Feature Files For Models

Use these for model-ready features:

```text
storage/features/bls/BLS-DATASET-001/feature_set.csv
storage/features/bls/BLS-DATASET-003/feature_set.csv
```

JSON versions:

```text
storage/features/bls/BLS-DATASET-001/feature_set.json
storage/features/bls/BLS-DATASET-003/feature_set.json
```

What `feature_set.csv` contains:

```text
series_id
series_title
frequency
year
period
period_name
date_index
value
previous_value
value_diff
pct_change
month
quarter
latest
footnotes
nlp_text
publication_datetime
```

Important feature fields:

| Field | Meaning |
| --- | --- |
| `value` | Current BLS value |
| `previous_value` | Previous available value in sequence |
| `value_diff` | Current value minus previous value |
| `pct_change` | Percentage change from previous value |
| `month` | Month number if monthly data |
| `quarter` | Quarter number if quarterly data |
| `nlp_text` | Human-readable sentence made from the row |

Example `nlp_text`:

```text
Total Nonfarm Employment for December 2020 was 142548.
```

Use `feature_set.csv` if:

- You want ready-made numeric model features.
- You want quick ML experiments.
- You want simple text (`nlp_text`) beside the values.

---

# 12. Footnotes Explained

BLS often returns:

```json
"footnotes": [{}]
```

This means there is no footnote text for that observation.

If BLS returns:

```json
"footnotes": [{"text": "Revised."}]
```

the pipeline stores:

```text
Revised.
```

Footnotes can matter because they may indicate:

- revised values
- preliminary values
- special publication notes
- data quality notes

If `footnotes` is empty, there is no extra note from BLS for that row.

---

# 13. How A Common User Should Read One Row

Example raw observation:

```json
{
  "seriesID": "CES0000000001",
  "year": "2020",
  "period": "M12",
  "periodName": "December",
  "value": "142548"
}
```

Plain English:

```text
In December 2020, total nonfarm employment was 142,548 thousand jobs.
That is about 142.548 million jobs.
```

Example CPI observation:

```json
{
  "seriesID": "CUUR0000SA0",
  "year": "2020",
  "period": "M01",
  "periodName": "January",
  "value": "257.971"
}
```

Plain English:

```text
In January 2020, the CPI-U All Items index was 257.971.
This is an inflation index level, not a dollar amount.
```

Example unemployment observation:

```json
{
  "seriesID": "LNS14000000",
  "year": "2020",
  "period": "M04",
  "periodName": "April",
  "value": "14.7"
}
```

Plain English:

```text
In April 2020, the unemployment rate was 14.7 percent.
```

---

# 14. How Developers Should Understand The Pipeline

Main modules:

```text
pipeline/backfill.py
pipeline/incremental.py
pipeline/collectors/
pipeline/parsers/
pipeline/normalizers/
pipeline/validators/
pipeline/storage/
pipeline/datasets/
pipeline/features/
```

Main historical entry point:

```text
pipeline.backfill.run_backfill(dry_run=False)
```

Main incremental entry point:

```text
python -m pipeline.incremental
```

Pipeline stages:

```text
Config / registry
-> scheduler
-> collectors
-> parsers
-> normalizer
-> validator
-> storage manager
-> dataset builder
-> feature builder
```

Registry files:

```text
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/SERIES_REGISTRY.md
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/DATASET_REGISTRY.md
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/API_REGISTRY.md
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/HTML_REGISTRY.md
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/PDF_REGISTRY.md
Docs/BLS/02_Website_Architecture_and_URL_Inventory/Registery/CALENDAR_REGISTRY.md
```

To add more data:

```text
1. Find official BLS series ID.
2. Add it to SERIES_REGISTRY.md.
3. Map it to a program_id and dataset_id.
4. Run historical backfill again.
5. Check storage/processed and storage/features.
```

Do not hardcode new series IDs inside Python code.

---

# 15. How To Inspect Data

List raw per-year responses:

```powershell
Get-ChildItem storage\raw\bls\api\series -Recurse -Filter response.json
```

Open one raw response:

```powershell
Get-Content storage\raw\bls\api\series\CES0000000001\2020\response.json
```

See processed files:

```powershell
Get-ChildItem storage\processed\bls -Recurse
```

See feature files:

```powershell
Get-ChildItem storage\features\bls -Recurse
```

Preview a CSV:

```powershell
Get-Content storage\features\bls\BLS-DATASET-003\feature_set.csv | Select-Object -First 10
```

Count rows in a CSV:

```powershell
Import-Csv storage\features\bls\BLS-DATASET-003\feature_set.csv | Measure-Object
```

Filter one series:

```powershell
Import-Csv storage\features\bls\BLS-DATASET-003\feature_set.csv |
  Where-Object { $_.series_id -eq "CES0000000001" } |
  Select-Object -First 10
```

---

# 16. How To Use In Python

Example using pandas:

```python
import pandas as pd

cpi = pd.read_csv("storage/features/bls/BLS-DATASET-001/feature_set.csv")
employment = pd.read_csv("storage/features/bls/BLS-DATASET-003/feature_set.csv")

print(cpi.head())
print(employment.head())
```

Example selecting one series:

```python
employment = pd.read_csv("storage/features/bls/BLS-DATASET-003/feature_set.csv")

nonfarm = employment[employment["series_id"] == "CES0000000001"]
unemployment = employment[employment["series_id"] == "LNS14000000"]
```

Example model columns:

```python
features = [
    "value",
    "previous_value",
    "value_diff",
    "pct_change",
    "month",
]

X = nonfarm[features]
```

Example NLP text:

```python
texts = nonfarm["nlp_text"].tolist()
```

Remember: `nlp_text` is generated from structured numeric data. It is not the
same as official BLS news-release text.

---

# 17. NLP And Sentiment Guidance

There are two different NLP ideas:

## Structured Row Text

The project can generate simple text like:

```text
Total Nonfarm Employment for December 2020 was 142548.
```

This is useful for:

- retrieval
- embeddings
- natural-language summaries
- simple text-based model input

But it is not true sentiment. A number alone does not contain sentiment.

## Real Sentiment Text

For sentiment analysis, better sources are:

- BLS news release HTML pages
- BLS PDF release text
- market news articles
- analyst reports
- social media / crypto market commentary

Current caveat:

Some `www.bls.gov` HTML/RSS/calendar URLs return `403 Forbidden` from this
environment. The API collection works, but website text scraping is incomplete
until the website collector access issue is fixed.

So for now:

```text
Use BLS API data for numeric macro features.
Use external text/news sources for sentiment.
```

---

# 18. Current Known Limitation

BLS API collection works.

Some BLS website URLs may fail with:

```text
403 Forbidden
```

This affects:

```text
HTML release pages
RSS feeds
Release calendars
Some PDF discovery workflows
```

The numeric API data can still be collected and used.

---

# 19. What To Use For Your Model

Best default model input:

```text
storage/features/bls/BLS-DATASET-001/feature_set.csv
storage/features/bls/BLS-DATASET-003/feature_set.csv
```

Use these when:

- You want ready-made columns like `value_diff` and `pct_change`.
- You want `nlp_text`.
- You want easier ML input.

Use processed datasets when:

```text
storage/processed/bls/BLS-DATASET-001/dataset.csv
storage/processed/bls/BLS-DATASET-003/dataset.csv
```

Use these when:

- You want only official cleaned observations.
- You want to build your own features.

Avoid raw data for training unless you are doing custom parsing:

```text
storage/raw/bls/...
```

---

# 20. Quick Troubleshooting

Error:

```text
ModuleNotFoundError: No module named 'BLS'
```

Fix:

```powershell
$env:PYTHONPATH="D:\Tier 1;D:\Tier 1\BLS"
```

Error:

```text
403 Forbidden
```

Meaning:

```text
BLS website page blocked this request.
API may still work.
```

Warning:

```text
CryptographyDeprecationWarning from pypdf
```

Meaning:

```text
This is an upstream warning from a PDF dependency.
It does not mean the API data failed.
```

No title in raw response:

```text
BLS disabled API catalog metadata.
Use series_id mapping from SERIES_REGISTRY.md.
Processed/feature files should carry local title enrichment when generated.
```
