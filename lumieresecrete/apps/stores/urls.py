from django.urls import path
from . import views

urlpatterns = [
    path('', views.store_list, name='store-list'),
    path('<int:pk>/', views.store_detail, name='store-detail'),
]
