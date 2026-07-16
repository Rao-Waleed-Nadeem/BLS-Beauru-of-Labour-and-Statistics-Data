import pytest
from pathlib import Path
from BLS.pipeline.collectors.series_registry_loader import SeriesRegistryLoader

def test_series_registry_loader(tmp_path: Path):
    registry_content = """# SERIES_REGISTRY.md

## SERIES-001

Series ID
```text
CUUR0000SA0
```

Title
```text
CPI-U
```

Program
```text
BLS-PROGRAM-001
```

Dataset
```text
BLS-DATASET-001
```

Priority
```text
Critical
```

Collection Method
```text
API
```

Storage
```text
raw/bls/cpi/
```

API Payload
```json
{
  "seriesid": ["CUUR0000SA0"],
  "startyear": "2020",
  "endyear": "2026"
}
```

Status
```text
Active
```
"""
    docs_path = tmp_path / "SERIES_REGISTRY.md"
    docs_path.write_text(registry_content, encoding="utf-8")
    
    loader = SeriesRegistryLoader(docs_path=docs_path)
    entries = loader.load()
    
    assert len(entries) == 1
    
    entry = entries[0]
    assert entry.entry_id == "SERIES-001"
    assert entry.series_id == "CUUR0000SA0"
    assert entry.title == "CPI-U"
    assert entry.program_id == "BLS-PROGRAM-001"
    assert entry.dataset_id == "BLS-DATASET-001"
    assert entry.collection_method == "API"
    assert entry.storage_path == "raw/bls/cpi/"
    assert entry.api_payload == {"seriesid": ["CUUR0000SA0"], "startyear": "2020", "endyear": "2026"}
    assert entry.enabled is True
