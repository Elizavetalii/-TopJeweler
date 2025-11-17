from django.contrib import admin
from .models import (
    User,
    UserSettings,
    Role,
    UserRole,
    SessionLog,
    AuditLog,
    Backups,
)

admin.site.site_header = "Lumiere Secrète — администрирование"
admin.site.site_title = "Lumiere Secrète Admin"
admin.site.index_title = "Управление витриной и заказами"

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'created_at', 'last_login')
    search_fields = ('first_name', 'last_name', 'email')

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'date_format', 'page_size')
    search_fields = ('user__email',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_id', 'role_name')
    search_fields = ('role_name',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user_role_id', 'user', 'role')
    search_fields = ('user__email', 'role__role_name')


@admin.register(SessionLog)
class SessionLogAdmin(admin.ModelAdmin):
    list_display = ('session_log_id', 'user', 'login_time', 'logout_time')
    search_fields = ('user__email',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('audit_log_id', 'table_name', 'operation', 'datetime', 'user')
    search_fields = ('table_name', 'operation', 'user__email')


@admin.register(Backups)
class BackupsAdmin(admin.ModelAdmin):
    list_display = ('backup_id', 'created_at', 'type', 'status', 'user')
    search_fields = ('type', 'status', 'user__email')
