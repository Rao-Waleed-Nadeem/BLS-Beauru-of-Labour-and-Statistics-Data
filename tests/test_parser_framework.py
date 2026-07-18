import json
from dataclasses import asdict
import pytest

from pipeline.parsers import (
    BaseParser,
    MetadataSchema,
    UnifiedObject,
    ReleaseSchema,
    APISchema
)


class DummyParser(BaseParser):
    def parse(self, raw_data, metadata):
        meta = MetadataSchema(
            uuid="123",
            dataset_id="ds1",
            program_id="prg1",
            series_id="ser1",
            collector="dummy",
            collector_version="1.0",
            schema_version="1.0",
            source_type="API",
            collection_timestamp="2026-07-18T10:00:00Z",
            validation_status="PASS",
            checksum="abc"
        )
        api = APISchema(
            series_id="ser1",
            series_title="Title",
            frequency="M",
            year="2026",
            period="M06",
            period_name="June",
            value="100.5"
        )
        return UnifiedObject(metadata=meta, api=api)

def test_base_parser_enforces_abstract_methods():
    with pytest.raises(TypeError):
        # Should raise TypeError because parse is abstract
        class IncompleteParser(BaseParser):
            pass
        IncompleteParser()

def test_dummy_parser_returns_unified_object():
    parser = DummyParser()
    obj = parser.parse("raw", {})
    assert isinstance(obj, UnifiedObject)
    assert obj.metadata.uuid == "123"
    assert obj.api.value == "100.5"
    assert obj.html is None  # Check default None

def test_unified_object_json_serialization():
    parser = DummyParser()
    obj = parser.parse("raw", {})
    
    obj_dict = asdict(obj)
    json_str = json.dumps(obj_dict)
    
    parsed_json = json.loads(json_str)
    
    assert parsed_json["metadata"]["uuid"] == "123"
    assert parsed_json["api"]["series_id"] == "ser1"
    # Ensure fields that are None serialize to null (which is None in python after json.loads)
    assert parsed_json.get("html") is None
    assert parsed_json.get("pdf") is None

def test_schema_defaults():
    # Test that defaults work correctly
    release = ReleaseSchema(
        release_id="r1",
        release_name="Release 1",
        program_name="P1",
        dataset_name="D1",
        release_datetime="2026-07-18"
    )
    assert release.revision is False
    assert release.status == "published"
    assert release.reference_period == ""

