import csv
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.db import connections
from django.db.models import Sum
from openpyxl import Workbook

from apps.orders.models import Order, OrderItem
from apps.catalog.models import Product, Category, ProductReview
from apps.stores.models import Store
from apps.product_variants.models import ProductVariant
from apps.accounts.models import UserRole
from apps.orders.views import _parse_order_datetime

PERIOD_CHOICES = {
    '7d': ('Последние 7 дней', 7),
    '30d': ('Последние 30 дней', 30),
    '90d': ('Последние 90 дней', 90),
    'year': ('Последний год', 365),
    'all': ('За всё время', None),
}

def sales_report(request):
    """Generate a sales report for a specified period."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        return JsonResponse({'error': 'Please provide start_date and end_date.'}, status=400)

    sales_data = Order.objects.values('store__name').annotate(total_sales=Sum('total_amount'))

    return JsonResponse(list(sales_data), safe=False)

def product_report(request):
    """Generate a report of products sold."""
    product_data = Product.objects.annotate(total_sold=Sum('variants__orderitem__quantity')).filter(total_sold__gt=0)

    return render(request, 'reports/product_report.html', {'products': product_data})

def store_report(request):
    """Generate a report of store performance."""
    store_data = Store.objects.annotate(total_orders=Sum('orders__id')).filter(total_orders__gt=0)

    return render(request, 'reports/store_report.html', {'stores': store_data})


def _user_is_manager(user):
    return UserRole.objects.filter(user=user, role__role_name__iexact='менеджер').exists()


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_input_date(value):
    if not value:
        return None
    patterns = ("%Y-%m-%d", "%d.%m.%Y")
    for fmt in patterns:
        try:
            dt = datetime.strptime(value, fmt)
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except (ValueError, TypeError):
            continue
    return None


def _resolve_period(request):
    now = timezone.now()
    period_key = request.GET.get('period', '30d')
    if period_key in PERIOD_CHOICES and PERIOD_CHOICES[period_key][1]:
        days = PERIOD_CHOICES[period_key][1]
        start = now - timedelta(days=days)
        end = now
    else:
        start = _parse_input_date(request.GET.get('start')) or (now - timedelta(days=30))
        end = _parse_input_date(request.GET.get('end')) or now
        period_key = 'custom'
    if start > end:
        start, end = end, start
    return start, end, period_key


def _filtered_orders(start, end, store_id=None):
    qs = Order.objects.select_related('status', 'store')
    if store_id:
        qs = qs.filter(store__store_id=store_id)
    tz = timezone.get_current_timezone()
    filtered = []
    for order in qs:
        parsed = _parse_order_datetime(order.created_at)
        if not parsed:
            continue
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, tz)
        if start and parsed < start:
            continue
        if end and parsed > end:
            continue
        filtered.append((order, parsed))
    return filtered


def _gather_dashboard_data(request):
    start, end, period_key = _resolve_period(request)
    category_filter = request.GET.get('category') or ''
    store_filter = request.GET.get('store') or ''

    orders = _filtered_orders(start, end, store_filter or None)
    order_ids = [order.order_id for order, _ in orders]
    items_qs = OrderItem.objects.filter(order__order_id__in=order_ids).select_related(
        'order__store',
        'product_variant__product__category',
        'product_variant__size',
    )
    if category_filter:
        items_qs = items_qs.filter(product_variant__product__category__category_id=category_filter)
    items = list(items_qs)

    product_stats = defaultdict(lambda: {'name': '', 'quantity': 0, 'revenue': Decimal('0')})
    category_stats = defaultdict(lambda: {'name': '', 'quantity': 0, 'revenue': Decimal('0')})
    size_stats = defaultdict(int)
    store_stats = defaultdict(lambda: {'name': '', 'orders': 0, 'revenue': Decimal('0')})
    total_revenue = Decimal('0')
    daily_metrics = defaultdict(lambda: {'count': 0, 'revenue': Decimal('0')})

    for item in items:
        qty = item.quantity or 0
        price = item.price or Decimal('0')
        line_total = price * qty
        total_revenue += line_total
        variant = item.product_variant
        product = getattr(variant, 'product', None)
        category = getattr(product, 'category', None)
        size_label = getattr(variant.size, 'size', 'Без размера')
        product_name = getattr(product, 'name', 'Товар')
        product_id = getattr(product, 'product_id', None)
        if product_id is not None:
            product_entry = product_stats[product_id]
            product_entry['name'] = product_name
            product_entry['quantity'] += qty
            product_entry['revenue'] += line_total
        if category:
            cat_entry = category_stats[category.category_id]
            cat_entry['name'] = category.name
            cat_entry['quantity'] += qty
            cat_entry['revenue'] += line_total
        size_stats[size_label] += qty
        store = item.order.store
        if store:
            store_entry = store_stats[store.store_id]
            store_entry['name'] = store.name
            store_entry['revenue'] += line_total

    store_counts = Counter(order.store.store_id if order.store else 'unknown' for order, _ in orders)
    for store_id, count in store_counts.items():
        if store_id in store_stats:
            store_stats[store_id]['orders'] = count
        elif store_id != 'unknown':
            store_obj = next((order.store for order, _ in orders if order.store and order.store.store_id == store_id), None)
            if store_obj:
                store_stats[store_id] = {
                    'name': store_obj.name,
                    'orders': count,
                    'revenue': Decimal('0'),
                }

    status_breakdown = Counter(getattr(order.status, 'name_status', 'Без статуса') for order, _ in orders)
    inventory = ProductVariant.objects.select_related('product', 'size', 'store').order_by('quantity')[:10]
    User = get_user_model()
    new_users = User.objects.filter(date_joined__gte=start).count()
    active_users = User.objects.filter(last_login__gte=start).count()
    pending_reviews = ProductReview.objects.filter(is_public=False).select_related('product', 'user').order_by('-created_at')[:20]
    recent_orders = sorted(orders, key=lambda item: item[1], reverse=True)[:10]
    for order, parsed in orders:
        day = parsed.date()
        entry = daily_metrics[day]
        entry['count'] += 1
        total_amount = getattr(order, 'total_amount', None) or Decimal('0')
        entry['revenue'] += total_amount

    filters_state = {
        'start': start.date().isoformat(),
        'end': end.date().isoformat(),
        'category': category_filter,
        'store': store_filter,
        'period': period_key,
        'period_label': PERIOD_CHOICES.get(period_key, ('Период', None))[0],
        'export_format': request.GET.get('format', 'csv'),
    }

    query_string = request.GET.urlencode()
    base_export = reverse('reports:manager_export')
    export_url = f"{base_export}?{query_string}" if query_string else base_export

    context = {
        'filters': filters_state,
        'period_choices': PERIOD_CHOICES,
        'category_options': Category.objects.order_by('name'),
        'store_options': Store.objects.order_by('name'),
        'product_stats': sorted(product_stats.values(), key=lambda x: x['revenue'], reverse=True),
        'category_stats': sorted(category_stats.values(), key=lambda x: x['revenue'], reverse=True),
        'size_stats': sorted(size_stats.items(), key=lambda x: x[1], reverse=True),
        'store_stats': sorted(store_stats.values(), key=lambda x: x['revenue'], reverse=True),
        'order_summary': {
            'count': len(orders),
            'revenue': total_revenue,
        },
        'status_breakdown': list(status_breakdown.items()),
        'inventory': inventory,
        'user_activity': {
            'new': new_users,
            'active': active_users,
        },
        'pending_reviews': pending_reviews,
        'recent_orders': [
            {
                'id': order.order_id,
                'status': getattr(order.status, 'name_status', '—'),
                'store': getattr(order.store, 'name', '—'),
                'total': order.total_amount,
                'created': parsed,
            } for order, parsed in recent_orders
        ],
        'daily_metrics': [
            {
                'date': day.isoformat(),
                'label': day.strftime('%d.%m'),
                'count': data['count'],
                'revenue': data['revenue'],
            }
            for day, data in sorted(daily_metrics.items())
        ],
        'export_query': query_string,
        'start': start,
        'end': end,
    }
    return context, items


@login_required
def manager_dashboard(request):
    if not _user_is_manager(request.user):
        return HttpResponseForbidden("Недостаточно прав.")
    context, _ = _gather_dashboard_data(request)
    custom_views = _fetch_analytics_views()
    context["view_snapshots"] = custom_views
    return render(request, 'reports/manager_dashboard.html', context)


@login_required
def manager_stats(request):
    if not _user_is_manager(request.user):
        return HttpResponseForbidden("Недостаточно прав.")
    context, _ = _gather_dashboard_data(request)
    context['chart_payload'] = {
        'status': [
            {'label': label or 'Нет статуса', 'value': count}
            for label, count in context['status_breakdown']
        ],
        'categories': [
            {'label': item['name'], 'value': _to_float(item['revenue']), 'count': item['quantity']}
            for item in context['category_stats'][:10]
        ],
        'stores': [
            {
                'label': store['name'],
                'value': _to_float(store['revenue']),
                'orders': store.get('orders', 0)
            }
            for store in context['store_stats'][:10]
        ],
        'sizes': [
            {'label': label, 'value': qty}
            for label, qty in context['size_stats'][:10]
        ],
        'orders': [
            {'label': f"#{order['id']}", 'value': _to_float(order['total'])}
            for order in context['recent_orders']
        ],
        'products': [
            {'label': item['name'], 'value': _to_float(item['revenue']), 'count': item['quantity']}
            for item in context['product_stats'][:8]
        ],
        'daily': [
            {'label': entry['label'], 'value': _to_float(entry['revenue']), 'count': entry['count']}
            for entry in context['daily_metrics']
        ],
    }
    return render(request, 'reports/manager_stats.html', context)


def _fetch_analytics_views():
    data = {
        "order_summary": [],
        "product_performance": [],
        "user_activity": [],
    }
    with connections['default'].cursor() as cursor:
        try:
            cursor.execute('SELECT order_id, user_name, total_amount, status_name FROM "vw_order_summary" ORDER BY order_id DESC LIMIT 5;')
            data["order_summary"] = cursor.fetchall()
        except Exception:
            data["order_summary"] = []
        try:
            cursor.execute('SELECT product_name, category_name, total_quantity, total_revenue FROM "vw_product_performance" ORDER BY total_revenue DESC LIMIT 5;')
            data["product_performance"] = cursor.fetchall()
        except Exception:
            data["product_performance"] = []
        try:
            cursor.execute('SELECT username, email, orders_count, orders_total, last_order_date FROM "vw_user_activity" ORDER BY orders_total DESC LIMIT 5;')
            data["user_activity"] = cursor.fetchall()
        except Exception:
            data["user_activity"] = []
    return data


@login_required
def manager_export(request):
    if not _user_is_manager(request.user):
        return HttpResponseForbidden("Недостаточно прав.")
    context, items = _gather_dashboard_data(request)
    export_format = request.GET.get('format', context['filters'].get('export_format', 'csv')).lower()
    filename_base = f"manager-report-{context['filters']['start']}-to-{context['filters']['end']}"

    headers = ['Order ID', 'Дата', 'Магазин', 'Товар', 'Количество', 'Выручка']
    rows = []
    for item in items:
        order = item.order
        product = getattr(item.product_variant, 'product', None)
        product_name = getattr(product, 'name', 'Товар')
        store_name = getattr(order.store, 'name', '—')
        qty = item.quantity or 0
        price = item.price or Decimal('0')
        rows.append([
            order.order_id,
            order.created_at,
            store_name,
            product_name,
            qty,
            f"{(price * qty):.2f}",
        ])

    if export_format == 'xlsx':
        wb = Workbook()
        ws = wb.active
        ws.title = "Отчёт"
        ws.append(headers)
        for row in rows:
            ws.append(row)
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
        return response

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


@login_required
@require_http_methods(["POST"])
def manager_review_action(request, pk=None):
    if not _user_is_manager(request.user):
        return HttpResponseForbidden("Недостаточно прав.")
    review = get_object_or_404(ProductReview, pk=pk)
    action = request.POST.get('action')
    next_url = request.POST.get('next')
    if action == 'approve':
        review.is_public = True
        review.save(update_fields=['is_public'])
        messages.success(request, "Отзыв опубликован.")
    elif action == 'hide':
        review.is_public = False
        review.save(update_fields=['is_public'])
        messages.info(request, "Отзыв скрыт.")
    elif action == 'delete':
        review.delete()
        messages.success(request, "Отзыв удалён.")
    else:
        messages.error(request, "Неизвестное действие.")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect('reports:manager_dashboard')


@login_required
def manager_reviews(request):
    if not _user_is_manager(request.user):
        return HttpResponseForbidden("Недостаточно прав.")
    status_filter = request.GET.get('status', 'pending')
    qs = ProductReview.objects.select_related('product', 'user').order_by('-created_at')
    if status_filter == 'pending':
        qs = qs.filter(is_public=False)
    elif status_filter == 'published':
        qs = qs.filter(is_public=True)
    pending_count = ProductReview.objects.filter(is_public=False).count()
    published_count = ProductReview.objects.filter(is_public=True).count()
    all_count = pending_count + published_count
    context = {
        'status_filter': status_filter,
        'reviews': qs,
        'pending_count': pending_count,
        'published_count': published_count,
        'all_count': all_count,
    }
    return render(request, 'reports/manager_reviews.html', context)
