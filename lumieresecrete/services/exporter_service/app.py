from django.core.management.base import BaseCommand
import csv
from apps.orders.models import Order

class Command(BaseCommand):
    help = 'Export order data to CSV'

    def handle(self, *args, **kwargs):
        with open('orders_export.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Order ID', 'User ID', 'Total Amount', 'Status', 'Product Variants'])

            orders = Order.objects.all()
            for order in orders:
                product_variants = order.orderitem_set.values_list('product_variant__name', flat=True)
                writer.writerow([order.id, order.user_id, order.total_amount, order.status.name, ', '.join(product_variants)])

        self.stdout.write(self.style.SUCCESS('Successfully exported order data to orders_export.csv'))
