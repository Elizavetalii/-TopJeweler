import json
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem, OrderShareToken, Status
from apps.product_variants.models import ProductVariant

User = get_user_model()


class OrderShareTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='secret')
        category = Category.objects.create(name='Ring')
        product = Product.objects.create(name='Кольцо', category=category)
        variant = ProductVariant.objects.create(product=product, price=1000, quantity=3)
        status = Status.objects.create(name_status='Создан')
        self.order = Order.objects.create(user=self.user, status=status, total_amount=1000, created_at='2025-01-01 12:00')
        OrderItem.objects.create(order=self.order, product_variant=variant, quantity=1, price=1000)
        self.client = Client()
        self.client.login(username='bob', password='secret')

    def test_share_creates_token(self):
        url = reverse('orders:order_share', args=[self.order.order_id])
        response = self.client.post(url, data=json.dumps({'channel': 'link'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('share_url', data)
        token = OrderShareToken.objects.filter(order=self.order).first()
        self.assertIsNotNone(token)
        self.assertTrue(token.expires_at > timezone.now())
