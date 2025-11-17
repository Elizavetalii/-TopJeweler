from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.auditlog.utils import get_current_user

from .models import Order, OrderNotification, OrderStatusHistory

_PREVIOUS_STATUS = {}


@receiver(pre_save, sender=Order)
def cache_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    status_obj = getattr(previous, 'status', None)
    _PREVIOUS_STATUS[instance.pk] = (
        getattr(status_obj, 'status_id', None),
        getattr(status_obj, 'name_status', '') or ''
    )


@receiver(post_save, sender=Order)
def track_status_history(sender, instance, created, **kwargs):
    previous_status_id, previous_status_name = _PREVIOUS_STATUS.pop(instance.pk, (None, ""))
    current_status_id = getattr(instance.status, 'status_id', None)
    should_log = created or (current_status_id != previous_status_id)
    if not should_log:
        return
    user = get_current_user()
    if user and not getattr(user, 'is_authenticated', False):
        user = None
    status_name = getattr(instance.status, 'name_status', None) or ("Создан" if created else "")
    OrderStatusHistory.objects.create(
        order=instance,
        status=instance.status,
        status_name=status_name,
        changed_by=user,
    )
    if instance.user:
        OrderNotification.objects.create(
            user=instance.user,
            order=instance,
            old_status=previous_status_name or "—",
            new_status=status_name or "",
        )
