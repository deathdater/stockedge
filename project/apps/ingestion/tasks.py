import csv
import hashlib
import io
import logging
import re
import time
import zipfile
from datetime import datetime, timedelta

import requests
from celery import chunks, shared_task
from django.db import transaction
from django.utils import timezone

from project.apps.ingestion.metrics import incr
from project.apps.ingestion.models import IngestionRun
from project.apps.ingestion.validators import DataValidator
from project.apps.market_data.models import DailyCandle

logger = logging.getLogger(__name__)

BHAVCOPY_URL_TEMPLATE = "https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PR{date_yy}.zip"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
MAX_RETRIES = 5
RETRY_BACKOFF_SECONDS = 60


class TransientDownloadError(Exception):
    pass


def _format_yy(date_obj: datetime) -> str:
    return date_obj.strftime("%d%m%y")


def _download_zip(date_obj: datetime) -> tuple[bytes, str, str] | None:
    date_yy = _format_yy(date_obj)
    url = BHAVCOPY_URL_TEMPLATE.format(date_yy=date_yy)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    if response.status_code >= 500:
        raise TransientDownloadError(f"server error status={response.status_code}")
    if response.status_code == 404:
        # No bhavcopy for this date — likely a market holiday
        return None
    response.raise_for_status()
    payload = response.content
    return payload, hashlib.sha256(payload).hexdigest(), url


def _extract_pd_csv(zip_bytes: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            if re.match(r"^Pd.*csv$", info.filename):
                with archive.open(info.filename, "r") as fh:
                    content = io.TextIOWrapper(fh, encoding="utf-8")
                    return list(csv.DictReader(content))
    raise ValueError("Pd CSV file not found in PR zip archive")


@shared_task(
    bind=True,
    autoretry_for=(TransientDownloadError, requests.Timeout, requests.ConnectionError),
    retry_backoff=RETRY_BACKOFF_SECONDS,
    retry_jitter=True,
    retry_kwargs={"max_retries": MAX_RETRIES},
)
def download_bhavcopy(self, date_str: str, expected_sha256: str | None = None):
    started = time.monotonic()
    date_obj = datetime.strptime(date_str, "%d%m%Y")
    trade_date = date_obj.date()
    run = IngestionRun.objects.create(source_date=trade_date, source="bhavcopy_daily")

    logger.info("ingestion.run.started", extra={"event": "ingestion.run.started", "run_id": run.id, "date": date_str})
    incr("ingestion_runs_started")

    try:
        result = _download_zip(date_obj)
        if result is None:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            run.status = IngestionRun.Status.SKIPPED if hasattr(IngestionRun.Status, "SKIPPED") else IngestionRun.Status.FAILED
            run.finished_at = timezone.now()
            run.elapsed_ms = elapsed_ms
            run.error_message = "No bhavcopy available (404) — likely a market holiday"
            run.save()
            logger.info("ingestion.run.skipped", extra={"event": "ingestion.run.skipped", "run_id": run.id, "date": date_str})
            return {"run_id": run.id, "date": date_str, "status": "skipped"}

        zip_bytes, actual_hash, source_url = result
        if expected_sha256 and actual_hash != expected_sha256:
            raise ValueError("checksum mismatch")

        raw_rows = _extract_pd_csv(zip_bytes)
        rows_seen = rows_valid = rows_invalid = rows_inserted = rows_updated = 0
        errors = []

        with transaction.atomic():
            for raw in raw_rows:
                if str(raw.get("SERIES", "")).strip().upper() != "EQ":
                    continue
                rows_seen += 1
                try:
                    cleaned = DataValidator.parse_row(raw, trade_date=trade_date)
                    rows_valid += 1
                except Exception as exc:  # noqa: BLE001
                    rows_invalid += 1
                    errors.append({"row": rows_seen, "error": str(exc)})
                    incr("ingestion_rows_invalid")
                    continue

                _, created = DailyCandle.objects.update_or_create(
                    symbol=cleaned["symbol"],
                    date=cleaned["date"],
                    defaults={
                        "open": cleaned["open"],
                        "high": cleaned["high"],
                        "low": cleaned["low"],
                        "close": cleaned["close"],
                        "volume": cleaned["volume"],
                    },
                )
                if created:
                    rows_inserted += 1
                    incr("ingestion_rows_inserted")
                else:
                    rows_updated += 1
                    incr("ingestion_rows_updated")

        elapsed_ms = int((time.monotonic() - started) * 1000)
        run.status = IngestionRun.Status.SUCCESS
        run.source_file_name = source_url.rsplit("/", 1)[-1]
        run.source_file_hash = actual_hash
        run.rows_seen = rows_seen
        run.rows_valid = rows_valid
        run.rows_invalid = rows_invalid
        run.rows_inserted = rows_inserted
        run.rows_updated = rows_updated
        run.finished_at = timezone.now()
        run.elapsed_ms = elapsed_ms
        run.error_payload = {"row_errors": errors[:100], "source_url": source_url}
        run.save()

        logger.info("ingestion.run.completed", extra={"event": "ingestion.run.completed", "run_id": run.id, "status": run.status, "counts": {"seen": rows_seen, "valid": rows_valid, "invalid": rows_invalid, "inserted": rows_inserted, "updated": rows_updated}, "elapsed_ms": elapsed_ms})
        incr("ingestion_runs_succeeded")
        return {"run_id": run.id, "date": date_str, "status": "success"}
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - started) * 1000)
        run.status = IngestionRun.Status.FAILED
        run.finished_at = timezone.now()
        run.elapsed_ms = elapsed_ms
        run.error_message = str(exc)
        run.error_payload = {"exception": exc.__class__.__name__}
        run.save(update_fields=["status", "finished_at", "elapsed_ms", "error_message", "error_payload"])
        incr("ingestion_runs_failed")
        logger.exception("ingestion.run.failed", extra={"event": "ingestion.run.failed", "run_id": run.id, "date": date_str, "error": str(exc)})
        raise


@shared_task(bind=True)
def fetch_last_10_years(self, end_date_str: str | None = None):
    end_date = datetime.strptime(end_date_str, "%d%m%Y").date() if end_date_str else timezone.now().date()
    start_date = end_date - timedelta(days=3650)

    date_args = []
    cursor = start_date
    while cursor <= end_date:
        if cursor.weekday() < 5:
            date_args.append((cursor.strftime("%d%m%Y"),))
        cursor += timedelta(days=1)

    if not date_args:
        return {"scheduled": 0, "start_date": start_date.isoformat(), "end_date": end_date.isoformat()}

    # Use chunks to batch independent tasks (50 per group) on the ingestion queue
    download_bhavcopy.chunks(date_args, 50).apply_async(queue="ingestion")
    logger.info("ingestion.backfill.scheduled", extra={"event": "ingestion.backfill.scheduled", "scheduled": len(date_args), "start_date": start_date.isoformat(), "end_date": end_date.isoformat()})
    incr("ingestion_backfill_scheduled_days", len(date_args))
    return {"scheduled": len(date_args), "start_date": start_date.isoformat(), "end_date": end_date.isoformat()}


@shared_task
def get_last_10_years_fetch_status(limit: int = 3650):
    runs = IngestionRun.objects.filter(source="bhavcopy_daily").order_by("-source_date")[:limit]
    summary = {
        "total_runs": len(runs),
        "success": sum(1 for r in runs if r.status == IngestionRun.Status.SUCCESS),
        "failed": sum(1 for r in runs if r.status == IngestionRun.Status.FAILED),
        "skipped": sum(1 for r in runs if r.status == IngestionRun.Status.SKIPPED),
        "started": sum(1 for r in runs if r.status == IngestionRun.Status.STARTED),
    }
    by_date = [
        {
            "date": run.source_date.isoformat(),
            "status": run.status,
            "rows_seen": run.rows_seen,
            "rows_valid": run.rows_valid,
            "rows_inserted": run.rows_inserted,
            "rows_updated": run.rows_updated,
            "rows_invalid": run.rows_invalid,
            "elapsed_ms": run.elapsed_ms,
            "error_message": run.error_message,
        }
        for run in runs
    ]
    return {"summary": summary, "results": by_date}
