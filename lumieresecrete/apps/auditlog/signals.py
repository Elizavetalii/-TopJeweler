import json

from django.apps import apps
from django.db.models.signals import post_delete, post_save, pre_save
from django.forms.models import model_to_dict
from django.utils import timezone

from .models import AuditLog
from .utils import get_current_user, get_request_metadata

_PRE_SAVE_STATE = {}


def _is_project_model(model):
    module = model.__module__
    if not module.startswith("apps."):
        return False
    if model is AuditLog:
        return False
    app_label = getattr(model._meta, "app_label", "")
    if app_label == "accounts" and model.__name__ in {"AuditLog", "SessionLog", "Backups"}:
        return False
    return True


def _serialize_instance(instance):
    try:
        data = model_to_dict(instance)
    except Exception:
        data = {}
        for field in instance._meta.fields:
            data[field.name] = getattr(instance, field.name, None)
    for key, value in data.items():
        try:
            json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            data[key] = str(value)
    return data


def _legacy_fragment(data):
    if not data:
        return None
    try:
        payload = json.dumps(data, ensure_ascii=False)
    except Exception:
        payload = str(data)
    return payload[:255]


def _log_change(instance, action, old_data=None, new_data=None):
    user = get_current_user()
    meta = get_request_metadata()
    payload = new_data or _serialize_instance(instance)
    AuditLog.objects.create(
        event_type=AuditLog.EVENT_DB,
        action=action,
        app_label=instance._meta.app_label,
        model_name=instance.__class__.__name__,
        object_pk=str(getattr(instance, instance._meta.pk.attname, "")),
        user=user,
        path=meta.get("path"),
        method=meta.get("method"),
        ip_address=meta.get("ip"),
        changes=payload,
    )
    try:
        from apps.accounts.models import AuditLog as LegacyAuditLog
        LegacyAuditLog.objects.create(
            table_name=instance._meta.db_table[:255],
            operation=action[:255] if isinstance(action, str) else str(action)[:255],
            datetime=timezone.now(),
            old_value=_legacy_fragment(old_data),
            new_value=_legacy_fragment(payload),
            field=None,
            user=user if user and getattr(user, "is_authenticated", False) else None,
        )
    except Exception:
        pass


def _capture_pre_save(sender, instance, **kwargs):
    if sender is AuditLog:
        return
    pk = getattr(instance, instance._meta.pk.attname, None)
    if not pk:
        return
    try:
        baseline = sender.objects.get(pk=pk)
    except sender.DoesNotExist:
        return
    key = (sender, pk)
    _PRE_SAVE_STATE[key] = _serialize_instance(baseline)


def _handle_post_save(sender, instance, created, **kwargs):
    if sender is AuditLog:
        return
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    key = (sender, getattr(instance, instance._meta.pk.attname, None))
    old_data = _PRE_SAVE_STATE.pop(key, None)
    _log_change(instance, action, old_data=old_data, new_data=_serialize_instance(instance))


def _handle_post_delete(sender, instance, **kwargs):
    if sender is AuditLog:
        return
    payload = _serialize_instance(instance)
    _log_change(instance, AuditLog.ACTION_DELETE, old_data=payload, new_data=None)


def register_audit_signals():
    for model in apps.get_models():
        if not _is_project_model(model):
            continue
        pre_save.connect(_capture_pre_save, sender=model, weak=False)
        post_save.connect(_handle_post_save, sender=model, weak=False)
        post_delete.connect(_handle_post_delete, sender=model, weak=False)


register_audit_signals()
