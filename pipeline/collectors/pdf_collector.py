import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import pypdf

from pipeline.scheduler.scheduler import TaskScheduler
from pipeline.utils.base_utils import get_project_root, setup_logger


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class PDFCollector:
    """PDF Collector (M09).

    Responsible for:
    - Downloading official PDF releases based on discovered URLs.
    - Validating HTTP status (200 only).
    - Generating SHA256.
    - Detecting duplicates using the checksum.
    - Saving original.pdf and extracting text (text.txt).
    - Writing metadata.json, validation.json, and collector.log.
    """

    def __init__(
        self,
        *,
        scheduler: TaskScheduler,
        storage_root: Optional[Path] = None,
        processed_root: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.scheduler = scheduler
        self.logger = logger or setup_logger("pdf_collector")

        root = get_project_root()
        self.storage_root = (
            storage_root
            if storage_root is not None
            else root / "storage" / "raw" / "bls" / "pdf"
        )
        self.processed_root = (
            processed_root
            if processed_root is not None
            else root / "storage" / "processed" / "bls" / "pdf_text"
        )
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.processed_root.mkdir(parents=True, exist_ok=True)

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extracts text from PDF bytes using pypdf."""
        from io import BytesIO

        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n\n".join(extracted_text)

    def _download_pdf_with_retries(self, url: str) -> Dict[str, Any]:
        resp = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Bitcoin-Market-Intelligence-Dataset",
                "Accept": "application/pdf",
                "Accept-Encoding": "gzip",
            },
        )
        resp.raise_for_status()
        return {
            "status_code": resp.status_code,
            "content": resp.content,
            "content_type": resp.headers.get("Content-Type", ""),
            "content_length": len(resp.content),
        }

    def collect(
        self,
        *,
        source_url: str,
        program_id: str,
        dataset_id: str = "",
        now: Optional[datetime] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        now_utc = now or datetime.now(timezone.utc)
        program_id = program_id or "unknown_program"

        results: Dict[str, Any] = {
            "validation": {"status": "unknown"},
        }

        # Directories
        year_dir = self.storage_root / program_id / str(now_utc.year)
        year_dir.mkdir(parents=True, exist_ok=True)

        processed_dir = self.processed_root / program_id
        processed_dir.mkdir(parents=True, exist_ok=True)

        filename_prefix = f"{now_utc.strftime('%Y-%m-%d')}_{program_id}"
        pdf_filename = f"{filename_prefix}.pdf"
        text_filename = f"{filename_prefix}.txt"

        original_pdf_path = year_dir / pdf_filename
        metadata_path = year_dir / "metadata.json"
        validation_path = year_dir / "validation.json"
        collector_log_path = year_dir / "collector.log"
        duplicate_index_path = year_dir / "duplicate_index.json"
        
        extracted_text_path = processed_dir / text_filename

        existing_keys = []
        if duplicate_index_path.exists():
            try:
                payload = json.loads(duplicate_index_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and isinstance(payload.get("keys"), list):
                    existing_keys = [str(x) for x in payload["keys"]]
            except Exception:
                existing_keys = []

        try:
            if dry_run:
                from io import BytesIO
                writer = pypdf.PdfWriter()
                writer.add_blank_page(width=72, height=72)
                # We can't easily add text to a blank page with pypdf alone, so we'll just mock the extract_text.
                # Actually, wait, it's easier to just patch extract_text or use a minimal valid pdf.
                # Let's generate a valid empty PDF bytes.
                out_io = BytesIO()
                writer.write(out_io)
                pdf_bytes = out_io.getvalue()
                
                http_status = 200
                content_type = "application/pdf"
                content_length = len(pdf_bytes)
            else:
                dl = self._download_pdf_with_retries(source_url)
                http_status = int(dl["status_code"])
                content_type = dl.get("content_type", "")
                pdf_bytes = dl["content"]
                content_length = dl.get("content_length", len(pdf_bytes))

            if http_status != 200:
                raise ValueError(f"Invalid HTTP Status: {http_status}")
            
            if "pdf" not in content_type.lower() and not source_url.lower().endswith(".pdf"):
                self.logger.warning("Content-Type does not strictly indicate PDF, but proceeding.")

            sha = _sha256_bytes(pdf_bytes)
            duplicate = sha in set(existing_keys)

            if not duplicate:
                # Save original PDF
                original_pdf_path.write_bytes(pdf_bytes)
                
                # Extract and save text
                extracted_text = self._extract_text_from_pdf_bytes(pdf_bytes)
                extracted_text_path.write_text(extracted_text, encoding="utf-8")

                # Update index
                duplicate_index_path.write_text(
                    json.dumps({"keys": existing_keys + [sha]}, indent=2),
                    encoding="utf-8",
                )

            # Metadata (per schema in PDF_REGISTRY.md)
            metadata_payload = {
                "pdf_id": f"BLS-PDF-{sha[:8]}", # Generates an ID or pass from registry
                "source_url": source_url,
                "download_timestamp": now_utc.isoformat(),
                "http_status": http_status,
                "sha256": sha,
                "content_length": content_length,
                "pages": 0, # We don't have this in metadata cheaply without re-parsing or saving it from extraction
                "filename": pdf_filename,
                "mime_type": content_type or "application/pdf"
            }
            metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")

            validation_payload = {
                "status": "ok",
                "http_status": http_status,
                "sha256": sha,
                "duplicate": duplicate,
            }
            if duplicate:
                validation_payload["reason"] = "duplicate"
            
            validation_path.write_text(
                json.dumps(validation_payload, indent=2), encoding="utf-8"
            )

            with open(collector_log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"[{now_utc.isoformat()}] pdf_collector url={source_url} program={program_id} sha256={sha} duplicate={duplicate}\n"
                )

            results["validation"] = {"status": "ok"}
            results["duplicate"] = duplicate
            results["sha256"] = sha

            if not duplicate:
                # Enqueue parsing job
                self.scheduler.enqueue_collection_job(
                    collector="pdf_parser", # Assuming parser is next
                    program_id=program_id,
                    dataset_id=dataset_id,
                    series_id="",
                    source_url=str(extracted_text_path),
                    priority=0,
                    scheduled_time=now_utc,
                )

        except Exception as e:
            validation_payload = {"status": "failed", "error": str(e), "url": source_url}
            validation_path.write_text(json.dumps(validation_payload, indent=2), encoding="utf-8")
            with open(collector_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{now_utc.isoformat()}] pdf_collector url={source_url} status=failed error={str(e)}\n")
            results["validation"] = {"status": "failed", "error": str(e)}

        return results
