from django.http import HttpResponse
import csv
from .models import Order, OrderItem

def export_orders_to_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'User ID', 'Created At', 'Total Amount', 'Status'])

    orders = Order.objects.all()
    for order in orders:
        writer.writerow([order.order_id, order.user_id, order.created_at, order.total_amount, order.status_id])

    return response

def export_order_items_to_csv(request, order_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="order_items_{order_id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order Item ID', 'Order ID', 'Product Variant ID', 'Quantity', 'Price'])

    order_items = OrderItem.objects.filter(order_id=order_id)
    for item in order_items:
        writer.writerow([item.order_item_id, item.order_id, item.product_variant_id, item.quantity, item.price])

    return response
