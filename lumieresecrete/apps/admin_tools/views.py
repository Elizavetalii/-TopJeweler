import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .forms import BackupForm, RestoreForm
from .utils import backup_database, log_action, restore_database


@staff_member_required
def maintenance_view(request):
    backup_form = BackupForm(request.POST or None, prefix="backup")
    restore_form = RestoreForm(request.POST or None, request.FILES or None, prefix="restore")

    if request.method == "POST":
        if "backup" in request.POST and backup_form.is_valid():
            backup_path = backup_database(request.user)
            log_action(request.user, "create_backup", {"path": backup_path})
            messages.success(request, "Резервная копия успешно создана.")
            return FileResponse(open(backup_path, "rb"), as_attachment=True, filename=Path(backup_path).name)

        if "restore" in request.POST and restore_form.is_valid():
            uploaded: UploadedFile = restore_form.cleaned_data["backup_file"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                for chunk in uploaded.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                restore_database(tmp_path, user=request.user)
            except Exception as exc:
                messages.error(request, f"Не удалось восстановить данные: {exc}")
            else:
                log_action(request.user, "restore_backup", {"source": uploaded.name})
                messages.success(request, "Данные успешно восстановлены из резервной копии.")
            finally:
                Path(tmp_path).unlink(missing_ok=True)
            return HttpResponseRedirect(reverse("admin_tools:maintenance"))

    context = {
        "backup_form": backup_form,
        "restore_form": restore_form,
    }
    return render(request, "admin_tools/maintenance.html", context)
