from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.orders.models import Order
from apps.cart.models import CartItem
from apps.product_variants.models import ProductVariant
from apps.stores.models import Store

class EndToEndTestCase(APITestCase):

    def setUp(self):
        self.store = Store.objects.create(name="Test Store")
        self.user = User.objects.create_user(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="testpassword"
        )
        self.product_variant = ProductVariant.objects.create(
            product_id=1,  # Assuming a product with ID 1 exists
            store=self.store,
            price=100.00,
            quantity=10
        )

    def test_user_registration_and_order_creation(self):
        # User registration
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password': 'newpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User login
        response = self.client.post(reverse('accounts:login'), {
            'email': 'newuser@example.com',
            'password': 'newpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Add item to cart
        response = self.client.post(reverse('cart:add_to_cart'), {
            'product_variant_id': self.product_variant.id,
            'quantity': 2
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create order
        response = self.client.post(reverse('orders:create_order'), {
            'store_id': self.store.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)

    def test_cart_management(self):
        # Add item to cart
        response = self.client.post(reverse('cart:add_to_cart'), {
            'product_variant_id': self.product_variant.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # View cart
        response = self.client.get(reverse('cart:view_cart'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.product_variant.id, [item['product_variant_id'] for item in response.data['items']])

    def test_order_status_monitoring(self):
        # Create an order
        order_response = self.client.post(reverse('orders:create_order'), {
            'store_id': self.store.id
        })
        order_id = order_response.data['id']

        # Check order status
        response = self.client.get(reverse('orders:order_detail', args=[order_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Pending')  # Assuming default status is 'Pending'