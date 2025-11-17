from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # API endpoints (legacy)
    path('api/orders/', views.OrderListView.as_view(), name='order-list'),
    path('api/orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail-json'),
    path('api/orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('api/orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order-update'),
    path('api/orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order-delete'),

    # User-facing pages
    path('history/', views.order_history, name='order_history'),
    path('search/', views.order_search, name='order_search'),
    path('<int:order_id>/', views.order_detail_page, name='order_detail'),
    path('<int:order_id>/receipt/', views.order_receipt_pdf, name='order_receipt'),
    path('<int:order_id>/public/<slug:token>/receipt/', views.order_receipt_public, name='order_receipt_public'),
    path('<int:order_id>/share/', views.order_share, name='order_share'),
    path('<int:order_id>/repeat/', views.order_repeat, name='order_repeat'),
    path('<int:order_id>/cancel/', views.order_cancel, name='order_cancel'),
]
