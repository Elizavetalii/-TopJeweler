import base64
import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional
from urllib.parse import quote_plus

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    JsonResponse,
)
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.response import Response
try:
    from weasyprint import HTML
    _WEASYPRINT_ERROR = None
except Exception as exc:  # noqa: F401
    HTML = None
    _WEASYPRINT_ERROR = exc

from apps.cart.models import CartItem
from apps.orders.models import Order, OrderItem, OrderShareToken, Status
try:
    from apps.stores.models import Store
except Exception:
    Store = None

PLACEHOLDER_IMAGE = "https://placehold.co/160x160/F1ECE6/2E2E2E?text=LS"
PERIOD_OPTIONS = {
    '7d': ('Последние 7 дней', 7),
    '30d': ('Последние 30 дней', 30),
    '90d': ('Последние 90 дней', 90),
    'year': ('Последний год', 365),
    'all': ('За всё время', None),
}


def _parse_order_datetime(value):
    if not value:
        return None
    patterns = ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y")
    for fmt in patterns:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _build_order_cards(orders, *, product_term=None, order_number=None, highlight_predicates=None):
    highlight_predicates = highlight_predicates or []
    product_term = (product_term or '').lower()
    cards = []
    for order in orders:
        matched_order = bool(order_number and str(order.order_id) == str(order_number))
        matches = []
        matched_ids = set()
        items_payload = []
        manager = getattr(order, 'orderitem', None) or getattr(order, 'orderitem_set', None)
        if not manager:
            continue
        for order_item in manager.all():
            variant = order_item.product_variant
            product = getattr(variant, 'product', None)
            product_name = getattr(product, 'name', 'Товар')
            product_id = getattr(product, 'product_id', None)
            highlight = False
            if product_term and product_name and product_term in product_name.lower():
                highlight = True
            for predicate in highlight_predicates:
                try:
                    if predicate(order_item):
                        highlight = True
                        break
                except Exception:
                    continue
            if highlight and product_id not in matched_ids:
                matches.append({
                    "name": product_name,
                    "quantity": order_item.quantity,
                    "subtotal": order_item.price * order_item.quantity,
                    "product_id": product_id,
                })
                matched_ids.add(product_id)
            items_payload.append({
                "name": product_name,
                "quantity": order_item.quantity,
                "subtotal": order_item.price * order_item.quantity,
                "product_id": product_id,
                "highlight": highlight,
                "color": getattr(getattr(variant, 'color', None), 'name_color', ''),
                "size": getattr(getattr(variant, 'size', None), 'size', ''),
            })
        match_target = matches[0]["product_id"] if matches else None
        cards.append({
            "id": order.order_id,
            "status": getattr(order.status, 'name_status', '—'),
            "created_at": order.created_at,
            "total": order.total_amount,
            "detail_url": reverse('orders:order_detail', args=[order.order_id]) if hasattr(order, 'order_id') else '#',
            "matches": matches,
            "matched_order": matched_order,
            "items": items_payload,
            "match_target": match_target,
            "store_name": getattr(order.store, 'name', ''),
        })
    return cards


from .serializers import OrderItemSerializer, OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class _OrderJsonMixin:
    def _order_to_dict(self, order: Order):
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "status_id": order.status_id,
            "total_amount": str(order.total_amount),
            "store_id": order.store_id,
            "created_at": order.created_at,
        }


class OrderListView(_OrderJsonMixin, View):
    def get(self, request):
        orders = [self._order_to_dict(o) for o in Order.objects.all()[:100]]
        return JsonResponse({"orders": orders})

    def http_method_not_allowed(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])


class OrderDetailView(_OrderJsonMixin, View):
    def get(self, request, pk=None):
        order = Order.objects.filter(order_id=pk).first() or Order.objects.filter(pk=pk).first()
        if not order:
            return HttpResponseNotFound("Order not found")
        return JsonResponse(self._order_to_dict(order))

    def http_method_not_allowed(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])


@method_decorator(csrf_exempt, name='dispatch')
class OrderCreateView(_OrderJsonMixin, View):
    def post(self, request):
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)

        data = {
            "user_id": payload.get("user_id"),
            "status_id": payload.get("status_id"),
            "total_amount": payload.get("total_amount", 0),
            "store_id": payload.get("store_id"),
            "created_at": payload.get("created_at"),
        }
        order = Order.objects.create(**data)
        return JsonResponse(self._order_to_dict(order), status=201)


@method_decorator(csrf_exempt, name='dispatch')
class OrderUpdateView(_OrderJsonMixin, View):
    def post(self, request, pk=None):
        order = Order.objects.filter(order_id=pk).first() or Order.objects.filter(pk=pk).first()
        if not order:
            return HttpResponseNotFound("Order not found")

        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON"}, status=400)

        for field in ["status_id", "total_amount", "store_id", "created_at"]:
            if field in payload:
                setattr(order, field, payload[field])
        order.save()
        return JsonResponse(self._order_to_dict(order))


@method_decorator(csrf_exempt, name='dispatch')
class OrderDeleteView(View):
    def post(self, request, pk=None):
        order = Order.objects.filter(order_id=pk).first() or Order.objects.filter(pk=pk).first()
        if not order:
            return HttpResponseNotFound("Order not found")
        order.delete()
        return JsonResponse({"deleted": True})

    def http_method_not_allowed(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['POST'])


def _parse_order_datetime(value: Optional[str]) -> datetime:
    if not value:
        return timezone.now()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d.%m.%Y %H:%M"):
        try:
            return timezone.make_aware(datetime.strptime(value, fmt))
        except (ValueError, TypeError):
            continue
    return timezone.now()


def _build_status_timeline(order: Order):
    base_time = _parse_order_datetime(order.created_at)
    history = []
    if hasattr(order, "status_history"):
        history = list(order.status_history.order_by("changed_at"))

    def find_timestamp(keywords, fallback_hours=None):
        for entry in history:
            name = (entry.status_name or "").lower()
            if any(word in name for word in keywords):
                return entry.changed_at
        if fallback_hours is not None:
            return base_time + timedelta(hours=fallback_hours)
        return None

    steps = [
        ("Создан", find_timestamp(["созд", "create"], fallback_hours=0) or base_time),
        ("Собран", find_timestamp(["собр", "готов", "ready", "complete"], fallback_hours=4)),
        ("Передан в доставку", find_timestamp(["перед", "достав", "ship"], fallback_hours=12)),
        ("Доставлен", find_timestamp(["достав", "deliver"], fallback_hours=36)),
    ]

    timeline = []
    now = timezone.now()
    for label, timestamp in steps:
        timeline.append({
            "label": label,
            "timestamp": timestamp,
            "is_done": timestamp is not None and timestamp <= now,
        })
    return timeline


def _ensure_owner(order: Order, user):
    return order.user_id == getattr(user, 'id', None)


def _build_order_items(order: Order):
    items = []
    items_manager = getattr(order, 'orderitem', None) or getattr(order, 'orderitem_set', None)
    if not items_manager:
        return []
    for item in items_manager.select_related(
        'product_variant__product', 'product_variant__color', 'product_variant__size'
    ).prefetch_related(
        'product_variant__images',
        'product_variant__product__images'
    ):
        variant = item.product_variant
        product = getattr(variant, 'product', None)
        product_id = getattr(product, 'product_id', None)
        image = None
        if hasattr(variant, 'get_primary_image_url'):
            image = variant.get_primary_image_url()
        if not image and product and hasattr(product, 'images'):
            legacy = product.images.first()
            if legacy and legacy.image_url:
                image = legacy.image_url
        image = image or PLACEHOLDER_IMAGE
        items.append({
            "name": getattr(product, 'name', str(variant)),
            "product_id": product_id,
            "detail_url": reverse('product_detail', args=[product_id]) if product_id else None,
            "color": getattr(getattr(variant, 'color', None), 'name_color', ''),
            "size": getattr(getattr(variant, 'size', None), 'size', ''),
            "quantity": item.quantity,
            "price": item.price,
            "subtotal": item.price * item.quantity,
            "photo": image,
        })
    return items


def _order_context(order: Order):
    items = _build_order_items(order)
    timeline = _build_status_timeline(order)
    payment = order.payment_set.first() if hasattr(order, 'payment_set') else None
    items_total = sum(i["subtotal"] for i in items)
    discount = getattr(order, 'discount_amount', Decimal('0'))
    promo_code = getattr(order.promo_code, 'code', None)
    status_label = (getattr(order.status, 'name_status', '') or '').lower()
    non_cancel_keywords = ('отмен', 'достав', 'выполн', 'заверш', 'closed', 'shipp')
    can_cancel = not any(keyword in status_label for keyword in non_cancel_keywords)
    return {
        "order": order,
        "items": items,
        "items_total": items_total,
        "timeline": timeline,
        "payment": payment,
        "store": getattr(order.store, 'name', 'Бутик'),
        "total": order.total_amount,
        "discount": discount,
        "promo_code": promo_code,
        "can_cancel": can_cancel,
    }


@login_required(login_url='accounts:login')
def order_history(request):
    qs = (
        Order.objects.filter(user=request.user)
        .select_related('status', 'store')
        .prefetch_related(
            'orderitem_set__product_variant__product',
            'orderitem_set__product_variant__images',
            'orderitem_set__product_variant__product__images'
        )
        .order_by('-order_id')
    )
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    store_filter = request.GET.get('store', '').strip()
    period = request.GET.get('period', 'all')
    order_number_query = None
    product_term = None
    if query:
        filters = Q()
        if query.isdigit():
            filters |= Q(order_id=int(query))
            order_number_query = query
        filters |= Q(orderitem__product_variant__product__name__icontains=query)
        qs = qs.filter(filters)
        if not query.isdigit():
            product_term = query.lower()
    if status_filter:
        qs = qs.filter(status__name_status=status_filter)
    if store_filter:
        qs = qs.filter(store__store_id=store_filter)
    orders = list(qs)
    if period in PERIOD_OPTIONS and PERIOD_OPTIONS[period][1]:
        start_date = timezone.now() - timedelta(days=PERIOD_OPTIONS[period][1])
        filtered = []
        for order in orders:
            parsed = _parse_order_datetime(order.created_at)
            if parsed and parsed >= start_date:
                filtered.append(order)
        orders = filtered
    paginator = Paginator(orders, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    order_cards = _build_order_cards(
        page_obj.object_list,
        product_term=product_term,
        order_number=order_number_query,
    )
    status_options = list(Status.objects.order_by('name_status').values_list('name_status', flat=True))
    store_options = []
    if Store is not None:
        store_qs = Store.objects.filter(order__user=request.user).distinct().order_by('name')
        store_options = [
            {"id": getattr(store, 'store_id', None), "name": getattr(store, 'name', '')}
            for store in store_qs
        ]
    base_query = request.GET.copy()
    if 'page' in base_query:
        base_query.pop('page')
    context = {
        "orders": order_cards,
        "page_obj": page_obj,
        "filters": {
            "q": query,
            "status": status_filter,
            "store": store_filter,
            "period": period,
            "period_options": PERIOD_OPTIONS,
            "status_options": status_options,
            "store_options": store_options,
            "base_query": base_query.urlencode(),
        },
    }
    return render(request, 'orders/order_history.html', context)


@login_required(login_url='accounts:login')
def order_detail_page(request, order_id: int):
    order = get_object_or_404(
        Order.objects.select_related('status', 'store', 'user')
        .prefetch_related(
            'orderitem_set__product_variant__product',
            'orderitem_set__product_variant__color',
            'orderitem_set__product_variant__size',
            'orderitem_set__product_variant__images',
            'orderitem_set__product_variant__product__images',
            'payment_set',
            'status_history__status',
            'status_history__changed_by',
        ),
        order_id=order_id,
        user=request.user,
    )
    focus_target = request.GET.get('focus')
    context = {
        "order_ctx": _order_context(order),
        "receipt_url": reverse('orders:order_receipt', args=[order_id]),
        "share_url": reverse('orders:order_share', args=[order_id]),
        "repeat_url": reverse('orders:order_repeat', args=[order_id]),
        "cancel_url": reverse('orders:order_cancel', args=[order_id]),
        "focus_target": focus_target,
        "placeholder_image": PLACEHOLDER_IMAGE,
    }
    return render(request, 'orders/order_detail.html', context)


def _generate_qr_data(data: str) -> str:
    qr = qrcode.QRCode(version=2, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def _receipt_context(order: Order, request, public=False):
    items = _build_order_items(order)
    subtotal = sum(Decimal(item['subtotal']) for item in items)
    discount = getattr(order, 'discount_amount', Decimal('0'))
    taxable_subtotal = max(Decimal('0'), subtotal - discount)
    # Налог не применяется — цены окончательные
    tax = Decimal('0.00')
    shipping = Decimal('0.00')
    total = taxable_subtotal + shipping
    detail_url = request.build_absolute_uri(reverse('orders:order_detail', args=[order.order_id]))
    qr_target = detail_url if not public else request.build_absolute_uri(request.path.replace('/receipt/', '/'))
    customer_name = ''
    if order.user:
        full_name = order.user.get_full_name() or order.user.username
        if public and full_name:
            parts = full_name.split()
            customer_name = f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]
        else:
            customer_name = full_name
    address = '' if public else getattr(getattr(order.user, 'profile', None), 'address', '')
    return {
        "order": order,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "taxable_subtotal": taxable_subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "issued_at": timezone.now(),
        "customer_name": customer_name,
        "address": address,
        "qr_code": _generate_qr_data(qr_target),
        "is_public": public,
        "promo_code": getattr(order.promo_code, 'code', None),
    }


def _ensure_weasyprint():
    if HTML is None:
        message = "WeasyPrint недоступен: установите системные библиотеки GTK/Pango и python-пакеты."
        if _WEASYPRINT_ERROR:
            message = f"{message} Причина: {_WEASYPRINT_ERROR}"
        raise RuntimeError(message)


def _render_receipt_pdf(order: Order, request, public=False):
    """Render receipt to PDF using WeasyPrint.

    If WeasyPrint or system libs are unavailable, the caller can choose to
    fall back to HTML (handled in the view). This function will raise on error.
    """
    _ensure_weasyprint()
    context = _receipt_context(order, request, public=public)
    html = render_to_string('orders/receipt.html', context)
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    return pdf


@login_required(login_url='accounts:login')
def order_receipt_pdf(request, order_id: int):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    inline = request.GET.get('inline') == '1'
    try:
        pdf = _render_receipt_pdf(order, request)
        response = HttpResponse(pdf, content_type='application/pdf')
        disposition = 'inline' if inline else 'attachment'
        response['Content-Disposition'] = f"{disposition}; filename=receipt_{order_id}.pdf"
        return response
    except Exception as exc:
        # Fallback to HTML representation so пользователь не видит 500
        context = _receipt_context(order, request, public=False)
        html = render_to_string('orders/receipt.html', context)
        if settings.DEBUG:
            html = f"<!-- PDF generation error: {exc} -->\n" + html
        return HttpResponse(html)


def order_receipt_public(request, order_id: int, token: str):
    share_token = get_object_or_404(OrderShareToken, order_id=order_id, token=token)
    if share_token.expires_at < timezone.now():
        return HttpResponseForbidden("Ссылка больше не активна")
    order = share_token.order
    try:
        pdf = _render_receipt_pdf(order, request, public=True)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f"inline; filename=receipt_{order_id}.pdf"
        return response
    except Exception as exc:
        context = _receipt_context(order, request, public=True)
        html = render_to_string('orders/receipt.html', context)
        if settings.DEBUG:
            html = f"<!-- PDF generation error: {exc} -->\n" + html
        return HttpResponse(html)


def _create_share_token(order: Order, channel: Optional[str] = None) -> OrderShareToken:
    token = get_random_string(32)
    expires_at = timezone.now() + timedelta(days=7)
    return OrderShareToken.objects.create(order=order, token=token, channel=channel, expires_at=expires_at)


def _build_public_receipt_url(order: Order, request) -> str:
    token = _create_share_token(order)
    return request.build_absolute_uri(reverse('orders:order_receipt_public', args=[order.order_id, token.token]))


@login_required(login_url='accounts:login')
@require_POST
def order_share(request, order_id: int):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    try:
        payload = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        payload = request.POST
    channel = (payload.get('channel') or 'link').strip().lower()
    allowed = {'telegram', 'vk', 'facebook', 'email', 'link'}
    if channel not in allowed:
        return JsonResponse({'error': 'Unknown channel'}, status=400)

    public_receipt_url = _build_public_receipt_url(order, request)
    encoded = quote_plus(public_receipt_url)
    share_url = public_receipt_url
    if channel == 'telegram':
        share_url = f"https://t.me/share/url?url={encoded}"
    elif channel == 'vk':
        share_url = f"https://vk.com/share.php?url={encoded}"
    elif channel == 'facebook':
        share_url = f"https://www.facebook.com/sharer/sharer.php?u={encoded}"
    elif channel == 'email':
        subject = f"Чек заказа №{order.order_id}"
        body = f"Скачать чек: {public_receipt_url}"
        share_url = f"mailto:?subject={subject}&body={body}"

    return JsonResponse({"status": "ok", "channel": channel, "share_url": share_url})


@login_required(login_url='accounts:login')
@require_POST
def order_repeat(request, order_id: int):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    added = 0
    items_manager = getattr(order, 'orderitem', None) or getattr(order, 'orderitem_set', None)
    if not items_manager:
        messages.info(request, "Не нашли товары в заказе.")
        return redirect('orders:order_detail', order_id=order_id)
    for item in items_manager.select_related('product_variant'):
        variant = item.product_variant
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product_variant=variant,
            defaults={'price': getattr(variant, 'price', item.price), 'quantity': item.quantity},
        )
        if not created:
            cart_item.quantity = (cart_item.quantity or 0) + item.quantity
            cart_item.price = getattr(variant, 'price', item.price)
            cart_item.save()
        added += 1
    messages.success(request, f"Товары из заказа №{order_id} добавлены в корзину.")
    return redirect('view_cart')


@login_required(login_url='accounts:login')
@require_POST
def order_cancel(request, order_id: int):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    status_name = (order.status.name_status if order.status else '').lower()
    if 'достав' in status_name:
        messages.info(request, "Заказ уже доставлен и не может быть отменён.")
        return redirect('orders:order_detail', order_id=order_id)
    cancelled_status, _ = Status.objects.get_or_create(name_status='Отменён')
    order.status = cancelled_status
    order.save()
    messages.info(request, "Заказ отменён")
    return redirect('orders:order_detail', order_id=order_id)
@login_required(login_url='accounts:login')
def order_search(request):
    qs = (
        Order.objects.filter(user=request.user)
        .select_related('status', 'store')
        .prefetch_related(
            'orderitem_set__product_variant__product__category',
            'orderitem_set__product_variant__color',
            'orderitem_set__product_variant__size',
            'orderitem_set__product_variant__images',
            'orderitem_set__product_variant__product__images',
        )
        .order_by('-order_id')
    )
    form = {
        "product_name": request.GET.get('product_name', '').strip(),
        "article": request.GET.get('article', '').strip(),
        "brand": request.GET.get('brand', '').strip(),
        "color": request.GET.get('color', '').strip(),
        "size": request.GET.get('size', '').strip(),
        "price_min": request.GET.get('price_min', '').strip(),
        "price_max": request.GET.get('price_max', '').strip(),
        "date_from": request.GET.get('date_from', '').strip(),
        "date_to": request.GET.get('date_to', '').strip(),
        "status": request.GET.get('status', '').strip(),
        "store": request.GET.get('store', '').strip(),
    }
    highlight_predicates = []
    product_term = None
    order_number_query = None
    if form["product_name"]:
        qs = qs.filter(orderitem__product_variant__product__name__icontains=form["product_name"])
        product_term = form["product_name"].lower()
    if form["article"]:
        article = form["article"]
        if article.isdigit():
            qs = qs.filter(order_id=int(article))
            order_number_query = article
        else:
            qs = qs.filter(orderitem__product_variant__product__name__icontains=article)
            product_term = article.lower()
    if form["brand"]:
        qs = qs.filter(orderitem__product_variant__product__category__name__icontains=form["brand"])
    if form["color"]:
        qs = qs.filter(orderitem__product_variant__color__name_color__icontains=form["color"])
        color_lower = form["color"].lower()
        highlight_predicates.append(
            lambda item, color_lower=color_lower: color_lower in (
                getattr(getattr(item.product_variant, 'color', None), 'name_color', '') or ''
            ).lower()
        )
    if form["size"]:
        qs = qs.filter(orderitem__product_variant__size__size__icontains=form["size"])
        size_lower = form["size"].lower()
        highlight_predicates.append(
            lambda item, size_lower=size_lower: size_lower in (
                getattr(getattr(item.product_variant, 'size', None), 'size', '') or ''
            ).lower()
        )
    if form["status"]:
        qs = qs.filter(status__name_status=form["status"])
    if form["store"]:
        qs = qs.filter(store__store_id=form["store"])
    price_min = form["price_min"]
    price_max = form["price_max"]
    try:
        price_min = Decimal(price_min) if price_min else None
    except InvalidOperation:
        price_min = None
    try:
        price_max = Decimal(price_max) if price_max else None
    except InvalidOperation:
        price_max = None

    orders = list(qs)
    date_from = None
    date_to = None
    if form["date_from"]:
        try:
            date_from = datetime.strptime(form["date_from"], "%Y-%m-%d")
        except ValueError:
            date_from = None
    if form["date_to"]:
        try:
            date_to = datetime.strptime(form["date_to"], "%Y-%m-%d")
        except ValueError:
            date_to = None

    filtered_orders = []
    for order in orders:
        if price_min is not None and order.total_amount < price_min:
            continue
        if price_max is not None and order.total_amount > price_max:
            continue
        parsed = _parse_order_datetime(order.created_at)
        if date_from and (not parsed or parsed < date_from):
            continue
        if date_to and (not parsed or parsed > date_to + timedelta(days=1)):
            continue
        filtered_orders.append(order)

    paginator = Paginator(filtered_orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    cards = _build_order_cards(
        page_obj.object_list,
        product_term=product_term,
        order_number=order_number_query,
        highlight_predicates=highlight_predicates,
    )
    status_options = list(Status.objects.order_by('name_status').values_list('name_status', flat=True))
    store_options = []
    if Store is not None:
        store_qs = Store.objects.filter(order__user=request.user).distinct().order_by('name')
        store_options = [
            {"id": getattr(store, 'store_id', None), "name": getattr(store, 'name', '')}
            for store in store_qs
        ]
    base_query = request.GET.copy()
    if 'page' in base_query:
        base_query.pop('page')
    context = {
        "orders": cards,
        "page_obj": page_obj,
        "filters": form,
        "status_options": status_options,
        "store_options": store_options,
        "base_query": base_query.urlencode(),
    }
    return render(request, 'orders/order_search.html', context)
