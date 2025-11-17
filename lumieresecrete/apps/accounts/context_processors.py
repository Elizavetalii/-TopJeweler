from .models import UserSettings, UserRole


def user_preferences(request):
    style = 'heart'
    theme = 'light'
    page_size = None
    is_manager = False
    if request.user.is_authenticated:
        try:
            settings_obj = request.user.usersettings
        except UserSettings.DoesNotExist:
            settings_obj = None
        if settings_obj:
            style = settings_obj.favorite_icon or style
            theme = settings_obj.theme or theme
            page_size = settings_obj.page_size
        is_manager = UserRole.objects.filter(
            user=request.user,
            role__role_name__iexact='менеджер'
        ).exists()
    return {
        "favorite_icon_style": style,
        "theme_preference": theme,
        "page_size_preference": page_size,
        "is_manager": is_manager,
        "is_privileged": is_manager or getattr(request.user, 'is_staff', False),
    }
