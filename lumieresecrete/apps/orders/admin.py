from django.contrib import admin
from .models import Order, OrderItem, Status, Payment, PromoCode

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'created_at', 'status', 'total_amount')
    search_fields = ('user__email',)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_item_id', 'order', 'product_variant', 'quantity', 'price')

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('status_id', 'name_status')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'order', 'method', 'amount', 'status')
    search_fields = ('order__order_id', 'method', 'status')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'discount_amount', 'min_order_total', 'is_active', 'valid_from', 'valid_to', 'usage_count', 'usage_limit')
    list_filter = ('is_active',)
    search_fields = ('code', 'description')
    ordering = ('-id',)
