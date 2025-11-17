from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    EVENT_REQUEST = "request"
    EVENT_DB = "db"
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_REQUEST = "request"

    EVENT_CHOICES = (
        (EVENT_REQUEST, "Request"),
        (EVENT_DB, "Database"),
    )

    action = models.CharField(max_length=32)
    event_type = models.CharField(
        max_length=16, choices=EVENT_CHOICES, default=EVENT_DB
    )
    app_label = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_pk = models.CharField(max_length=64, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=16, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "AuditLogs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["app_label", "model_name"]),
        ]

    def __str__(self):
        subject = self.model_name or self.event_type
        return f"[{self.event_type}] {self.action} {subject}"
