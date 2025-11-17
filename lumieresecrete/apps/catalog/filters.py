from django_filters import rest_framework as filters
from .models import Product, Category, Store

class ProductFilter(filters.FilterSet):
    category = filters.ModelChoiceFilter(queryset=Category.objects.all())
    store = filters.ModelChoiceFilter(queryset=Store.objects.all())
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Product
        fields = ['category', 'store', 'min_price', 'max_price', 'name']