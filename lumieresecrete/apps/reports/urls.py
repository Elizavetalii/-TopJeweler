from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('sales/', views.sales_report, name='sales-report'),
    path('products/', views.product_report, name='product-report'),
    path('stores/', views.store_report, name='store-report'),
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/stats/', views.manager_stats, name='manager_stats'),
    path('manager/export/', views.manager_export, name='manager_export'),
    path('manager/reviews/', views.manager_reviews, name='manager_reviews'),
    path('manager/reviews/<int:pk>/', views.manager_review_action, name='manager_review_action'),
]
