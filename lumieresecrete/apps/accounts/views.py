from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy

from .forms import UserRegistrationForm, UserLoginForm, UserSettingsForm
from .models import UserSettings, Role, UserRole
from apps.orders.models import OrderNotification


def _user_is_manager(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return UserRole.objects.filter(
        user=user,
        role__role_name__iexact='менеджер'
    ).exists()


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('catalog_list')
    form = UserRegistrationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            role, _ = Role.objects.get_or_create(role_name='Клиент')
            UserRole.objects.get_or_create(user=user, role=role)
            login(request, user)
            messages.success(request, "Добро пожаловать в Lumiere Secrète!")
            return redirect('catalog_list')
        messages.error(request, "Проверьте введённые данные.")
    return render(request, 'accounts/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('catalog_list')
    form = UserLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password']
        )
        if user is not None:
            login(request, user)
            messages.success(request, "Вы успешно вошли.")
            next_url = request.GET.get('next')
            if not next_url:
                if _user_is_manager(user):
                    next_url = reverse('reports:manager_dashboard')
                elif user.is_staff:
                    next_url = reverse('admin:index')
                else:
                    next_url = reverse('catalog_list')
            return redirect(next_url)
        messages.error(request, "Неверный email или пароль.")
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Вы вышли из аккаунта.")
    return redirect('catalog_list')


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    is_manager = UserRole.objects.filter(
        user=request.user,
        role__role_name__iexact='менеджер'
    ).exists()
    allow_catalog_preferences = not (request.user.is_staff or is_manager)
    initial_data = {
        'theme': settings_obj.theme,
        'date_format': settings_obj.date_format,
        'page_size': settings_obj.page_size,
        'favorite_icon': settings_obj.favorite_icon,
    }
    intent = request.POST.get('intent')
    settings_form = UserSettingsForm(
        request.POST if request.method == 'POST' and intent != 'password' else None,
        initial=initial_data,
        allow_catalog_preferences=allow_catalog_preferences,
    )
    password_form = PasswordChangeForm(
        user=request.user,
        data=request.POST if request.method == 'POST' and intent == 'password' else None
    )
    if request.method == 'POST':
        if intent == 'password':
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Пароль обновлён.")
                return redirect('accounts:profile')
            messages.error(request, "Исправьте ошибки в форме смены пароля.")
        else:
            if settings_form.is_valid():
                for field in ['theme', 'date_format']:
                    setattr(settings_obj, field, settings_form.cleaned_data[field])
                if allow_catalog_preferences:
                    for field in ['page_size', 'favorite_icon']:
                        setattr(settings_obj, field, settings_form.cleaned_data[field])
                settings_obj.save()
                messages.success(request, "Настройки обновлены.")
                return redirect('accounts:profile')
            messages.error(request, "Проверьте введённые настройки.")
    notifications = list(OrderNotification.objects.filter(user=request.user).order_by('-created_at')[:10])
    unread_count = OrderNotification.objects.filter(user=request.user, is_read=False).count()
    return render(request, 'accounts/profile.html', {
        'form': settings_form,
        'password_form': password_form,
        'formatted_date_joined': _format_user_datetime(request.user, request.user.date_joined),
        'formatted_last_login': _format_user_datetime(request.user, request.user.last_login),
        'allow_catalog_preferences': allow_catalog_preferences,
        'notifications': notifications,
        'unread_notifications': unread_count,
    })


@login_required
@require_http_methods(["POST"])
def notifications_mark_read(request):
    OrderNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(["POST"])
def update_theme(request):
    """Lightweight endpoint to persist user's theme from admin toggle or site.
    Expected POST body form-encoded or JSON with key 'theme' in {'light','dark'}.
    Returns JSON with the saved theme.
    """
    theme = (request.POST.get('theme') or request.body.decode('utf-8') or '').lower()
    if 'dark' in theme:
        value = 'dark'
    elif 'light' in theme:
        value = 'light'
    else:
        # Try JSON parse
        try:
            import json
            payload = json.loads(request.body.decode() or '{}')
            value = 'dark' if (payload.get('theme') == 'dark') else 'light'
        except Exception:
            value = 'light'
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
    settings_obj.theme = value
    settings_obj.save(update_fields=['theme'])
    return JsonResponse({'status': 'ok', 'theme': value})


class PasswordResetViewSafe(PasswordResetView):
    """Password reset that never raises on email send and sends HTML.

    - Uses our custom HTML template and Russian subject
    - Adds a plain-text fallback part
    - Sets fail_silently=True to avoid HTTP 500 if SMTP недоступен
    """
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.txt'
    # Отправляем только текстовое письмо, чтобы исключить отображение HTML-кода
    html_email_template_name = None
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

    def form_valid(self, form):
        form.save(
            use_https=self.request.is_secure(),
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            request=self.request,
            from_email=None,
            extra_email_context={'site_name': 'Lumiere Secrète'},
            fail_silently=True,
        )
        return redirect(self.get_success_url())
def _format_user_datetime(user, value):
    if not value:
        return "—"
    fmt = "%d.%m.%Y %H:%M"
    try:
        settings_obj = user.usersettings
        if settings_obj.date_format:
            fmt = settings_obj.date_format
    except UserSettings.DoesNotExist:
        pass
    try:
        return timezone.localtime(value).strftime(fmt)
    except Exception:
        try:
            return value.strftime(fmt)
        except Exception:
            return str(value)
