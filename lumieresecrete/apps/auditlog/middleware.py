from django.utils.deprecation import MiddlewareMixin

from .models import AuditLog
from .utils import (
    clear_context,
    get_current_user,
    set_current_user,
    set_request_context,
)


class AuditLogMiddleware(MiddlewareMixin):
    SAFE_PREFIXES = ("/static/", "/media/")

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None
        set_current_user(user)
        ip = request.META.get("HTTP_X_FORWARDED_FOR")
        if ip:
            ip = ip.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        set_request_context(path=request.path, method=request.method, ip=ip)

    def process_response(self, request, response):
        try:
            if request.path.startswith(self.SAFE_PREFIXES):
                return response
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                user = get_current_user()
                AuditLog.objects.create(
                    user=user,
                    action=AuditLog.ACTION_REQUEST,
                    event_type=AuditLog.EVENT_REQUEST,
                    path=request.path,
                    method=request.method,
                    ip_address=getattr(request, "META", {}).get("REMOTE_ADDR"),
                    metadata={
                        "status_code": response.status_code,
                        "user_agent": request.META.get("HTTP_USER_AGENT"),
                    },
                )
            return response
        finally:
            clear_context()

    def process_exception(self, request, exception):
        clear_context()
