from django.db import models

class Address(models.Model):
    address_id = models.AutoField(primary_key=True, db_column='AddressID')
    city = models.CharField(max_length=255, db_column='City', null=True, blank=True)
    street = models.CharField(max_length=255, db_column='Street', null=True, blank=True)

    class Meta:
        db_table = 'Address'

    def __str__(self):
        return f"{self.street}, {self.city}"


class Store(models.Model):
    store_id = models.AutoField(primary_key=True, db_column='StoreID')
    name = models.CharField(max_length=255, db_column='Name')
    address = models.ForeignKey('stores.Address', on_delete=models.SET_NULL, null=True, blank=True, db_column='AddressID')
    business_hours = models.CharField(max_length=255, db_column='BusinessHours', null=True, blank=True)
    photo = models.TextField(blank=True, null=True, db_column='Photo')

    class Meta:
        db_table = 'Stores'

    def __str__(self):
        return self.name
