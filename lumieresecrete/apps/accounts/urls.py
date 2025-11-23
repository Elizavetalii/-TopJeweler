from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    notifications_mark_read,
    update_theme,
    PasswordResetViewSafe,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('password-reset/', PasswordResetViewSafe.as_view(), name='password_reset'),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
    path(
        'notifications/read/',
        notifications_mark_read,
        name='notifications_mark_read',
    ),
    path('theme/', update_theme, name='update_theme'),
]
