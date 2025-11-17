from django.test import TestCase
from apps.catalog.models import Product, Category

class CatalogTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.category, self.category)

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Test Category')

    def test_product_str(self):
        self.assertEqual(str(self.product), 'Test Product')