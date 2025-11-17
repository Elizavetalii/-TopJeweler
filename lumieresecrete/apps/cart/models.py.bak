from django.db import models

class CartItem(models.Model):
    order_item_id = models.AutoField(primary_key=True, db_column='OrderItemID')  # чтобы соответствовать SQL
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, db_column='UserID')
    product_variant = models.ForeignKey('product_variants.ProductVariant', on_delete=models.CASCADE, db_column='ProductVariantID')
    quantity = models.PositiveIntegerField(default=1, db_column='Quantity')
    price = models.DecimalField(max_digits=10, decimal_places=2, db_column='Price')

    class Meta:
        db_table = 'CartItems'

    def __str__(self):
        return f"{self.product_variant} in cart of {self.user}"


class Cart(models.Model):
    # SQL у тебя не полностью описывает Cart — я сделаю простой OneToOne модель:
    cart_id = models.AutoField(primary_key=True, db_column='CartID')
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, db_column='UserID')
    # ManyToMany через CartItem не совсем типично, но оставим поле для удобства (не хранится в SQL напрямую)
    items = models.ManyToManyField('cart.CartItem', blank=True, related_name='carts')

    class Meta:
        db_table = 'Cart'

    def __str__(self):
        return f"Cart of {self.user}"
