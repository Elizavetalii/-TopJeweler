from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_alter_productreview_is_public"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ReviewModerationLog",
                    fields=[
                        (
                            "review",
                            models.OneToOneField(
                                db_column="ReviewID",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="moderation_log",
                                to="catalog.productreview",
                            ),
                        ),
                        (
                            "log_id",
                            models.AutoField(
                                db_column="LogID", primary_key=True, serialize=False
                            ),
                        ),
                        (
                            "status",
                            models.CharField(
                                db_column="Status", default="pending", max_length=32
                            ),
                        ),
                        ("notes", models.TextField(blank=True, db_column="Notes")),
                        (
                            "created_at",
                            models.DateTimeField(auto_now_add=True, db_column="CreatedAt"),
                        ),
                    ],
                    options={
                        "db_table": "ReviewModerationLog",
                        "managed": False,
                    },
                )
            ],
            database_operations=[],
        )
    ]
