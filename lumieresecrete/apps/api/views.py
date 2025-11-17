from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer, ProductSerializer, OrderSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

# Заглушки (stub endpoints)
class UserRegistrationView(APIView):
    def post(self, request):
        return Response({"detail": "registration endpoint placeholder"}, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    def post(self, request):
        return Response({"detail": "login endpoint placeholder"}, status=status.HTTP_200_OK)

class ProductListView(APIView):
    def get(self, request):
        return Response([], status=status.HTTP_200_OK)

class OrderCreateView(APIView):
    def post(self, request):
        return Response({"detail": "order create placeholder"}, status=status.HTTP_201_CREATED)

class CartView(APIView):
    def get(self, request):
        return Response({"items": []}, status=status.HTTP_200_OK)
