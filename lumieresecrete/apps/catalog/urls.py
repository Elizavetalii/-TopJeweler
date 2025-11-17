from django.urls import path
from . import views

urlpatterns = [
    path('', views.catalog_list, name='catalog_list'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('favorites/clear/', views.favorite_clear, name='favorite_clear'),
    path('favorites/add-all/', views.favorites_add_all_to_cart, name='favorites_add_all_to_cart'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:category_id>/', views.category_detail, name='category_detail'),
]
