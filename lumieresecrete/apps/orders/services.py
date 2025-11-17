from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction

from .models import Order, OrderItem
from apps.product_variants.models import ProductVariant

class OrderService:
    @staticmethod
    def create_order(user, cart_items):
        if not cart_items:
            raise ValidationError("Корзина пуста — нечего оформлять.")
        with transaction.atomic():
            order = Order.objects.create(user=user, total_amount=Decimal('0.00'))
            for raw_item in cart_items:
                variant_id = raw_item.get('product_variant_id')
                quantity = int(raw_item.get('quantity', 0) or 0)
                if quantity <= 0:
                    raise ValidationError("Количество товара должно быть положительным.")
                try:
                    variant = ProductVariant.objects.get(pk=variant_id)
                except ProductVariant.DoesNotExist as exc:
                    raise ValidationError(f"Вариант товара с ID {variant_id} не найден.") from exc

                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "CALL sp_adjust_variant_stock(%s, %s)",
                            [variant.pk, -quantity]
                        )
                except DatabaseError as db_exc:
                    raise ValidationError(
                        f"Не удалось зарезервировать остаток для {variant}: {db_exc}"
                    ) from db_exc

                OrderItem.objects.create(
                    order=order,
                    product_variant=variant,
                    quantity=quantity,
                    price=variant.price
                )

            with connection.cursor() as cursor:
                cursor.execute("CALL sp_recalculate_order_total(%s)", [order.order_id])
            order.refresh_from_db(fields=["total_amount"])
            return order

    @staticmethod
    def update_order_status(order_id, status_id):
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            order.status_id = status_id
            order.save(update_fields=["status"])
            return order

    @staticmethod
    def get_order_details(order_id):
        order = Order.objects.prefetch_related('orderitem_set').get(id=order_id)
        return {
            'order_id': order.id,
            'total_amount': order.total_amount,
            'items': [
                {
                    'product_variant_id': item.product_variant.id,
                    'quantity': item.quantity,
                    'price': item.price
                } for item in order.orderitem_set.all()
            ]
        }
