from django.contrib import admin
from .models import Store, Address

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('store_id', 'name', 'business_hours')
    search_fields = ('name',)
    list_filter = ('business_hours',)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('address_id', 'street', 'city')
    search_fields = ('street', 'city')
