import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Повторите пароль")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('placeholder', field.label)
            field.widget.attrs.setdefault('class', 'input')
        self.fields['password'].widget.attrs['class'] = 'input'
        self.fields['password_confirm'].widget.attrs['class'] = 'input'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Пароли не совпадают.")

        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""
        if len(password) < 6:
            raise ValidationError("Пароль должен содержать не менее 6 символов.")
        if not re.search(r'[A-ZА-Я]', password):
            raise ValidationError("Добавьте хотя бы одну заглавную букву.")
        if not re.search(r'[a-zа-я]', password):
            raise ValidationError("Добавьте хотя бы одну строчную букву.")
        if not re.search(r'\d', password):
            raise ValidationError("Добавьте хотя бы одну цифру.")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>/?]', password):
            raise ValidationError("Добавьте хотя бы один специальный символ.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data.get('email')
        user.username = email or user.username
        user.email = email
        user.is_staff = False
        user.is_superuser = False
        user.set_password(self.cleaned_data.get("password"))
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'input')


FAVORITE_ICON_CHOICES = [
    ('heart', 'Сердечко'),
    ('star', 'Звезда'),
]

DATE_FORMAT_CHOICES = [
    ('%d.%m.%Y %H:%M', '13.11.2025 20:41'),
    ('%d.%m.%Y', '13.11.2025'),
    ('%Y-%m-%d', '2025-11-13'),
    ('%d %B %Y', '13 ноября 2025'),
]


class UserSettingsForm(forms.Form):
    theme = forms.ChoiceField(choices=[('light', 'Светлая'), ('dark', 'Тёмная')])
    date_format = forms.ChoiceField(choices=DATE_FORMAT_CHOICES, required=False)
    page_size = forms.IntegerField(min_value=1, required=False)
    favorite_icon = forms.ChoiceField(choices=FAVORITE_ICON_CHOICES, required=False)

    def __init__(self, *args, allow_catalog_preferences=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not allow_catalog_preferences:
            for field_name in ('page_size', 'favorite_icon'):
                self.fields[field_name].required = False
