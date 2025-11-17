from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_seed_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='favorite_icon',
            field=models.CharField(choices=[('heart', 'Heart'), ('star', 'Star')], db_column='FavoriteIcon', default='heart', max_length=10),
        ),
    ]
