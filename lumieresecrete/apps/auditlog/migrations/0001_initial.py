from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("action", models.CharField(max_length=32)),
                (
                    "event_type",
                    models.CharField(
                        choices=[("request", "Request"), ("db", "Database")],
                        default="db",
                        max_length=16,
                    ),
                ),
                ("app_label", models.CharField(blank=True, max_length=100)),
                ("model_name", models.CharField(blank=True, max_length=100)),
                ("object_pk", models.CharField(blank=True, max_length=64)),
                ("path", models.CharField(blank=True, max_length=255)),
                ("method", models.CharField(blank=True, max_length=16)),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("changes", models.JSONField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "AuditLogs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(
                fields=["event_type", "created_at"], name="audit_event_created_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(
                fields=["app_label", "model_name"], name="audit_model_idx"
            ),
        ),
    ]

