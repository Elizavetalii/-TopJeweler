from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User
from django.contrib.auth.hashers import make_password

class AccountTests(APITestCase):

    def setUp(self):
        self.user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'testuser@example.com',
            'password': 'testpassword'
        }
        self.user = User.objects.create(
            first_name=self.user_data['first_name'],
            last_name=self.user_data['last_name'],
            email=self.user_data['email'],
            password=make_password(self.user_data['password'])
        )

    def test_user_registration(self):
        response = self.client.post(reverse('accounts:register'), self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)  # One user created in setUp

    def test_user_login(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_user_login_invalid(self):
        response = self.client.post(reverse('accounts:login'), {
            'email': self.user_data['email'],
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_profile(self):
        self.client.login(email=self.user_data['email'], password=self.user_data['password'])
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user_data['email'])