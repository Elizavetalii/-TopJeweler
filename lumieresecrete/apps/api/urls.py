from django.urls import path
from .views import UserRegistrationView, UserLoginView, ProductListView, OrderCreateView, CartView

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='user-register'),
    path('auth/login/', UserLoginView.as_view(), name='user-login'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('orders/create/', OrderCreateView.as_view(), name='order-create'),
    path('cart/', CartView.as_view(), name='cart-view'),
]
