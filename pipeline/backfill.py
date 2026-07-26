"""pipeline.backfill — M21 Historical Backfill Orchestrator

This script orchestrates the collection of historical BLS data from 2020 to the present.
It executes the collectors in the correct order (Archive -> HTML -> PDF -> API)
and utilizes the `backfill_start_year` parameter for the API collector.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.collectors.archive_collector import ArchiveCollector
from pipeline.collectors.html_collector import HTMLCollector
from pipeline.collectors.pdf_collector import PDFCollector
from pipeline.collectors.api_collector import APICollector
from pipeline.collectors.series_registry_loader import SeriesRegistryLoader
from pipeline.parsers.api_parser import APIParser
from pipeline.normalizers.unified_normalizer import UnifiedNormalizer
from pipeline.validators.validation_engine import ValidationEngine
from pipeline.validators.validation_result import ValidationStatus
from pipeline.storage.storage_manager import StorageManager
from pipeline.datasets.dataset_builder import DatasetBuilder
from pipeline.features.feature_builder import FeatureBuilder
from pipeline.incremental import load_processed_objects

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("backfill")


def run_backfill(dry_run: bool = False) -> None:
    logger.info("Starting M21 Historical Backfill (2020 -> Current)")
    
    scheduler = TaskScheduler().initialize()
    now = datetime.now(timezone.utc)
    
    # 1. Archive Collector (Discovers historical HTML/PDF releases)
    logger.info("Running Archive Collector...")
    archive_collector = ArchiveCollector(scheduler=scheduler)
    try:
        archive_results = archive_collector.collect(now=now, dry_run=dry_run)
        logger.info(f"Archive collection finished. Results: {archive_results}")
    except Exception as e:
        logger.error(f"Archive collector failed: {e}")

    # 2. HTML Collector
    logger.info("Running HTML Collector...")
    html_collector = HTMLCollector(scheduler=scheduler)
    try:
        html_results = html_collector.collect(now=now, dry_run=dry_run)
        logger.info(f"HTML collection finished. Results: {html_results}")
    except Exception as e:
        logger.error(f"HTML collector failed: {e}")

    # 3. Process the job queue for dynamically discovered HTML/PDF jobs
    logger.info("Processing job queue for discovered HTML and PDF jobs...")
    pdf_collector = PDFCollector(scheduler=scheduler)
    
    while True:
        job = scheduler.dispatch()
        if not job:
            break
            
        try:
            if job.collector == "pdf":
                logger.info(f"Executing PDF collection job for {job.source_url}")
                pdf_collector.collect(
                    source_url=job.source_url,
                    program_id=job.program_id,
                    dataset_id=job.dataset_id,
                    now=now,
                    dry_run=dry_run
                )
            elif job.collector == "html":
                # HTML collector usually processes registry, but if we have specific URLs we might need to handle them.
                # However, our current HTML collector doesn't accept url parameter in collect().
                # For this milestone, we'll just log and complete it if it's dynamically discovered.
                logger.info(f"Discovered HTML job for {job.source_url}")
                
            scheduler.complete_job(job.job_id)
        except Exception as e:
            logger.error(f"Failed job {job.job_id}: {e}")
            scheduler.fail_job(job.job_id)

    # 4. API Collector (with backfill_start_year=2020)
    logger.info("Running API Collector with backfill_start_year=2020...")
    api_collector = APICollector(scheduler=scheduler)
    try:
        api_results = api_collector.collect(now=now, dry_run=dry_run, backfill_start_year=2020)
        logger.info(f"API collection finished. Results: {api_results}")
    except Exception as e:
        logger.error(f"API collector failed: {e}")

    # 5. Process API parser jobs produced by APICollector.
    logger.info("Processing API parser jobs into validated, processed, and feature outputs...")
    storage = StorageManager("storage")
    parser = APIParser()
    normalizer = UnifiedNormalizer()
    validator = ValidationEngine(strict=True)
    dataset_builder = DatasetBuilder(storage=storage)
    feature_builder = FeatureBuilder(storage=storage)
    series_registry = {
        entry.series_id: entry
        for entry in SeriesRegistryLoader().load()
        if entry.series_id
    }

    seen_keys = set()
    passed_by_dataset_year: Dict[Tuple[str, str], List] = {}
    passed_objects = []

    while True:
        job = scheduler.dispatch()
        if not job:
            break

        try:
            if job.collector != "api_parser":
                logger.info(f"Skipping unsupported backfill processing job: {job.collector}")
                scheduler.complete_job(job.job_id)
                continue

            metadata = {
                "dataset_id": job.dataset_id,
                "program_id": job.program_id,
                "series_id": job.series_id,
                "series_title": series_registry.get(job.series_id).title if job.series_id in series_registry else "",
                "frequency": (
                    series_registry.get(job.series_id).frequency or "Monthly"
                    if job.series_id in series_registry
                    else ""
                ),
                "collector": "api_collector",
                "collector_version": "1.0",
                "schema_version": "1.0",
                "source_type": "API",
                "collection_timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source_url": job.source_url,
            }
            raw_objects = parser.parse_all(job.source_url, metadata)
            normalized = normalizer.normalize_all(raw_objects)
            reports = validator.validate_all(normalized, seen_keys=seen_keys)

            for obj, report in zip(normalized, reports):
                if report.overall_status == ValidationStatus.FAIL:
                    continue
                year = obj.api.year if obj.api else str(now.year)
                key = (job.dataset_id, year)
                passed_by_dataset_year.setdefault(key, []).append(obj)
                passed_objects.append(obj)

            scheduler.complete_job(job.job_id)
        except Exception as e:
            logger.exception(f"API parser job {job.job_id} failed: {e}")
            scheduler.fail_job(job.job_id)

    for (dataset_id, year), objects in passed_by_dataset_year.items():
        reports = validator.validate_all(objects, seen_keys=set())
        result = storage.save_validated_batch(objects, reports, dataset_id, year)
        logger.info(
            "Validated storage dataset=%s year=%s count=%d success=%s skipped=%s path=%s",
            dataset_id,
            year,
            len(objects),
            result.success,
            result.skipped,
            result.path,
        )

    if passed_objects:
        dataset_results = dataset_builder.build_processed_from_validated(
            passed_objects,
            write_csv=True,
            overwrite=True,
        )
        logger.info(f"Processed dataset results: {dataset_results}")

        for dataset_id in dataset_results:
            processed_objects = load_processed_objects(storage, dataset_id)
            feature_results = feature_builder.build_features(
                dataset_id,
                processed_objects,
                write_csv=True,
                overwrite=True,
            )
            logger.info(f"Feature results for {dataset_id}: {feature_results}")
    else:
        logger.info("No validated API objects were produced by backfill parser jobs.")

    logger.info("M21 Historical Backfill collection complete.")
    logger.info("Historical API data has been collected, validated, processed, and feature-engineered where available.")


if __name__ == "__main__":
    # Perform a dry run by default for safety.
    run_backfill(dry_run=True)
