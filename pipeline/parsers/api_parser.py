"""
api_parser.py — M15 API Parser

Converts raw BLS Public Data API v2 JSON responses into UnifiedObjects.

Each BLS API response contains one or more series, each with a list of
time-series observations (data points).  The parser converts each
observation into one UnifiedObject populated with APISchema.

Input contract (raw_data):
    dict  — parsed BLS API JSON response (from json.load / requests.json())
    str   — path string to a response.json file, OR raw JSON text
    bytes — raw JSON bytes
    Path  — filesystem path to a response.json file

The parser also accepts an optional ``series_id`` kwarg in *metadata* to
filter a specific series from a multi-series response.  When not supplied,
all series in the response are parsed.

Rules (from API_REGISTRY.md):
  - Preserve original numeric values exactly.
  - Never modify source JSON.
  - Validate before parsing: status, responseTime, Results, series.
  - Primary key: series_id + year + period.
  - Store unavailable values as null.

BLS API response structure (reference):
    {
        "status": "REQUEST_SUCCEEDED",
        "responseTime": 123,
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": "CUUR0000SA0",
                    "catalog": { ... },
                    "data": [
                        {
                            "year": "2026",
                            "period": "M06",
                            "periodName": "June",
                            "value": "315.605",
                            "latest": "true",
                            "footnotes": [{"code": "R", "text": "Revised."}]
                        }
                    ]
                }
            ]
        }
    }
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.parsers.base_parser import BaseParser
from pipeline.parsers.models import (
    APISchema,
    MetadataSchema,
    UnifiedObject,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_RESPONSE_KEYS = {"status", "responseTime", "Results"}
_SUCCEEDED_STATUS = "REQUEST_SUCCEEDED"


def _validate_response(payload: Dict[str, Any]) -> None:
    """
    Validate the top-level BLS API JSON response structure.

    Raises
    ------
    ValueError
        If any required key is missing, the status is not REQUEST_SUCCEEDED,
        or the Results structure is malformed.
    """
    missing = _REQUIRED_RESPONSE_KEYS - set(payload.keys())
    if missing:
        raise ValueError(
            f"BLS API response missing required keys: {sorted(missing)}"
        )

    status = payload.get("status")
    if status != _SUCCEEDED_STATUS:
        messages = payload.get("message") or []
        raise ValueError(
            f"BLS API response status is not REQUEST_SUCCEEDED: "
            f"status={status!r}, messages={messages}"
        )

    results = payload.get("Results", {})
    if not isinstance(results, dict) or "series" not in results:
        raise ValueError(
            "BLS API response 'Results' object missing 'series' key."
        )

    if not isinstance(results["series"], list):
        raise ValueError(
            "BLS API response 'Results.series' must be a list."
        )

    for i, s in enumerate(results["series"]):
        if "seriesID" not in s:
            raise ValueError(
                f"Series at index {i} missing required 'seriesID' field."
            )
        if "data" not in s:
            raise ValueError(
                f"Series '{s.get('seriesID', i)}' missing required 'data' field."
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_latest(value: Any) -> bool:
    """
    Normalise the BLS ``latest`` field.

    The BLS API returns ``latest`` as the string ``"true"`` on the most
    recent observation and omits it (or sets it to ``"false"``) on older
    ones.  Normalise to a Python bool.
    """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _footnotes_to_list(footnotes: Any) -> List[str]:
    """
    Convert the BLS ``footnotes`` field to a flat list of strings.

    BLS returns footnotes as a list of dicts like
    ``[{"code": "R", "text": "Revised."}]`` or as an empty list ``[{}]``.
    We normalise to a flat list of text strings, dropping empty entries.
    """
    if not footnotes or not isinstance(footnotes, list):
        return []
    result = []
    for fn in footnotes:
        if isinstance(fn, dict):
            text = fn.get("text", "").strip()
            if text:
                result.append(text)
    return result


def _build_api_schema(series_id: str, obs: Dict[str, Any]) -> APISchema:
    """
    Build an APISchema for a single BLS data-point observation.

    Values are preserved exactly as returned by the API.  Only the
    ``latest`` boolean coercion and footnote flattening are applied.
    """
    return APISchema(
        series_id=series_id,
        series_title=obs.get("seriesTitle", ""),  # may be absent in some responses
        frequency=obs.get("frequency", ""),
        year=obs.get("year", ""),
        period=obs.get("period", ""),
        period_name=obs.get("periodName", ""),
        value=obs.get("value", ""),
        latest=_coerce_latest(obs.get("latest", False)),
        footnotes=_footnotes_to_list(obs.get("footnotes", [])),
    )


def _build_metadata(metadata: Dict[str, Any], series_id: str) -> MetadataSchema:
    """Build a MetadataSchema from caller metadata, binding to a specific series."""
    return MetadataSchema(
        uuid=metadata.get("uuid", ""),
        dataset_id=metadata.get("dataset_id", ""),
        program_id=metadata.get("program_id", ""),
        series_id=series_id,
        collector=metadata.get("collector", "api_parser"),
        collector_version=metadata.get("collector_version", "1.0"),
        schema_version=metadata.get("schema_version", "1.0"),
        source_type=metadata.get("source_type", "API"),
        collection_timestamp=metadata.get("collection_timestamp", ""),
        normalization_timestamp=metadata.get("normalization_timestamp", ""),
        validation_status=metadata.get("validation_status", "PASS"),
        checksum=metadata.get("checksum", ""),
    )


# ---------------------------------------------------------------------------
# APIParser
# ---------------------------------------------------------------------------

class APIParser(BaseParser):
    """
    Parser for BLS Public Data API v2 responses (M15).

    Converts a raw API JSON response into one or more UnifiedObjects —
    **one per observation (data point)** per series.

    The ``parse()`` method satisfies the ``BaseParser`` contract by returning
    the first observation of the (optionally filtered) target series.
    Use ``parse_all()`` to get every observation.

    Accepted ``metadata`` keys
    --------------------------
    ================  =======================================================
    Key               Description
    ================  =======================================================
    uuid              Record UUID
    series_id         If set, only observations from this series are returned.
                      If absent, observations from all series are returned.
    dataset_id        Dataset identifier
    program_id        Program identifier
    collector         Collector name (default: ``api_parser``)
    collector_version Collector version (default: ``1.0``)
    schema_version    Schema version (default: ``1.0``)
    source_type       Must be ``API`` (default: ``API``)
    collection_timestamp  ISO-8601 UTC timestamp
    normalization_timestamp  ISO-8601 UTC timestamp
    validation_status ``PASS`` or ``FAIL``
    checksum          Checksum of the raw payload
    source_url        URL or path the response was collected from
    ================  =======================================================

    Usage::

        parser = APIParser()

        # From a parsed dict
        objects = parser.parse_all(response_dict, {"series_id": "CUUR0000SA0"})

        # From a response.json file path (enqueued by APICollector)
        from pathlib import Path
        objects = parser.parse_all(
            Path("/storage/raw/bls/api/2026/2026-07-18T08-30-00Z/response.json"),
            {"series_id": "CUUR0000SA0"}
        )
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, raw_data: Any, metadata: Dict[str, Any]) -> UnifiedObject:
        """
        Parse a BLS API JSON response and return the **first** observation.

        Satisfies the ``BaseParser`` contract.  For all observations use
        :meth:`parse_all`.

        Parameters
        ----------
        raw_data : dict | str | bytes | Path
            BLS API JSON response, or a path/string pointing to one.
        metadata : dict
            See class docstring for accepted keys.

        Returns
        -------
        UnifiedObject
            Populated with ``metadata`` and ``api`` for the first observation
            of the target series.  If the response has no data points,
            returns a metadata-only ``UnifiedObject``.

        Raises
        ------
        ValueError
            If ``raw_data`` cannot be decoded, the response is invalid, or
            the target ``series_id`` is not in the response.
        """
        objects = self.parse_all(raw_data, metadata)
        if objects:
            return objects[0]
        # Empty response — metadata-only object
        payload = self._normalise_input(raw_data)
        meta = _build_metadata(metadata, metadata.get("series_id", ""))
        return UnifiedObject(metadata=meta)

    def parse_all(
        self, raw_data: Any, metadata: Dict[str, Any]
    ) -> List[UnifiedObject]:
        """
        Parse a BLS API JSON response and return **one UnifiedObject per
        observation**.

        Parameters
        ----------
        raw_data : dict | str | bytes | Path
            BLS API JSON response.
        metadata : dict
            See class docstring.  Set ``"series_id"`` to filter to a single
            series; omit it to parse all series in the response.

        Returns
        -------
        list[UnifiedObject]
            One object per observation (data point).

        Raises
        ------
        ValueError
            Invalid input or malformed API response.
        """
        payload = self._normalise_input(raw_data)
        _validate_response(payload)

        target_series_id: Optional[str] = metadata.get("series_id") or None
        series_list: List[Dict[str, Any]] = payload["Results"]["series"]

        # Optionally filter to a single series
        if target_series_id:
            series_list = [
                s for s in series_list if s.get("seriesID") == target_series_id
            ]
            if not series_list:
                raise ValueError(
                    f"series_id '{target_series_id}' not found in API response. "
                    f"Available: {[s.get('seriesID') for s in payload['Results']['series']]}"
                )

        objects: List[UnifiedObject] = []

        for series in series_list:
            series_id = series["seriesID"]
            data_points: List[Dict[str, Any]] = series.get("data", [])

            # Attach catalog/series-level fields to each observation
            catalog = series.get("catalog", {})
            series_title = catalog.get("series_title", "")
            frequency = catalog.get("frequency", "")

            for obs in data_points:
                # Merge series-level fields into the observation dict
                obs_enriched = dict(obs)
                obs_enriched.setdefault("seriesTitle", series_title)
                obs_enriched.setdefault("frequency", frequency)

                meta = _build_metadata(metadata, series_id)
                api_schema = _build_api_schema(series_id, obs_enriched)
                objects.append(UnifiedObject(metadata=meta, api=api_schema))

        return objects

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_input(raw_data: Any) -> Dict[str, Any]:
        """
        Convert *raw_data* to a parsed Python dict.

        Accepted types:
            dict  — returned as-is
            bytes — decoded as UTF-8, then JSON-parsed
            Path  — read file, then JSON-parsed
            str   — if ending with .json treated as path; otherwise JSON-parsed

        Raises
        ------
        ValueError
            Unsupported type, file not found, or JSON decode error.
        """
        if isinstance(raw_data, dict):
            return raw_data

        if isinstance(raw_data, bytes):
            try:
                return json.loads(raw_data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(f"Cannot decode API response bytes: {exc}") from exc

        if isinstance(raw_data, Path):
            if not raw_data.exists():
                raise ValueError(f"Path does not exist: {raw_data}")
            try:
                return json.loads(raw_data.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Cannot parse JSON from file {raw_data}: {exc}"
                ) from exc

        if isinstance(raw_data, str):
            # Path string ending in .json
            if raw_data.endswith(".json"):
                p = Path(raw_data)
                if not p.exists():
                    raise ValueError(f"Path does not exist: {raw_data}")
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Cannot parse JSON from file {raw_data}: {exc}"
                    ) from exc
            # Raw JSON string
            try:
                return json.loads(raw_data)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Cannot parse raw_data as JSON string: {exc}"
                ) from exc

        raise ValueError(
            f"Unsupported raw_data type: {type(raw_data).__name__}. "
            "Expected dict, str, bytes, or Path."
        )
