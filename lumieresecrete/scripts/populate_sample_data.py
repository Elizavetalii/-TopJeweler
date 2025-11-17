import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumieresecrete.settings.development')
django.setup()

def populate_sample_data():
    # Sample data for Users
    call_command('loaddata', 'users.json')

    # Sample data for Products
    call_command('loaddata', 'products.json')

    # Sample data for Orders
    call_command('loaddata', 'orders.json')

if __name__ == '__main__':
    populate_sample_data()