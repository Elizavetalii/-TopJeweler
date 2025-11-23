from .models import UserSettings, UserRole


def user_preferences(request):
    style = 'heart'
    theme = 'light'
    page_size = None
    is_manager = False
    if request.user.is_authenticated:
        # Cache user settings on the user instance to avoid repeated DB hits per request
        settings_obj = getattr(request.user, "_cached_usersettings", None)
        if settings_obj is None:
            try:
                settings_obj = request.user.usersettings
            except UserSettings.DoesNotExist:
                settings_obj = None
            setattr(request.user, "_cached_usersettings", settings_obj)
        if settings_obj:
            style = settings_obj.favorite_icon or style
            theme = settings_obj.theme or theme
            page_size = settings_obj.page_size
        # Use the cached property from User model (it memoizes per request)
        try:
            is_manager = bool(getattr(request.user, "is_manager", False))
        except Exception:
            is_manager = False
    return {
        "favorite_icon_style": style,
        "theme_preference": theme,
        "page_size_preference": page_size,
        "is_manager": is_manager,
        "is_privileged": is_manager or getattr(request.user, 'is_staff', False),
    }
