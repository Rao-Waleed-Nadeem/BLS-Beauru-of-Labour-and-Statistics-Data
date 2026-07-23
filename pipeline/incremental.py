"""pipeline.incremental — M22 Incremental Updates Orchestrator

This script orchestrates the collection and processing of incremental BLS updates.
It checks the calendar, RSS feeds, and archives for new releases, enqueues collection jobs,
and processes them through parsing, normalization, validation, storage, dataset building,
and feature engineering.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.scheduler.models import Job, JobStatus
from pipeline.collectors.calendar_collector import CalendarCollector
from pipeline.collectors.archive_collector import ArchiveCollector
from pipeline.collectors.rss_collector import RSSCollector
from pipeline.collectors.html_collector import HTMLCollector
from pipeline.collectors.pdf_collector import PDFCollector
from pipeline.collectors.api_collector import APICollector

from pipeline.parsers.api_parser import APIParser
from pipeline.parsers.pdf_parser import PDFParser
from pipeline.parsers.models import (
    UnifiedObject,
    MetadataSchema,
    APISchema,
    PDFSchema,
    HTMLSchema,
    ReleaseSchema,
    EventSchema,
    AttachmentSchema,
    RelationshipSchema,
)
from pipeline.normalizers.unified_normalizer import UnifiedNormalizer
from pipeline.validators.validation_engine import ValidationEngine
from pipeline.storage.storage_manager import StorageManager
from pipeline.datasets.dataset_builder import DatasetBuilder
from pipeline.features.feature_builder import FeatureBuilder

logger = logging.getLogger("incremental")


def dict_to_unified_object(d: Dict[str, Any]) -> UnifiedObject:
    """Safely convert a serialized dictionary back into a UnifiedObject."""
    def clean_fields(cls, data_dict):
        if not data_dict:
            return None
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data_dict.items() if k in field_names})

    metadata = clean_fields(MetadataSchema, d.get("metadata"))
    api = clean_fields(APISchema, d.get("api"))
    release = clean_fields(ReleaseSchema, d.get("release"))
    event = clean_fields(EventSchema, d.get("event"))
    html = clean_fields(HTMLSchema, d.get("html"))
    pdf = clean_fields(PDFSchema, d.get("pdf"))
    attachments = clean_fields(AttachmentSchema, d.get("attachments"))
    relationships = clean_fields(RelationshipSchema, d.get("relationships"))

    return UnifiedObject(
        metadata=metadata,
        release=release,
        event=event,
        api=api,
        html=html,
        pdf=pdf,
        attachments=attachments,
        relationships=relationships,
    )


def load_processed_objects(storage: StorageManager, dataset_id: str) -> List[UnifiedObject]:
    """Load existing processed objects from the storage hierarchy."""
    path = storage.root / "processed" / "bls" / dataset_id / "dataset.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [dict_to_unified_object(item) for item in data]
        return [dict_to_unified_object(data)]
    except Exception as e:
        logger.error(f"Failed to load processed dataset for {dataset_id}: {e}")
        return []


def load_validated_objects(storage: StorageManager, dataset_id: str) -> List[UnifiedObject]:
    """Load validated objects across all years for a dataset."""
    validated_dir = storage.root / "validated" / "bls" / dataset_id
    if not validated_dir.exists():
        return []
    objs = []
    for json_path in validated_dir.glob("**/validated.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    objs.append(dict_to_unified_object(item))
            else:
                objs.append(dict_to_unified_object(data))
        except Exception as e:
            logger.error(f"Failed to load validated objects from {json_path}: {e}")
    return objs


def run_incremental(
    now: Optional[datetime] = None,
    dry_run: bool = False,
    storage_root: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs the daily update pipeline incrementally."""
    logger.info("Starting M22 Incremental Update (Daily Mode)")

    now_utc = now or datetime.now(timezone.utc)

    scheduler = TaskScheduler().initialize()
    storage = StorageManager(storage_root or "storage")
    normalizer = UnifiedNormalizer()
    validator = ValidationEngine(strict=True)
    dataset_builder = DatasetBuilder(storage=storage)
    feature_builder = FeatureBuilder(storage=storage)

    # Initialize collectors with explicit storage roots
    calendar_collector = CalendarCollector(
        scheduler=scheduler,
        storage_root=storage.root / "raw" / "bls" / "calendar",
    )
    archive_collector = ArchiveCollector(
        scheduler=scheduler,
        storage_root=storage.root / "raw" / "bls" / "archive",
    )
    rss_collector = RSSCollector(
        scheduler=scheduler,
        storage_root=storage.root / "raw" / "bls" / "rss",
    )
    html_collector = HTMLCollector(
        scheduler=scheduler,
        storage_root=storage.root / "raw" / "bls" / "html",
    )
    pdf_collector = PDFCollector(
        scheduler=scheduler,
        storage_root=storage.root / "raw" / "bls" / "pdf",
    )
    api_collector = APICollector(
        scheduler=scheduler,
        storage_root=storage.root / "raw" / "bls" / "api",
    )

    # 1. Schedule sync jobs (calendar_sync, archive_sync, rss_sync)
    scheduler.schedule_sync_jobs(now=now_utc)

    updated_datasets: Set[str] = set()

    # Track seen keys for duplicate detection in this execution run
    seen_keys: Set[str] = set()

    # Process job queue
    while True:
        job = scheduler.dispatch()
        if not job:
            break

        logger.info(
            f"Dispatched job: ID={job.job_id}, collector={job.collector}, "
            f"program={job.program_id}, dataset={job.dataset_id}"
        )

        try:
            if job.collector == "calendar_sync":
                calendar_collector.collect(now=now_utc, dry_run=dry_run)

            elif job.collector == "archive_sync":
                archive_collector.collect(now=now_utc, dry_run=dry_run)

            elif job.collector == "rss_sync":
                rss_collector.collect(now=now_utc, dry_run=dry_run)

            elif job.collector == "calendar_event":
                # Only trigger if the scheduled time has arrived or past
                if now_utc >= job.scheduled_time:
                    # Enqueue HTML/PDF/API jobs for program
                    registry = scheduler.registry_cache
                    for dataset in registry.datasets.values():
                        if dataset.program_id == job.program_id:
                            for method in dataset.collection_methods:
                                method_lower = method.lower()
                                if method_lower == "api":
                                    scheduler.enqueue_collection_job(
                                        collector="api",
                                        program_id=dataset.program_id,
                                        dataset_id=dataset.dataset_id,
                                        priority=0,
                                        scheduled_time=now_utc,
                                    )
                                elif method_lower == "html":
                                    scheduler.enqueue_collection_job(
                                        collector="html",
                                        program_id=dataset.program_id,
                                        dataset_id=dataset.dataset_id,
                                        source_url=job.source_url or dataset.page_url,
                                        priority=0,
                                        scheduled_time=now_utc,
                                    )
                                elif method_lower == "pdf":
                                    scheduler.enqueue_collection_job(
                                        collector="pdf",
                                        program_id=dataset.program_id,
                                        dataset_id=dataset.dataset_id,
                                        source_url=job.source_url,
                                        priority=0,
                                        scheduled_time=now_utc,
                                    )

            elif job.collector == "html":
                html_collector.collect(now=now_utc, dry_run=dry_run)

            elif job.collector == "pdf":
                pdf_collector.collect(
                    source_url=job.source_url,
                    program_id=job.program_id,
                    dataset_id=job.dataset_id,
                    now=now_utc,
                    dry_run=dry_run,
                )

            elif job.collector == "api":
                api_collector.collect(now=now_utc, dry_run=dry_run)

            elif job.collector == "api_parser":
                parser = APIParser()
                metadata = {
                    "dataset_id": job.dataset_id,
                    "program_id": job.program_id,
                    "series_id": job.series_id,
                    "collector": "api_collector",
                    "collector_version": "1.0",
                    "schema_version": "1.0",
                    "source_type": "API",
                    "collection_timestamp": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "source_url": job.source_url,
                }
                raw_objects = parser.parse_all(job.source_url, metadata)

                # Load existing processed records to populate seen_keys for duplicate detection
                if job.dataset_id:
                    existing_objs = load_processed_objects(storage, job.dataset_id)
                    for ext in existing_objs:
                        if ext.api:
                            seen_keys.add(f"api::{ext.api.series_id}::{ext.api.year}::{ext.api.period}")
                        if ext.metadata and ext.metadata.checksum:
                            seen_keys.add(f"checksum::{ext.metadata.checksum}")

                normalized = normalizer.normalize_all(raw_objects)
                reports = validator.validate_all(normalized, seen_keys=seen_keys)

                passed_objs = []
                passed_reps = []
                from pipeline.validators.validation_result import ValidationStatus
                for o, r in zip(normalized, reports):
                    if r.overall_status != ValidationStatus.FAIL:
                        passed_objs.append(o)
                        passed_reps.append(r)

                if passed_objs:
                    # Group by year
                    by_year = {}
                    for o, r in zip(passed_objs, passed_reps):
                        year = o.api.year if o.api else str(now_utc.year)
                        by_year.setdefault(year, []).append((o, r))

                    for year, pairs in by_year.items():
                        year_objs, year_reps = zip(*pairs)
                        storage.save_validated_batch(list(year_objs), list(year_reps), job.dataset_id, year)

                    updated_datasets.add(job.dataset_id)

            elif job.collector == "pdf_parser":
                parser = PDFParser()
                metadata = {
                    "dataset_id": job.dataset_id,
                    "program_id": job.program_id,
                    "series_id": job.series_id,
                    "collector": "pdf_collector",
                    "collector_version": "1.0",
                    "schema_version": "1.0",
                    "source_type": "PDF",
                    "collection_timestamp": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "source_url": job.source_url,
                }

                # Load existing processed records to populate seen_keys
                if job.dataset_id:
                    existing_objs = load_processed_objects(storage, job.dataset_id)
                    for ext in existing_objs:
                        if ext.metadata and ext.metadata.checksum:
                            seen_keys.add(f"checksum::{ext.metadata.checksum}")

                obj = parser.parse(job.source_url, metadata)
                normalized = normalizer.normalize(obj)
                report = validator.validate(normalized, seen_keys=seen_keys)

                from pipeline.validators.validation_result import ValidationStatus
                if report.overall_status != ValidationStatus.FAIL:
                    year = (
                        normalized.pdf.filename.split("_")[0].split("-")[0]
                        if (normalized.pdf and normalized.pdf.filename)
                        else str(now_utc.year)
                    )
                    storage.save_validated(normalized, report, job.dataset_id, year)
                    updated_datasets.add(job.dataset_id)

            scheduler.complete_job(job.job_id)
            logger.info(f"Job {job.job_id} completed successfully.")

        except Exception as e:
            logger.exception(f"Job {job.job_id} failed: {e}")
            scheduler.fail_job(job.job_id)

    # 3. Post-execution Dataset & Feature updates
    results = {}
    for dataset_id in updated_datasets:
        if not dataset_id:
            continue
        try:
            logger.info(f"Rebuilding processed dataset and features for {dataset_id}...")
            # Load validated objects for this dataset
            validated_objs = load_validated_objects(storage, dataset_id)

            # Rebuild dataset (overwrite=True is allowed for incremental runs)
            ds_result = dataset_builder.build_processed_from_validated(
                validated_objs,
                write_csv=True,
                overwrite=True,
            )

            # Rebuild features (overwrite=True is allowed for incremental runs)
            processed_objs = load_processed_objects(storage, dataset_id)
            feat_result = feature_builder.build_features(
                dataset_id,
                processed_objs,
                write_csv=True,
                overwrite=True,
            )

            results[dataset_id] = {
                "dataset": ds_result.get(dataset_id),
                "features": feat_result,
            }
        except Exception as e:
            logger.exception(f"Failed to rebuild dataset or features for {dataset_id}: {e}")

    return {
        "status": "complete",
        "updated_datasets": list(updated_datasets),
        "results": results,
    }


if __name__ == "__main__":
    import sys
    # Support direct execution with logging to stdout
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    run_incremental(dry_run="--dry-run" in sys.argv)
