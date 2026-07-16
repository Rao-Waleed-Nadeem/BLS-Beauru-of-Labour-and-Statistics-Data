import pytest

from BLS.pipeline.registry import (
    DatasetRegistryEntry,
    ProgramRegistryEntry,
    RegistryCache,
    RegistryLoader,
    RegistryParser,
    RegistryValidator,
    UrlRegistryEntry,
)
from BLS.pipeline.utils.base_utils import get_project_root

REGISTRY_DIR = (
    get_project_root()
    / "Docs"
    / "BLS"
    / "02_Website_Architecture_and_URL_Inventory"
    / "Registery"
)


@pytest.fixture
def registry_docs() -> dict[str, str]:
    return {
        "URL_REGISTRY.md": (REGISTRY_DIR / "URL_REGISTRY.md").read_text(encoding="utf-8"),
        "PROGRAM_REGISTRY.md": (
            REGISTRY_DIR / "PROGRAM_REGISTRY.md"
        ).read_text(encoding="utf-8"),
        "DATASET_REGISTRY.md": (
            REGISTRY_DIR / "DATASET_REGISTRY.md"
        ).read_text(encoding="utf-8"),
    }


def test_registry_loader_loads_all_registries():
    loader = RegistryLoader()
    cache = loader.load()

    assert len(cache.urls) == 14
    assert len(cache.programs) == 8
    assert len(cache.datasets) == 8

    assert cache.get_url("BLS-URL-001") is not None
    assert cache.get_program("BLS-PROGRAM-001") is not None
    assert cache.get_dataset("BLS-DATASET-001") is not None


def test_registry_loader_is_idempotent():
    loader = RegistryLoader()
    first = loader.load()
    second = loader.load()

    assert first is second
    assert len(second.urls) == 14


def test_registry_loader_reload_clears_and_reloads():
    loader = RegistryLoader()
    first = loader.load()
    second = loader.reload()

    assert first is second
    assert len(second.datasets) == 8


def test_registry_loader_get_cache():
    loader = RegistryLoader()
    cache = loader.get_cache()

    assert len(cache.programs) == 8


def test_registry_loader_missing_file():
    loader = RegistryLoader(docs_dir="non_existent_dir")
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_parser_parse_urls(registry_docs):
    parser = RegistryParser()
    urls = parser.parse_urls(registry_docs["URL_REGISTRY.md"])

    assert len(urls) == 14
    assert urls[0].id == "BLS-URL-001"
    assert urls[0].url == "https://www.bls.gov/"


def test_parser_parse_programs(registry_docs):
    parser = RegistryParser()
    programs = parser.parse_programs(registry_docs["PROGRAM_REGISTRY.md"])

    assert len(programs) == 8
    assert programs[0].program_id == "BLS-PROGRAM-001"
    assert programs[0].name == "Consumer Price Index"
    assert programs[0].base_url == "https://www.bls.gov/cpi/"


def test_parser_parse_datasets(registry_docs):
    parser = RegistryParser()
    datasets = parser.parse_datasets(registry_docs["DATASET_REGISTRY.md"])

    assert len(datasets) == 8
    assert datasets[0].dataset_id == "BLS-DATASET-001"
    assert datasets[0].program_id == "BLS-PROGRAM-001"
    assert datasets[1].dataset_id == "BLS-DATASET-002"


def test_validator_rejects_invalid_url_id():
    validator = RegistryValidator()
    entry = UrlRegistryEntry(
        id="INVALID",
        category="ROOT",
        name="Test",
        url="https://www.bls.gov/",
        purpose="Test",
        priority="Critical",
        status="Active",
    )

    with pytest.raises(ValueError, match="Invalid URL ID format"):
        validator.validate_url(entry)


def test_validator_rejects_unknown_program_reference():
    validator = RegistryValidator()
    cache = RegistryCache()
    cache.add_dataset(
        DatasetRegistryEntry(
            dataset_name="Test Dataset",
            dataset_id="BLS-DATASET-999",
            program_id="BLS-PROGRAM-999",
        )
    )

    with pytest.raises(ValueError, match="references unknown Program ID"):
        validator.validate_relationships(cache)


def test_cache_rejects_duplicate_ids():
    cache = RegistryCache()
    entry = UrlRegistryEntry(
        id="BLS-URL-001",
        category="ROOT",
        name="Duplicate",
        url="https://www.bls.gov/",
        purpose="Test",
        priority="Critical",
        status="Active",
    )
    cache.add_url(entry)

    with pytest.raises(ValueError, match="Duplicate URL ID"):
        cache.add_url(entry)


def test_public_registry_exports():
    from BLS.pipeline import registry

    assert registry.RegistryLoader is RegistryLoader
    assert registry.UrlRegistryEntry is UrlRegistryEntry
    assert registry.ProgramRegistryEntry is ProgramRegistryEntry
    assert registry.DatasetRegistryEntry is DatasetRegistryEntry
