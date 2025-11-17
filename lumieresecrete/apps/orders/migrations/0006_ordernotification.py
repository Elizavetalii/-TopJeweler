from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0005_orderstatushistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderNotification',
            fields=[
                ('notification_id', models.AutoField(db_column='NotificationID', primary_key=True, serialize=False)),
                ('old_status', models.CharField(blank=True, db_column='OldStatus', max_length=255)),
                ('new_status', models.CharField(blank=True, db_column='NewStatus', max_length=255)),
                ('is_read', models.BooleanField(db_column='IsRead', default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='CreatedAt')),
                ('order', models.ForeignKey(db_column='OrderID', on_delete=models.deletion.CASCADE, related_name='notifications', to='orders.order')),
                ('user', models.ForeignKey(db_column='UserID', on_delete=models.deletion.CASCADE, related_name='order_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'OrderNotifications',
                'ordering': ['-created_at'],
            },
        ),
    ]

