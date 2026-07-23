import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from BLS.pipeline.collectors.series_registry_loader import SeriesRegistryLoader, SeriesRegistryEntry
from BLS.pipeline.scheduler.scheduler import TaskScheduler
from BLS.pipeline.utils.base_utils import get_project_root, setup_logger


class APICollector:
    """API Collector (M10).

    Responsible for:
    - Loading series from SERIES_REGISTRY.md
    - Batching series IDs up to 50 per request
    - Making POST requests to BLS Public Data API v2
    - Handling API Keys if present
    - Validating responses
    - Saving raw JSON responses immutably
    - Enqueueing parsing jobs
    """

    def __init__(
        self,
        *,
        scheduler: TaskScheduler,
        registry_loader: Optional[SeriesRegistryLoader] = None,
        storage_root: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.scheduler = scheduler
        self.registry_loader = registry_loader or SeriesRegistryLoader()
        self.logger = logger or setup_logger("api_collector")

        root = get_project_root()
        self.storage_root = (
            storage_root
            if storage_root is not None
            else root / "storage" / "raw" / "bls" / "api"
        )
        self.storage_root.mkdir(parents=True, exist_ok=True)

        self.api_key = os.environ.get("BLS_API_KEY", "")
        self.endpoint = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def _validate_json_response(self, payload: Dict[str, Any], requested_series: List[str]) -> None:
        """Validates the structure of the BLS API JSON response."""
        required_keys = ["status", "responseTime", "Results"]
        for key in required_keys:
            if key not in payload:
                raise ValueError(f"Missing required key in response: {key}")

        if payload.get("status") != "REQUEST_SUCCEEDED":
            messages = payload.get("message") or []
            raise ValueError(f"BLS API request failed: {messages}")

        results = payload.get("Results", {})
        if not isinstance(results, dict) or "series" not in results:
            raise ValueError("Missing 'series' key in 'Results'")

        if not isinstance(results["series"], list):
            raise ValueError("'Results.series' must be a list")

        returned_series_ids = []
        for s in results["series"]:
            if "seriesID" not in s or "data" not in s:
                raise ValueError("Series object missing 'seriesID' or 'data'")
            returned_series_ids.append(s["seriesID"])

        missing = set(requested_series) - set(returned_series_ids)
        unexpected = set(returned_series_ids) - set(requested_series)
        if missing:
            raise ValueError(f"Requested series not found in response: {sorted(missing)}")
        if unexpected:
            raise ValueError(f"Response contained unrequested series: {sorted(unexpected)}")

    def _post_with_retries(
        self, payload: Dict[str, Any], dry_run: bool = False
    ) -> Tuple[Dict[str, Any], int, int]:
        """Makes a POST request to the BLS API with basic retry logic for transient errors."""
        if dry_run:
            return {
                "status": "REQUEST_SUCCEEDED",
                "responseTime": 100,
                "message": [],
                "Results": {
                    "series": [
                        {"seriesID": s_id, "data": []} for s_id in payload.get("seriesid", [])
                    ]
                }
            }, 200, 0

        max_attempts = 3
        delay = 2

        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(
                    self.endpoint,
                    json=payload,
                    timeout=30,
                    headers={
                        "User-Agent": "Bitcoin-Market-Intelligence-Dataset",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                
                # BLS sends 200 even for errors in payload sometimes, but HTTP 429/500 are standard.
                if resp.status_code in (202, 429, 500, 502, 503, 504):
                    self.logger.warning(f"Transient error {resp.status_code}, attempt {attempt}/{max_attempts}")
                    if attempt < max_attempts:
                        time.sleep(delay ** attempt)
                        continue
                    resp.raise_for_status()
                
                if resp.status_code != 200:
                    resp.raise_for_status()

                try:
                    return resp.json(), resp.status_code, attempt - 1
                except json.JSONDecodeError:
                    if attempt < max_attempts:
                        time.sleep(delay ** attempt)
                        continue
                    raise ValueError("Failed to decode JSON from BLS API")
                    
            except requests.RequestException as e:
                self.logger.warning(f"Request failed: {e}, attempt {attempt}/{max_attempts}")
                if attempt == max_attempts:
                    raise e
                time.sleep(delay ** attempt)
        
        raise RuntimeError("Unreachable")

    def _normalize_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create parser-ready JSON while preserving all original API values."""
        return {
            "collector": "api_collector",
            "collector_version": "m10",
            "status": payload.get("status"),
            "responseTime": payload.get("responseTime"),
            "series": payload.get("Results", {}).get("series", []),
        }

    def _batch_dir(self, year: str, timestamp: str, batch_number: int) -> Path:
        if batch_number == 1:
            return self.storage_root / year / timestamp
        return self.storage_root / year / f"{timestamp}-batch-{batch_number:03d}"

    def collect(
        self,
        *,
        now: Optional[datetime] = None,
        dry_run: bool = False,
        backfill_start_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        now_utc = now or datetime.now(timezone.utc)
        entries = [e for e in self.registry_loader.load() if e.enabled and e.collection_method.upper() == "API"]

        if not entries:
            return {"status": "no_entries"}

        results = {
            "batches": 0,
            "success": 0,
            "failed": 0,
            "details": [],
        }

        # The BLS API allows max 50 series per request for registered users.
        # We group series by their startyear/endyear parameters if possible, 
        # but for simplicity and safety against mixed parameters, we'll batch them up to 50 
        # using a common set of parameters if they share them, or group by parameters.

        seen_series_ids = set()
        duplicate_series_ids = set()
        for entry in entries:
            if not entry.series_id:
                raise ValueError(f"Series registry entry missing series_id: {entry.entry_id}")
            if entry.series_id in seen_series_ids:
                duplicate_series_ids.add(entry.series_id)
            seen_series_ids.add(entry.series_id)
        if duplicate_series_ids:
            raise ValueError(f"Duplicate series IDs in registry: {sorted(duplicate_series_ids)}")

        groups: Dict[str, List[SeriesRegistryEntry]] = {}
        for entry in entries:
            startyear = entry.api_payload.get("startyear", str(now_utc.year - 1))
            if backfill_start_year is not None:
                startyear = str(backfill_start_year)
            endyear = entry.api_payload.get("endyear", str(now_utc.year))
            key = f"{startyear}_{endyear}"
            groups.setdefault(key, []).append(entry)

        batch_number = 0
        for key, group_entries in groups.items():
            startyear, endyear = key.split("_")
            
            # chunk into 50s
            chunk_size = 50
            for i in range(0, len(group_entries), chunk_size):
                chunk = group_entries[i:i + chunk_size]
                series_ids = [e.series_id for e in chunk if e.series_id]
                
                if not series_ids:
                    continue
                
                results["batches"] += 1
                batch_number += 1
                
                payload = {
                    "seriesid": series_ids,
                    "startyear": startyear,
                    "endyear": endyear,
                    "catalog": True,
                    "calculations": True,
                    "annualaverage": True,
                }
                if self.api_key:
                    payload["registrationkey"] = self.api_key

                timestamp_str = now_utc.strftime("%Y-%m-%dT%H-%M-%SZ")
                year_str = str(now_utc.year)
                
                # As per API_REGISTRY.md storage standard
                batch_dir = self._batch_dir(year_str, timestamp_str, batch_number)
                batch_dir.mkdir(parents=True, exist_ok=True)
                
                request_path = batch_dir / "request.json"
                response_path = batch_dir / "response.json"
                normalized_path = batch_dir / "normalized.json"
                validation_path = batch_dir / "validation_report.json"
                log_path = batch_dir / "request.log"
                
                request_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                
                try:
                    start_time = time.monotonic()
                    resp_json, http_status, retry_count = self._post_with_retries(payload, dry_run=dry_run)
                    duration = time.monotonic() - start_time
                    
                    response_path.write_text(json.dumps(resp_json, indent=2), encoding="utf-8")
                    
                    self._validate_json_response(resp_json, series_ids)
                    normalized_path.write_text(
                        json.dumps(self._normalize_response(resp_json), indent=2),
                        encoding="utf-8",
                    )
                    
                    validation_payload = {
                        "status": "ok",
                        "http_status": http_status,
                        "retry_count": retry_count,
                        "series_requested": len(series_ids),
                        "series_returned": len(resp_json.get("Results", {}).get("series", [])),
                    }
                    validation_path.write_text(json.dumps(validation_payload, indent=2), encoding="utf-8")
                    
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(
                            f"[{now_utc.isoformat()}] series={','.join(series_ids)} "
                            f"endpoint={self.endpoint} http_status={http_status} "
                            f"response_time={resp_json.get('responseTime')} retry_count={retry_count} "
                            f"validation_status=ok duration={duration:.2f}s file={response_path}\n"
                        )
                    
                    results["success"] += 1
                    results["details"].append({"series": series_ids, "status": "ok"})
                    
                    # Enqueue parsing jobs
                    for e in chunk:
                        self.scheduler.enqueue_collection_job(
                            collector="api_parser",
                            program_id=e.program_id,
                            dataset_id=e.dataset_id,
                            series_id=e.series_id,
                            source_url=str(response_path),
                            priority=0,
                            scheduled_time=now_utc,
                        )

                except Exception as ex:
                    validation_payload = {"status": "failed", "error": str(ex)}
                    validation_path.write_text(json.dumps(validation_payload, indent=2), encoding="utf-8")
                    
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(
                            f"[{now_utc.isoformat()}] series={','.join(series_ids)} "
                            f"endpoint={self.endpoint} validation_status=failed error={str(ex)}\n"
                        )
                    
                    results["failed"] += 1
                    results["details"].append({"series": series_ids, "status": "failed", "error": str(ex)})

        return results
