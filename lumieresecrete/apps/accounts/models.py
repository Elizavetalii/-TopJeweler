from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    created_at = models.DateTimeField(auto_now_add=True, db_column='CreatedAt')
    class Meta:
        db_table = 'Users'

    def __str__(self):
        return self.email or self.username

    @property
    def is_manager(self):
        cached = getattr(self, '_cached_is_manager', None)
        if cached is not None:
            return cached
        role_match = self.userrole_set.filter(role__role_name__iexact='менеджер').exists()
        result = role_match
        self._cached_is_manager = result
        return result


class Role(models.Model):
    role_id = models.AutoField(primary_key=True, db_column='RoleID')
    role_name = models.CharField(max_length=255, db_column='RoleName')

    class Meta:
        db_table = 'Roles'

    def __str__(self):
        return self.role_name


class UserRole(models.Model):
    user_role_id = models.AutoField(primary_key=True, db_column='UserRoleID')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='RoleID')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, db_column='UserID')

    class Meta:
        db_table = 'UserRole'
        unique_together = (('role', 'user'),)

    def __str__(self):
        return f"{self.user.email} - {self.role.role_name}"


class UserSettings(models.Model):
    user_setting_id = models.AutoField(primary_key=True, db_column='UserSettingID')
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, db_column='UserID')
    theme = models.CharField(max_length=10, choices=[('light','Light'),('dark','Dark')], default='light', db_column='Theme')
    date_format = models.CharField(max_length=20, null=True, blank=True, db_column='DateFormat')
    page_size = models.IntegerField(default=10, db_column='PageSize')
    saved_filters = models.JSONField(default=dict, db_column='SavedFilters')
    favorite_icon = models.CharField(
        max_length=10,
        choices=[('heart', 'Heart'), ('star', 'Star')],
        default='heart',
        db_column='FavoriteIcon'
    )

    class Meta:
        db_table = 'UserSettings'

    def __str__(self):
        return f"Settings for {self.user.email}"

class SessionLog(models.Model):
    session_log_id = models.AutoField(primary_key=True, db_column='SessionLogID')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, db_column='UserID')
    login_time = models.DateTimeField(db_column='LoginTime', null=True)
    logout_time = models.DateTimeField(db_column='LogoutTime', null=True)

    class Meta:
        db_table = 'SessionLog'


class AuditLog(models.Model):
    audit_log_id = models.AutoField(primary_key=True, db_column='AuditLogID')
    table_name = models.CharField(max_length=255, db_column='TableName', null=True)
    operation = models.CharField(max_length=255, db_column='Operation', null=True)
    datetime = models.DateTimeField(db_column='Datetime', null=True)
    old_value = models.CharField(max_length=255, db_column='OldValue', null=True)
    new_value = models.CharField(max_length=255, db_column='NewValue', null=True)
    field = models.CharField(max_length=255, db_column='Field', null=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, db_column='UserID')

    class Meta:
        db_table = 'AuditLog'


class Backups(models.Model):
    backup_id = models.AutoField(primary_key=True, db_column='BackupID')
    created_at = models.CharField(max_length=255, db_column='CreatedAt', null=True)
    type = models.CharField(max_length=255, db_column='Type', null=True)
    file_path = models.TextField(db_column='FilePath', null=True)
    status = models.CharField(max_length=100, db_column='Status', null=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, db_column='UserID')
    class Meta:
        db_table = 'Backups'
