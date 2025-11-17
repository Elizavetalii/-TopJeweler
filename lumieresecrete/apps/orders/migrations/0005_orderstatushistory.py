from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0004_db_programming'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderStatusHistory',
            fields=[
                ('history_id', models.AutoField(db_column='HistoryID', primary_key=True, serialize=False)),
                ('status_name', models.CharField(blank=True, db_column='StatusName', max_length=255)),
                ('changed_at', models.DateTimeField(auto_now_add=True, db_column='ChangedAt')),
                ('changed_by', models.ForeignKey(blank=True, db_column='ChangedByID', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(db_column='OrderID', on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='orders.order')),
                ('status', models.ForeignKey(blank=True, db_column='StatusID', null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.status')),
            ],
            options={
                'db_table': 'OrderStatusHistory',
                'ordering': ['changed_at'],
            },
        ),
    ]

