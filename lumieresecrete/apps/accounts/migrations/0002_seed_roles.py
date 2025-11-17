from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    User = apps.get_model('accounts', 'User')
    UserRole = apps.get_model('accounts', 'UserRole')

    roles = {}
    for name in ['Администратор', 'Менеджер', 'Клиент']:
        role, _ = Role.objects.get_or_create(role_name=name)
        roles[name] = role

    client_role = roles['Клиент']
    for user in User.objects.all():
        UserRole.objects.get_or_create(user=user, role=client_role)


def unseed_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    Role.objects.filter(role_name__in=['Администратор', 'Менеджер', 'Клиент']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
