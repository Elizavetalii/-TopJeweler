import io
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.auditlog.utils import log_user_action
from apps.accounts.models import Backups


def backup_database(user=None):
    backup_dir = Path(settings.BASE_DIR).parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = timezone.now().strftime("backup-%Y%m%d-%H%M%S.json")
    destination = backup_dir / filename
    with destination.open("w", encoding="utf-8") as handle:
        call_command(
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            "--indent",
            "2",
            stdout=handle,
        )
    Backups.objects.create(
        created_at=timezone.now().isoformat(),
        type="manual-backup",
        file_path=str(destination),
        status="success",
        user=user,
    )
    if user:
        log_user_action(user, "dumpdata", {"file": str(destination)})
    return str(destination)


def restore_database(backup_file, user=None):
    call_command("loaddata", backup_file)
    Backups.objects.create(
        created_at=timezone.now().isoformat(),
        type="restore",
        file_path=str(backup_file),
        status="restored",
        user=user,
    )


def log_action(user, action, metadata=None):
    log_user_action(user, action, metadata=metadata or {})
