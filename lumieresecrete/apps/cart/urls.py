from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('clear/', views.cart_clear, name='cart_clear'),
    path('undo/', views.cart_undo, name='cart_undo'),
    path('promo/', views.cart_apply_promo, name='cart_apply_promo'),
    path('view/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
]
