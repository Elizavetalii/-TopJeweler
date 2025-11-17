from threading import local

from django.utils import timezone

from .models import AuditLog

_state = local()


def set_current_user(user):
    _state.user = user


def get_current_user():
    return getattr(_state, "user", None)


def set_request_context(path=None, method=None, ip=None):
    _state.path = path
    _state.method = method
    _state.ip = ip


def clear_context():
    for attr in ("user", "path", "method", "ip"):
        if hasattr(_state, attr):
            delattr(_state, attr)


def get_request_metadata():
    return {
        "path": getattr(_state, "path", ""),
        "method": getattr(_state, "method", ""),
        "ip": getattr(_state, "ip", None),
    }


def log_user_action(user, action, metadata=None, path=None, method=None, ip=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        event_type=AuditLog.EVENT_REQUEST,
        path=path or getattr(_state, "path", ""),
        method=method or getattr(_state, "method", ""),
        ip_address=ip or getattr(_state, "ip", None),
        metadata=metadata or {},
        created_at=timezone.now(),
    )
