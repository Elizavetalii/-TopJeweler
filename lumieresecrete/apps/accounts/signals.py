from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import SessionLog


@receiver(user_logged_in)
def handle_user_login(sender, user, request, **kwargs):
    log = SessionLog.objects.create(
        user=user,
        login_time=timezone.now(),
        logout_time=None,
    )
    if request is not None:
        request.session['session_log_id'] = log.pk


@receiver(user_logged_out)
def handle_user_logout(sender, user, request, **kwargs):
    log_id = None
    if request is not None:
        log_id = request.session.pop('session_log_id', None)
    if log_id:
        SessionLog.objects.filter(pk=log_id).update(logout_time=timezone.now())
    elif user and user.is_authenticated:
        SessionLog.objects.create(
            user=user,
            login_time=None,
            logout_time=timezone.now(),
        )
