from django.core.exceptions import ValidationError
from django.db import models

class Colors(models.Model):
    gemstone_id = models.AutoField(primary_key=True, db_column='GemstoneID')
    name_color = models.CharField(max_length=255, db_column='NameColor')
    color_code = models.CharField(max_length=100, db_column='ColorCode', blank=True, null=True)

    class Meta:
        db_table = 'Colors'
        verbose_name = 'Color'
        verbose_name_plural = 'Colors'

    def __str__(self):
        return self.name_color


class Sizes(models.Model):
    size_id = models.AutoField(primary_key=True, db_column='SizeID')
    size = models.CharField(max_length=100, db_column='Size')

    class Meta:
        db_table = 'Sizes'
        verbose_name = 'Size'
        verbose_name_plural = 'Sizes'

    def __str__(self):
        return self.size


class ProductVariant(models.Model):
    product_variant_id = models.AutoField(primary_key=True, db_column='ProductVariantID')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, db_column='ProductID', related_name='variants')
    color = models.ForeignKey('product_variants.Colors', on_delete=models.SET_NULL, null=True, db_column='ColorID', related_name='variants')
    size = models.ForeignKey('product_variants.Sizes', on_delete=models.SET_NULL, null=True, db_column='SizeID', related_name='variants')
    structure = models.CharField(max_length=100, null=True, blank=True, db_column='Structure')
    price = models.DecimalField(max_digits=10, decimal_places=2, db_column='Price')
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, db_column='PreviousPrice', null=True, blank=True)
    description = models.TextField(blank=True, null=True, db_column='Description')
    quantity = models.IntegerField(null=True, db_column='Quantity')
    store = models.ForeignKey('stores.Store', on_delete=models.SET_NULL, null=True, db_column='StoreID', related_name='product_variants')

    class Meta:
        db_table = 'ProductVariant'
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        return f"{self.product.name if self.product else 'No product'} ({self.color or 'No color'}, {self.size or 'No size'})"

    def _prefetched_images(self):
        cache = getattr(self, '_prefetched_objects_cache', {})
        images = cache.get('images')
        if images is None:
            images = self.images.all()
        return list(images)

    def get_product_gallery(self):
        product = getattr(self, 'product', None)
        if not product or not hasattr(product, 'images'):
            return []
        gallery = []
        for legacy in product.images.all():
            url = getattr(legacy, 'image_url', None)
            if not url:
                continue
            gallery.append({
                "id": getattr(legacy, 'image_id', None),
                "url": url,
                "alt": legacy.alt_text or getattr(product, 'name', ''),
                "is_primary": False,
            })
        return gallery

    def get_image_payload(self, fallback=True):
        payload = []
        for image in self._prefetched_images():
            url = image.url
            if not url:
                continue
            payload.append({
                "id": image.pk,
                "url": url,
                "alt": image.alt or str(self),
                "is_primary": image.is_primary,
            })
        if not payload and fallback:
            payload = self.get_product_gallery()
        return payload

    def get_primary_image_url(self, fallback=True):
        payload = self.get_image_payload(fallback=fallback)
        for item in payload:
            if item.get("is_primary") and item.get("url"):
                return item["url"]
        return payload[0]["url"] if payload else None

    def clean(self):
        errors = {}
        if self.price is None or self.price < 0:
            errors['price'] = "Цена варианта не может быть отрицательной."
        if self.previous_price is not None and self.previous_price < 0:
            errors['previous_price'] = "Предыдущая цена не может быть отрицательной."
        if self.quantity is not None and self.quantity < 0:
            errors['quantity'] = "Количество на складе не может быть отрицательным."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductVariantImage(models.Model):
    variant = models.ForeignKey(
        'product_variants.ProductVariant',
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='product_variants/%Y/%m/%d/', blank=True, null=True)
    source_url = models.URLField(blank=True)
    alt = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Variant Image'
        verbose_name_plural = 'Variant Images'

    def __str__(self):
        return f"Image for {self.variant} #{self.pk}"

    @property
    def url(self):
        if self.image:
            try:
                return self.image.url
            except ValueError:
                return ''
        return self.source_url
