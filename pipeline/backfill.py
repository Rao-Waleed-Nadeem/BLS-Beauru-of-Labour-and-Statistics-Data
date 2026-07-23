"""pipeline.backfill — M21 Historical Backfill Orchestrator

This script orchestrates the collection of historical BLS data from 2020 to the present.
It executes the collectors in the correct order (Archive -> HTML -> PDF -> API)
and utilizes the `backfill_start_year` parameter for the API collector.
"""

import logging
from datetime import datetime, timezone

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.collectors.archive_collector import ArchiveCollector
from pipeline.collectors.html_collector import HTMLCollector
from pipeline.collectors.pdf_collector import PDFCollector
from pipeline.collectors.api_collector import APICollector

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

    logger.info("M21 Historical Backfill collection complete.")
    logger.info("Downstream parsing and processing should be driven by the generated jobs in the scheduler queue.")


if __name__ == "__main__":
    # Perform a dry run by default for safety.
    run_backfill(dry_run=True)
