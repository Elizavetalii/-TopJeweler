from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cart.models import CartItem
from apps.catalog.models import Category, Product
from apps.orders.models import PromoCode
from apps.product_variants.models import ProductVariant

User = get_user_model()


class CartPromoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='promo', password='secret')
        self.client.force_login(self.user)
        category = Category.objects.create(name='Украшения')
        product = Product.objects.create(name='Колье', category=category)
        self.variant = ProductVariant.objects.create(product=product, price=Decimal('40000.00'), quantity=5)
        CartItem.objects.create(user=self.user, product_variant=self.variant, quantity=1, price=self.variant.price)
        self.promo = PromoCode.objects.create(
            code='VIP10',
            discount_percent=Decimal('10.00'),
            min_order_total=Decimal('30000.00'),
            is_active=True,
        )

    def test_apply_promo_returns_discounted_totals(self):
        url = reverse('cart_apply_promo')
        response = self.client.post(url, {'promo': 'vip10'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['promo']['code'], 'VIP10')
        self.assertTrue(data['promo']['is_applied'])
        self.assertEqual(data['totals']['discount'], '4000.00')
        self.assertEqual(data['totals']['total'], '36000.00')

    def test_promo_saved_when_total_below_minimum(self):
        item = CartItem.objects.get(user=self.user)
        item.price = Decimal('5000.00')
        item.save()
        url = reverse('cart_apply_promo')
        response = self.client.post(url, {'promo': 'VIP10'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data['promo']['code'], 'VIP10')
        self.assertFalse(data['promo']['is_applied'])
        self.assertTrue(data['promo']['recoverable'])
        self.assertIn('Минимальная сумма', data['promo']['message'])
        self.assertEqual(data['totals']['discount'], '0')
