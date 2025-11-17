from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class ProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)

class OrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=False)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
