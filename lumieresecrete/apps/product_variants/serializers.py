from rest_framework import serializers
from .models import ProductVariant

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'  # or specify the fields you want to include, e.g., ['id', 'product', 'color', 'size', 'price', 'quantity']