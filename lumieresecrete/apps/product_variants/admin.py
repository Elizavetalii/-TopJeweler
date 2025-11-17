from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import ProductVariant, Colors, Sizes, ProductVariantImage


class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 0
    fields = ('preview', 'image', 'source_url', 'alt', 'order', 'is_primary')
    readonly_fields = ('preview',)
    classes = ['collapse']

    def preview(self, obj):
        url = getattr(obj, 'url', None)
        if obj.pk and url:
            return mark_safe(f'<img src="{url}" style="height:60px;border-radius:6px;" />')
        return '—'

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product_variant_id', 'product', 'color', 'size', 'price', 'quantity')
    search_fields = ('product__name', 'color__name_color', 'size__size')
    list_filter = ('color', 'size', 'store')
    ordering = ('product', 'price')
    inlines = [ProductVariantImageInline]


@admin.register(Colors)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('gemstone_id', 'name_color', 'color_code')
    search_fields = ('name_color', 'color_code')


@admin.register(Sizes)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('size_id', 'size')
    search_fields = ('size',)
