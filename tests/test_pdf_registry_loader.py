import pytest
from pathlib import Path
from pipeline.collectors.pdf_registry_loader import PDFRegistryLoader, PDFRegistryEntry

def test_pdf_registry_loader(tmp_path: Path):
    registry_content = """# PDF_REGISTRY.md
    
# Bitcoin Market Intelligence Dataset

## PDF-001

Document ID
```text
BLS-PDF-001
```

Program
```text
BLS-PROGRAM-001
```

Dataset
```text
BLS-DATASET-001
```

Document
```text
Consumer Price Index
```

Discovery
```text
Economic News Releases
```

Priority
```text
Critical
```

Status
```text
Active
```

## PDF-002

Document ID
```text
BLS-PDF-002
```

Program
```text
BLS-PROGRAM-002
```

Document
```text
Producer Price Index
```

Status
```text
Disabled
```
"""
    docs_path = tmp_path / "PDF_REGISTRY.md"
    docs_path.write_text(registry_content, encoding="utf-8")
    
    loader = PDFRegistryLoader(docs_path=docs_path)
    entries = loader.load()
    
    assert len(entries) == 2
    
    entry1 = entries[0]
    assert entry1.pdf_id == "PDF-001"
    assert entry1.document_id == "BLS-PDF-001"
    assert entry1.program_id == "BLS-PROGRAM-001"
    assert entry1.dataset_id == "BLS-DATASET-001"
    assert entry1.document_name == "Consumer Price Index"
    assert entry1.enabled is True
    
    entry2 = entries[1]
    assert entry2.pdf_id == "PDF-002"
    assert entry2.document_id == "BLS-PDF-002"
    assert entry2.program_id == "BLS-PROGRAM-002"
    assert entry2.dataset_id == ""
    assert entry2.document_name == "Producer Price Index"
    assert entry2.enabled is False
