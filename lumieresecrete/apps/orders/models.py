from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

class Status(models.Model):
    status_id = models.AutoField(primary_key=True, db_column='StatusID')
    name_status = models.CharField(max_length=255, db_column='NameStatus')

    class Meta:
        db_table = 'Status'

    def __str__(self):
        return self.name_status


class PromoCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'PromoCodes'
        ordering = ['-id']
        constraints = [
            models.CheckConstraint(
                check=Q(discount_percent__isnull=False) | Q(discount_amount__isnull=False),
                name='promocode_has_discount'
            )
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def is_valid(self, amount: Decimal, when=None) -> bool:
        if not self.is_active:
            return False
        now = when or timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        if amount < (self.min_order_total or Decimal('0')):
            return False
        return True

    def discount_for_amount(self, amount: Decimal) -> Decimal:
        amount = amount or Decimal('0')
        if not self.is_valid(amount):
            return Decimal('0')
        if self.discount_percent:
            percent = (self.discount_percent or Decimal('0')) / Decimal('100')
            return (amount * percent).quantize(Decimal('0.01'))
        if self.discount_amount:
            return min(self.discount_amount, amount).quantize(Decimal('0.01'))
        return Decimal('0')

    def register_use(self):
        PromoCode.objects.filter(pk=self.pk).update(usage_count=F('usage_count') + 1)
        self.refresh_from_db(fields=['usage_count'])


class Order(models.Model):
    order_id = models.AutoField(primary_key=True, db_column='OrderID')
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, db_column='UserID')
    created_at = models.CharField(max_length=255, null=True, blank=True, db_column='CreatedAt')  # SQL использует varchar
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, db_column='StatusID')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='TotalAmount')
    store = models.ForeignKey('stores.Store', on_delete=models.SET_NULL, null=True, db_column='StoreID')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), db_column='DiscountAmount')
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True, db_column='PromoCodeID')

    class Meta:
        db_table = 'Orders'

    def __str__(self):
        return f"Order {self.order_id} by {self.user}"


class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True, db_column='OrderItemID')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, db_column='OrderID')
    product_variant = models.ForeignKey('product_variants.ProductVariant', on_delete=models.CASCADE, db_column='ProductVariantID')
    quantity = models.IntegerField(db_column='Quantity')
    price = models.DecimalField(max_digits=10, decimal_places=2, db_column='Price')

    class Meta:
        db_table = 'OrderItems'

    def __str__(self):
        return f"{self.quantity} of {self.product_variant} in Order {self.order.order_id}"

    def clean(self):
        errors = {}
        if self.quantity is None or self.quantity <= 0:
            errors['quantity'] = "Количество должно быть положительным."
        if self.price is None or self.price < 0:
            errors['price'] = "Цена должна быть неотрицательной."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True, db_column='PaymentID')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, db_column='OrderID')
    method = models.CharField(max_length=100, db_column='Method')
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='Amount')
    status = models.CharField(max_length=100, db_column='Status')

    class Meta:
        db_table = 'Payments'


class OrderShareToken(models.Model):
    token_id = models.AutoField(primary_key=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='share_tokens')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    channel = models.CharField(max_length=50, blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'OrderShareToken'
        indexes = [models.Index(fields=['token', 'expires_at'])]

    def __str__(self):
        return f"ShareToken(order={self.order_id}, token={self.token})"


class OrderStatusHistory(models.Model):
    history_id = models.AutoField(primary_key=True, db_column='HistoryID')
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        db_column='OrderID'
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='StatusID'
    )
    status_name = models.CharField(max_length=255, db_column='StatusName', blank=True)
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='ChangedByID'
    )
    changed_at = models.DateTimeField(auto_now_add=True, db_column='ChangedAt')

    class Meta:
        db_table = 'OrderStatusHistory'
        ordering = ['changed_at']

    def __str__(self):
        return f"{self.order_id}: {self.status_name} @ {self.changed_at}"


class OrderNotification(models.Model):
    notification_id = models.AutoField(primary_key=True, db_column='NotificationID')
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        db_column='UserID',
        related_name='order_notifications'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_column='OrderID',
        related_name='notifications'
    )
    old_status = models.CharField(max_length=255, blank=True, db_column='OldStatus')
    new_status = models.CharField(max_length=255, blank=True, db_column='NewStatus')
    is_read = models.BooleanField(default=False, db_column='IsRead')
    created_at = models.DateTimeField(auto_now_add=True, db_column='CreatedAt')

    class Meta:
        db_table = 'OrderNotifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Уведомление {self.order_id}: {self.old_status} -> {self.new_status}"
