from django.conf import settings
from django.db import models

class Category(models.Model):
    category_id = models.AutoField(primary_key=True, db_column='CategoryID')
    name = models.CharField(max_length=255, db_column='Name')

    class Meta:
        db_table = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    product_id = models.AutoField(primary_key=True, db_column='ProductID')
    name = models.CharField(max_length=255, db_column='Name')
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='CategoryID',
        related_name='products'
    )

    class Meta:
        db_table = 'Products'

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True, db_column='ImageID')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='images', db_column='ProductID')
    image_url = models.TextField(db_column='ImageURL')
    alt_text = models.CharField(max_length=255, blank=True, db_column='AltText')
    position = models.PositiveIntegerField(default=0, db_column='Position')

    class Meta:
        db_table = 'ProductImages'
        ordering = ['position', 'image_id']

    def __str__(self):
        return f"Image for {self.product.name}"


class Favorite(models.Model):
    favorite_id = models.AutoField(primary_key=True, db_column='FavoriteID')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, db_column='UserID', related_name='favorites')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, db_column='ProductID', related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True, db_column='CreatedAt')

    class Meta:
        db_table = 'Favorites'
        unique_together = (('user', 'product'),)

    def __str__(self):
        return f"{self.user} ♥ {self.product}"


class ProductReview(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='reviews')
    variant = models.ForeignKey('product_variants.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ProductReviews'
        ordering = ['-created_at']
        unique_together = (('product', 'user'),)

    def __str__(self):
        return f"Review {self.rating} for {self.product} by {self.user}"


class ReviewModerationLog(models.Model):
    log_id = models.AutoField(primary_key=True, db_column='LogID')
    review = models.OneToOneField(
        'catalog.ProductReview',
        on_delete=models.CASCADE,
        related_name='moderation_log',
        db_column='ReviewID'
    )
    status = models.CharField(max_length=32, db_column='Status', default='pending')
    notes = models.TextField(blank=True, db_column='Notes')
    created_at = models.DateTimeField(auto_now_add=True, db_column='CreatedAt')

    class Meta:
        db_table = 'ReviewModerationLog'
        managed = False

    def __str__(self):
        return f"Moderation log #{self.log_id} for review {self.review_id}"
