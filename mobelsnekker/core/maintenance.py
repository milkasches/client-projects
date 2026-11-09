"""Housekeeping: resend failed notifications, daily backup, GDPR clean-up.

Runs automatically at most once a day after a form submission or an admin
visit (no cron needed), and can be run by hand / by a scheduled task:

    python manage.py maintenance
"""
import logging
import shutil
import sqlite3
import time
import zipfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

log = logging.getLogger(__name__)

RETRY_MAX_ATTEMPTS = 6


def retry_notifications(limit=20):
    """Re-send admin notifications that failed earlier."""
    from .emails import notify_consultation, notify_order
    from .models import ConsultationRequest, Order

    sent = failed = 0
    cutoff = timezone.now() - timedelta(minutes=2)  # don't race the first attempt
    for model, fn in ((Order, notify_order), (ConsultationRequest, notify_consultation)):
        qs = model.objects.filter(notified_at__isnull=True, notify_attempts__lt=RETRY_MAX_ATTEMPTS,
                                  created_at__lt=cutoff).order_by("created_at")[:limit]
        for obj in qs:
            if fn(obj, with_client=False):
                sent += 1
            else:
                failed += 1
    return sent, failed


def backup(keep=None):
    """Consistent copy of the SQLite database + zip of uploaded files."""
    keep = keep or settings.BACKUP_KEEP
    folder = Path(settings.BACKUP_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    target = folder / f"backup-{stamp}"
    target.mkdir()

    if connection.vendor == "sqlite" and not connection.in_atomic_block:
        connection.ensure_connection()
        dst = sqlite3.connect(str(target / "db.sqlite3"))
        with dst:
            connection.connection.backup(dst)  # online backup: safe while the site is writing
        dst.close()

    media = Path(settings.MEDIA_ROOT)
    if media.exists():
        with zipfile.ZipFile(target / "media.zip", "w", zipfile.ZIP_STORED) as z:  # photos are already compressed
            for f in media.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(media))

    backups = sorted(p for p in folder.glob("backup-*") if p.is_dir())
    for old in backups[:-keep]:
        shutil.rmtree(old, ignore_errors=True)
    log.info("Backup written to %s", target)
    return target


def purge_old(days=None):
    """Delete closed requests older than RETENTION_DAYS (GDPR: keep data only as long as needed)."""
    from .models import ConsultationRequest, Order, Status

    days = days or settings.RETENTION_DAYS
    cutoff = timezone.now() - timedelta(days=days)
    closed = [Status.DONE, Status.LOST]
    n_orders = 0
    for o in Order.objects.filter(status__in=closed, created_at__lt=cutoff):
        o.delete()  # attachment files are removed by the post_delete signal
        n_orders += 1
    n_consult, _ = ConsultationRequest.objects.filter(
        status__in=closed + ["contacted"], created_at__lt=cutoff).delete()
    return n_orders, n_consult


def run_all():
    result = {"retry": retry_notifications(), "purged": purge_old()}
    result["backup"] = str(backup())
    return result


def maybe_daily():
    """Cheap check; does the real work at most once per BACKUP_INTERVAL_HOURS."""
    if not settings.AUTO_MAINTENANCE:
        return
    stamp = Path(settings.BACKUP_DIR) / ".last-maintenance"
    try:
        last = stamp.stat().st_mtime
    except FileNotFoundError:
        last = 0
    if time.time() - last < settings.BACKUP_INTERVAL_HOURS * 3600:
        return
    if not cache.add("iw-maintenance-lock", 1, 600):  # another worker is already on it
        return
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()
        run_all()
    finally:
        cache.delete("iw-maintenance-lock")
