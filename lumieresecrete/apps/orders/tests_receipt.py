from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem, Status
from apps.product_variants.models import ProductVariant

User = get_user_model()


class OrderReceiptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret', first_name='Alice', last_name='Wonder')
        self.category = Category.objects.create(name='Категория')
        self.product = Product.objects.create(name='Колье тест', category=self.category)
        self.variant = ProductVariant.objects.create(product=self.product, price=1990, quantity=2)
        self.status = Status.objects.create(name_status='Создан')
        self.order = Order.objects.create(user=self.user, status=self.status, total_amount=1990, store=None, created_at='2025-01-01 10:00')
        OrderItem.objects.create(order=self.order, product_variant=self.variant, quantity=1, price=1990)
        self.client = Client()
        self.client.login(username='alice', password='secret')
        self.weasy_patch = mock.patch('apps.orders.views.HTML')
        html_mock = self.weasy_patch.start()
        self.addCleanup(self.weasy_patch.stop)
        html_mock.return_value.write_pdf.return_value = b'%PDF-FAKE'

    def test_receipt_pdf_response(self):
        url = reverse('orders:order_receipt', args=[self.order.order_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
