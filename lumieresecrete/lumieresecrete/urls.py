from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='catalog_list', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('accounts/', include(('apps.accounts.urls', 'accounts'), namespace='accounts')),
    path('catalog/', include('apps.catalog.urls')),
    path('cart/', include('apps.cart.urls')),
    path('orders/', include(('apps.orders.urls', 'orders'), namespace='orders')),
    path('stores/', include('apps.stores.urls')),
    path('reports/', include('apps.reports.urls')),
    path('admin-tools/', include(('apps.admin_tools.urls', 'admin_tools'), namespace='admin_tools')),
]
