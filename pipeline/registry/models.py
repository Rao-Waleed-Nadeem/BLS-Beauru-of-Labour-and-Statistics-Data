from dataclasses import dataclass, field
from typing import List

@dataclass
class UrlRegistryEntry:
    id: str
    category: str
    name: str
    url: str
    purpose: str
    priority: str
    status: str

@dataclass
class ProgramRegistryEntry:
    program_id: str
    name: str = ""
    base_url: str = ""
    release_page: str = ""
    release_schedule: str = ""
    related_registries: List[str] = field(default_factory=list)
    primary_content: List[str] = field(default_factory=list)
    expected_output: List[str] = field(default_factory=list)
    implementation_status: str = ""

@dataclass
class DatasetRegistryEntry:
    dataset_name: str
    dataset_id: str
    program_id: str
    collection_methods: List[str] = field(default_factory=list)
    load_registries: List[str] = field(default_factory=list)
    raw_storage: str = ""
    processed_storage: str = ""
    output_files: List[str] = field(default_factory=list)
    pipeline: List[str] = field(default_factory=list)
    implementation_status: str = ""
