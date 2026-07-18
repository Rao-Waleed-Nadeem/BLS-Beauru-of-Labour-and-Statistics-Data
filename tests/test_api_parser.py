"""
test_api_parser.py — M15 API Parser Tests

Tests for pipeline.parsers.api_parser.APIParser.

Coverage:
  - parse() returns first observation as UnifiedObject
  - parse_all() returns one object per observation per series
  - MetadataSchema population
  - APISchema fields populated: series_id, year, period, periodName, value, latest, footnotes
  - latest coercion: "true" -> True, "false" -> False, bool passthrough
  - footnotes flattening from [{code, text}] to [str]
  - series_id filter in metadata
  - Multi-series response, all series parsed when no filter
  - Multi-series response filtered to one series
  - Empty data list returns empty list from parse_all
  - Empty data list returns metadata-only from parse()
  - Catalog fields (series_title, frequency) merged into observations
  - Input: dict
  - Input: bytes
  - Input: str JSON
  - Input: Path to response.json
  - Input: string path ending in .json
  - Invalid JSON string raises ValueError
  - Non-existent path raises ValueError
  - Unsupported type raises ValueError
  - Missing required response key raises ValueError
  - Status != REQUEST_SUCCEEDED raises ValueError
  - Missing Results.series raises ValueError
  - series_id not found in response raises ValueError
  - JSON serializable
  - Export from __init__ works
  - source_type defaults to API
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from pipeline.parsers.api_parser import (
    APIParser,
    _build_api_schema,
    _coerce_latest,
    _footnotes_to_list,
    _validate_response,
)
from pipeline.parsers.models import UnifiedObject


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_response(series: list, status: str = "REQUEST_SUCCEEDED") -> dict:
    """Build a minimal valid BLS API response dict."""
    return {
        "status": status,
        "responseTime": 150,
        "message": [],
        "Results": {
            "series": series
        }
    }


def _make_series(
    series_id: str,
    observations: list = None,
    catalog: dict = None,
) -> dict:
    """Build a series block."""
    return {
        "seriesID": series_id,
        "catalog": catalog or {},
        "data": observations or [],
    }


def _make_obs(
    year: str = "2026",
    period: str = "M06",
    period_name: str = "June",
    value: str = "315.605",
    latest: Any = "true",
    footnotes: list = None,
) -> dict:
    return {
        "year": year,
        "period": period,
        "periodName": period_name,
        "value": value,
        "latest": latest,
        "footnotes": footnotes if footnotes is not None else [{}],
    }


# A complete realistic single-series response
_CPI_RESPONSE = _make_response([
    _make_series(
        "CUUR0000SA0",
        observations=[
            _make_obs("2026", "M06", "June", "315.605", "true"),
            _make_obs("2026", "M05", "May",  "315.200", "false"),
            _make_obs("2026", "M04", "April","314.800", "false",
                      footnotes=[{"code": "R", "text": "Revised."}]),
        ],
        catalog={"series_title": "CPI-U All Items", "frequency": "Monthly"},
    )
])

# Multi-series response
_MULTI_RESPONSE = _make_response([
    _make_series(
        "CUUR0000SA0",
        observations=[_make_obs("2026", "M06", "June", "315.605", "true")],
        catalog={"series_title": "CPI-U", "frequency": "Monthly"},
    ),
    _make_series(
        "WPU00000000",
        observations=[
            _make_obs("2026", "M06", "June", "312.0", "true"),
            _make_obs("2026", "M05", "May",  "311.5", "false"),
        ],
        catalog={"series_title": "PPI All Commodities", "frequency": "Monthly"},
    ),
])

_BASE_METADATA = {
    "uuid": "api-uuid-001",
    "dataset_id": "BLS-DATASET-001",
    "program_id": "BLS-PROGRAM-001",
    "collector": "api_collector",
    "collector_version": "m10",
    "schema_version": "1.0",
    "source_type": "API",
    "collection_timestamp": "2026-07-18T08:30:00Z",
    "normalization_timestamp": "2026-07-18T08:31:00Z",
    "validation_status": "PASS",
    "source_url": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
}




# ---------------------------------------------------------------------------
# Unit Tests — Internal Helpers
# ---------------------------------------------------------------------------

class TestCoerceLatest:
    def test_string_true(self):
        assert _coerce_latest("true") is True

    def test_string_True_caps(self):
        assert _coerce_latest("True") is True

    def test_string_false(self):
        assert _coerce_latest("false") is False

    def test_bool_true(self):
        assert _coerce_latest(True) is True

    def test_bool_false(self):
        assert _coerce_latest(False) is False

    def test_empty_string(self):
        assert _coerce_latest("") is False

    def test_none(self):
        assert _coerce_latest(None) is False


class TestFootnotesToList:
    def test_empty_list(self):
        assert _footnotes_to_list([]) == []

    def test_none(self):
        assert _footnotes_to_list(None) == []

    def test_single_footnote(self):
        result = _footnotes_to_list([{"code": "R", "text": "Revised."}])
        assert result == ["Revised."]

    def test_multiple_footnotes(self):
        result = _footnotes_to_list([
            {"code": "R", "text": "Revised."},
            {"code": "P", "text": "Preliminary."},
        ])
        assert result == ["Revised.", "Preliminary."]

    def test_empty_dict_skipped(self):
        result = _footnotes_to_list([{}])
        assert result == []

    def test_missing_text_key_skipped(self):
        result = _footnotes_to_list([{"code": "R"}])
        assert result == []

    def test_non_list_returns_empty(self):
        assert _footnotes_to_list("bad") == []


class TestBuildApiSchema:
    def test_basic_fields(self):
        obs = _make_obs()
        schema = _build_api_schema("CUUR0000SA0", obs)
        assert schema.series_id == "CUUR0000SA0"
        assert schema.year == "2026"
        assert schema.period == "M06"
        assert schema.period_name == "June"
        assert schema.value == "315.605"
        assert schema.latest is True

    def test_footnotes_flattened(self):
        obs = _make_obs(footnotes=[{"code": "R", "text": "Revised."}])
        schema = _build_api_schema("S1", obs)
        assert schema.footnotes == ["Revised."]

    def test_empty_footnotes(self):
        obs = _make_obs(footnotes=[{}])
        schema = _build_api_schema("S1", obs)
        assert schema.footnotes == []

    def test_catalog_series_title_merged(self):
        obs = dict(_make_obs())
        obs["seriesTitle"] = "CPI-U All Items"
        schema = _build_api_schema("CUUR0000SA0", obs)
        assert schema.series_title == "CPI-U All Items"


class TestValidateResponse:
    def test_valid_response_passes(self):
        _validate_response(_CPI_RESPONSE)  # Should not raise

    def test_missing_status_raises(self):
        payload = dict(_CPI_RESPONSE)
        del payload["status"]
        with pytest.raises(ValueError, match="missing required keys"):
            _validate_response(payload)

    def test_missing_responseTime_raises(self):
        payload = dict(_CPI_RESPONSE)
        del payload["responseTime"]
        with pytest.raises(ValueError, match="missing required keys"):
            _validate_response(payload)

    def test_missing_Results_raises(self):
        payload = dict(_CPI_RESPONSE)
        del payload["Results"]
        with pytest.raises(ValueError, match="missing required keys"):
            _validate_response(payload)

    def test_failed_status_raises(self):
        payload = _make_response([], status="REQUEST_FAILED")
        with pytest.raises(ValueError, match="not REQUEST_SUCCEEDED"):
            _validate_response(payload)

    def test_missing_series_key_raises(self):
        payload = {
            "status": "REQUEST_SUCCEEDED",
            "responseTime": 100,
            "Results": {},
        }
        with pytest.raises(ValueError, match="missing 'series'"):
            _validate_response(payload)

    def test_series_not_list_raises(self):
        payload = {
            "status": "REQUEST_SUCCEEDED",
            "responseTime": 100,
            "Results": {"series": "not-a-list"},
        }
        with pytest.raises(ValueError, match="must be a list"):
            _validate_response(payload)

    def test_series_missing_seriesID_raises(self):
        payload = {
            "status": "REQUEST_SUCCEEDED",
            "responseTime": 100,
            "Results": {"series": [{"data": []}]},
        }
        with pytest.raises(ValueError, match="missing required 'seriesID'"):
            _validate_response(payload)

    def test_series_missing_data_raises(self):
        payload = {
            "status": "REQUEST_SUCCEEDED",
            "responseTime": 100,
            "Results": {"series": [{"seriesID": "X"}]},
        }
        with pytest.raises(ValueError, match="missing required 'data'"):
            _validate_response(payload)


# ---------------------------------------------------------------------------
# Integration Tests — APIParser.parse()
# ---------------------------------------------------------------------------

class TestAPIParserParseFromDict:
    """Parser receives a dict."""

    def setup_method(self):
        self.parser = APIParser()
        self.meta = {**_BASE_METADATA, "series_id": "CUUR0000SA0"}

    def test_returns_unified_object(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert isinstance(result, UnifiedObject)

    def test_returns_first_observation(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.api is not None
        assert result.api.year == "2026"
        assert result.api.period == "M06"

    def test_metadata_schema_populated(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        m = result.metadata
        assert m.uuid == "api-uuid-001"
        assert m.series_id == "CUUR0000SA0"
        assert m.source_type == "API"
        assert m.collector == "api_collector"
        assert m.validation_status == "PASS"

    def test_api_schema_value_preserved(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.api.value == "315.605"

    def test_api_schema_latest_coerced(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.api.latest is True

    def test_catalog_title_merged(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.api.series_title == "CPI-U All Items"

    def test_catalog_frequency_merged(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.api.frequency == "Monthly"

    def test_non_api_fields_are_none(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.html is None
        assert result.pdf is None
        assert result.release is None

    def test_source_type_defaults_to_api(self):
        result = self.parser.parse(_CPI_RESPONSE, {})
        assert result.metadata.source_type == "API"

    def test_collector_default(self):
        result = self.parser.parse(_CPI_RESPONSE, {})
        assert result.metadata.collector == "api_parser"

    def test_empty_data_returns_metadata_only(self):
        resp = _make_response([_make_series("CUUR0000SA0", observations=[])])
        result = self.parser.parse(resp, {"series_id": "CUUR0000SA0"})
        assert isinstance(result, UnifiedObject)
        assert result.api is None

    def test_json_serializable(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        obj_dict = asdict(result)
        json_str = json.dumps(obj_dict)
        parsed = json.loads(json_str)
        assert parsed["metadata"]["series_id"] == "CUUR0000SA0"
        assert parsed["api"]["value"] == "315.605"


class TestAPIParserParseAll:
    """parse_all() returns one object per observation."""

    def setup_method(self):
        self.parser = APIParser()
        self.meta = {**_BASE_METADATA, "series_id": "CUUR0000SA0"}

    def test_returns_all_observations(self):
        results = self.parser.parse_all(_CPI_RESPONSE, self.meta)
        assert len(results) == 3

    def test_each_is_unified_object(self):
        results = self.parser.parse_all(_CPI_RESPONSE, self.meta)
        for obj in results:
            assert isinstance(obj, UnifiedObject)

    def test_all_have_api_schema(self):
        results = self.parser.parse_all(_CPI_RESPONSE, self.meta)
        for obj in results:
            assert obj.api is not None

    def test_observations_in_order(self):
        results = self.parser.parse_all(_CPI_RESPONSE, self.meta)
        assert results[0].api.period == "M06"
        assert results[1].api.period == "M05"
        assert results[2].api.period == "M04"

    def test_revised_footnote_in_third_obs(self):
        results = self.parser.parse_all(_CPI_RESPONSE, self.meta)
        assert "Revised." in results[2].api.footnotes

    def test_empty_data_returns_empty_list(self):
        resp = _make_response([_make_series("CUUR0000SA0", observations=[])])
        results = self.parser.parse_all(resp, {"series_id": "CUUR0000SA0"})
        assert results == []

    def test_series_id_filter(self):
        meta = {**_BASE_METADATA, "series_id": "WPU00000000"}
        results = self.parser.parse_all(_MULTI_RESPONSE, meta)
        assert len(results) == 2
        for obj in results:
            assert obj.metadata.series_id == "WPU00000000"

    def test_no_filter_returns_all_series(self):
        meta = {**_BASE_METADATA}  # no series_id
        results = self.parser.parse_all(_MULTI_RESPONSE, meta)
        # 1 obs (CPI) + 2 obs (PPI) = 3
        assert len(results) == 3

    def test_series_id_not_found_raises(self):
        meta = {**_BASE_METADATA, "series_id": "NONEXISTENT"}
        with pytest.raises(ValueError, match="not found in API response"):
            self.parser.parse_all(_CPI_RESPONSE, meta)

    def test_primary_key_uniqueness(self):
        """series_id + year + period should be unique across observations."""
        results = self.parser.parse_all(_CPI_RESPONSE, self.meta)
        keys = [(o.api.series_id, o.api.year, o.api.period) for o in results]
        assert len(keys) == len(set(keys))


class TestAPIParserMultiSeries:
    """Multi-series responses."""

    def setup_method(self):
        self.parser = APIParser()

    def test_cpi_series_metadata_correct(self):
        meta = {**_BASE_METADATA, "series_id": "CUUR0000SA0"}
        results = self.parser.parse_all(_MULTI_RESPONSE, meta)
        assert results[0].metadata.series_id == "CUUR0000SA0"
        assert results[0].api.series_title == "CPI-U"

    def test_ppi_series_metadata_correct(self):
        meta = {**_BASE_METADATA, "series_id": "WPU00000000"}
        results = self.parser.parse_all(_MULTI_RESPONSE, meta)
        assert len(results) == 2
        for obj in results:
            assert obj.api.series_title == "PPI All Commodities"
            assert obj.api.frequency == "Monthly"


# ---------------------------------------------------------------------------
# Input Mode Tests
# ---------------------------------------------------------------------------

class TestAPIParserInputModes:
    """Tests for all supported input types."""

    def setup_method(self):
        self.parser = APIParser()
        self.meta = {**_BASE_METADATA, "series_id": "CUUR0000SA0"}

    def test_dict_input(self):
        result = self.parser.parse(_CPI_RESPONSE, self.meta)
        assert result.api is not None

    def test_bytes_input(self):
        raw = json.dumps(_CPI_RESPONSE).encode("utf-8")
        result = self.parser.parse(raw, self.meta)
        assert result.api.value == "315.605"

    def test_json_string_input(self):
        raw = json.dumps(_CPI_RESPONSE)
        result = self.parser.parse(raw, self.meta)
        assert result.api is not None

    def test_path_input(self, tmp_path):
        response_file = tmp_path / "response.json"
        response_file.write_text(json.dumps(_CPI_RESPONSE), encoding="utf-8")
        result = self.parser.parse(response_file, self.meta)
        assert result.api.value == "315.605"

    def test_string_path_input(self, tmp_path):
        response_file = tmp_path / "response.json"
        response_file.write_text(json.dumps(_CPI_RESPONSE), encoding="utf-8")
        result = self.parser.parse(str(response_file), self.meta)
        assert result.api is not None

    def test_non_existent_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            self.parser.parse(Path("/nonexistent/response.json"), self.meta)

    def test_non_existent_string_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            self.parser.parse("/nonexistent/response.json", self.meta)

    def test_invalid_json_string_raises(self):
        with pytest.raises(ValueError, match="Cannot parse raw_data"):
            self.parser.parse("{not valid json}", self.meta)

    def test_invalid_bytes_raises(self):
        with pytest.raises(ValueError, match="Cannot decode"):
            self.parser.parse(b"{not valid json}", self.meta)

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported raw_data type"):
            self.parser.parse(12345, self.meta)

    def test_list_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported raw_data type"):
            self.parser.parse([], self.meta)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestAPIParserEdgeCases:
    def setup_method(self):
        self.parser = APIParser()

    def test_observation_without_catalog(self):
        resp = _make_response([
            {"seriesID": "CUUR0000SA0", "data": [_make_obs()]}
        ])
        meta = {"series_id": "CUUR0000SA0"}
        result = self.parser.parse(resp, meta)
        # No catalog — series_title and frequency should default to ""
        assert result.api.series_title == ""
        assert result.api.frequency == ""

    def test_latest_false_coerced(self):
        resp = _make_response([
            {"seriesID": "S1", "data": [_make_obs(latest="false")]}
        ])
        result = self.parser.parse(resp, {"series_id": "S1"})
        assert result.api.latest is False

    def test_value_preserved_exactly(self):
        """Numeric values must not be reformatted."""
        resp = _make_response([
            {"seriesID": "S1", "data": [_make_obs(value="315.605")]}
        ])
        result = self.parser.parse(resp, {"series_id": "S1"})
        assert result.api.value == "315.605"

    def test_parse_all_with_bytes_from_path(self, tmp_path):
        response_file = tmp_path / "response.json"
        response_file.write_text(json.dumps(_CPI_RESPONSE), encoding="utf-8")
        raw_bytes = response_file.read_bytes()
        results = self.parser.parse_all(raw_bytes, {"series_id": "CUUR0000SA0"})
        assert len(results) == 3

    def test_metadata_uuid_empty_when_not_provided(self):
        result = self.parser.parse(_CPI_RESPONSE, {})
        assert result.metadata.uuid == ""


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------

class TestAPIParserExport:
    def test_import_from_package(self):
        from pipeline.parsers import APIParser as Imported
        assert Imported is not None

    def test_is_subclass_of_base_parser(self):
        from pipeline.parsers import APIParser as Imported, BaseParser
        assert issubclass(Imported, BaseParser)
