import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.orders.models import Order, OrderItem, Status, Payment, PromoCode
try:
    from apps.catalog.models import Favorite
except Exception:
    Favorite = None

PLACEHOLDER_IMAGE = "https://placehold.co/120x120/F1ECE6/2E2E2E?text=LS"

try:
    from .models import CartItem
except Exception:
    CartItem = None

try:
    from apps.product_variants.models import ProductVariant
except Exception:
    ProductVariant = None


def _wants_json(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json'


def _format_currency(value):
    if value is None:
        return "—"
    amount = (value or Decimal('0')).quantize(Decimal('0.01'))
    text = f"{amount:.2f}".rstrip('0').rstrip('.')
    return f"{text} ₽"


PROMO_SESSION_KEY = 'cart_promo'


def _store_promo_code(request, code: str):
    if code:
        request.session[PROMO_SESSION_KEY] = {"code": code.strip().upper()}
    elif PROMO_SESSION_KEY in request.session:
        del request.session[PROMO_SESSION_KEY]
    request.session.modified = True


def _get_stored_promo_code(request) -> str:
    data = request.session.get(PROMO_SESSION_KEY) or {}
    code = (data.get('code') or '').strip()
    return code.upper()


def _clear_promo_code(request):
    if PROMO_SESSION_KEY in request.session:
        del request.session[PROMO_SESSION_KEY]
        request.session.modified = True


def _evaluate_promo(promo: PromoCode, subtotal: Decimal):
    now = timezone.now()
    if not promo.is_active:
        return Decimal('0'), "Промокод больше не активен.", False
    if promo.valid_from and now < promo.valid_from:
        return Decimal('0'), "Промокод ещё не начал действовать.", False
    if promo.valid_to and now > promo.valid_to:
        return Decimal('0'), "Срок действия промокода истёк.", False
    if promo.usage_limit and promo.usage_count >= promo.usage_limit:
        return Decimal('0'), "Промокод больше недоступен.", False
    min_total = promo.min_order_total or Decimal('0')
    if subtotal < min_total:
        return (
            Decimal('0'),
            f"Минимальная сумма заказа для промокода — {_format_currency(min_total)}.",
            True,
        )
    discount = Decimal('0')
    if promo.discount_percent:
        percent = promo.discount_percent / Decimal('100')
        discount = (subtotal * percent).quantize(Decimal('0.01'))
    elif promo.discount_amount:
        discount = min(promo.discount_amount, subtotal).quantize(Decimal('0.01'))
    if discount <= 0:
        return Decimal('0'), "Скидка не может быть применена к этой сумме.", False
    return discount, None, False


def _resolve_cart_promo(request, subtotal: Decimal):
    code = _get_stored_promo_code(request)
    if not code:
        return {
            "code": "",
            "description": "",
            "discount": Decimal('0'),
            "discount_display": None,
            "message": None,
            "recoverable": False,
            "is_applied": False,
            "min_total": None,
            "min_total_display": None,
            "instance": None,
        }
    promo = PromoCode.objects.filter(code__iexact=code).first()
    if not promo:
        _clear_promo_code(request)
        return {
            "code": code,
            "description": "",
            "discount": Decimal('0'),
            "discount_display": None,
            "message": "Промокод не найден.",
            "recoverable": False,
            "is_applied": False,
            "min_total": None,
            "min_total_display": None,
            "instance": None,
        }
    discount, message, recoverable = _evaluate_promo(promo, subtotal)
    is_applied = discount > 0 and not message
    return {
        "code": promo.code,
        "description": promo.description,
        "discount": discount,
        "discount_display": f"-{_format_currency(discount)}" if discount > 0 else None,
        "message": message,
        "recoverable": recoverable,
        "is_applied": is_applied,
        "min_total": promo.min_order_total,
        "min_total_display": _format_currency(promo.min_order_total) if promo.min_order_total else None,
        "instance": promo if is_applied else (promo if recoverable else None),
    }


def _promo_payload(state):
    if not state:
        return None
    return {
        "code": state.get("code"),
        "description": state.get("description"),
        "discount": str(state.get("discount") or Decimal('0')),
        "discount_display": state.get("discount_display"),
        "message": state.get("message"),
        "recoverable": state.get("recoverable"),
        "is_applied": state.get("is_applied"),
        "min_total_display": state.get("min_total_display"),
    }


def _cart_queryset(user):
    return CartItem.objects.filter(user=user).select_related(
        'product_variant__product',
        'product_variant__color',
        'product_variant__size'
    ).prefetch_related(
        'product_variant__images',
        'product_variant__product__images'
    )


def _favorite_product_ids(user):
    if Favorite is None or not getattr(user, 'is_authenticated', False):
        return set()
    return set(Favorite.objects.filter(user=user).values_list('product_id', flat=True))


def _variant_image_url(variant):
    if variant is None:
        return PLACEHOLDER_IMAGE
    getter = getattr(variant, 'get_primary_image_url', None)
    if callable(getter):
        url = getter()
        if url:
            return url
    product = getattr(variant, 'product', None)
    if product and hasattr(product, 'images'):
        legacy = product.images.first()
        if legacy and legacy.image_url:
            return legacy.image_url
    return PLACEHOLDER_IMAGE


def _store_key(store):
    store_id = getattr(store, 'store_id', None)
    return str(store_id) if store_id is not None else "virtual-store"


def _store_details(store):
    name = getattr(store, 'name', None) or "Бутик Lumiere Secrète"
    address = getattr(store, 'address', None)
    city = (getattr(address, 'city', '') or '').strip() if address else ''
    street = (getattr(address, 'street', '') or '').strip() if address else ''
    location = ", ".join(part for part in [city, street] if part)
    display = f"{name} — {location}" if location else name
    return {
        "name": name,
        "city": city,
        "street": street,
        "display": display,
    }


def _store_label(store):
    return _store_details(store)["display"]


def _cart_items_and_total(user):
    if CartItem is None:
        return [], Decimal('0')
    items = []
    total = Decimal('0')
    favorite_ids = _favorite_product_ids(user)
    for it in _cart_queryset(user):
        variant = getattr(it, 'product_variant', None)
        product = getattr(variant, 'product', None)
        store = getattr(variant, 'store', None)
        price = it.price or getattr(variant, 'price', Decimal('0'))
        line_total = (price or Decimal('0')) * (it.quantity or 0)
        total += line_total
        product_id = getattr(product, 'product_id', getattr(product, 'id', None))
        detail_url = reverse('product_detail', args=[product_id]) if product_id else None
        favorite_url = reverse('favorite_toggle', args=[product_id]) if product_id else None
        items.append({
            "id": it.pk,
            "name": getattr(product, 'name', str(variant)),
            "price": price,
            "price_display": _format_currency(price),
            "quantity": it.quantity,
            "line_total": line_total,
            "line_total_display": _format_currency(line_total),
            "photo": _variant_image_url(variant),
            "color": getattr(getattr(variant, 'color', None), 'name_color', ''),
            "size": getattr(getattr(variant, 'size', None), 'size', ''),
            "store_label": _store_label(store),
            "detail_url": detail_url,
            "favorite_url": favorite_url,
            "is_favorite": product_id in favorite_ids,
            "update_url": reverse('cart_update', args=[it.pk]),
            "remove_url": reverse('remove_from_cart', args=[it.pk]),
        })
    return items, total


def _cart_totals(subtotal, promo_state=None):
    shipping = Decimal('0')
    discount = Decimal('0')
    promo_code = None
    if promo_state:
        discount = promo_state.get('discount') or Decimal('0')
        promo_code = promo_state.get('code')
    subtotal = subtotal or Decimal('0')
    discount = min(discount, subtotal)
    total = max(Decimal('0'), subtotal - discount + shipping)
    data = {
        "subtotal": str(subtotal),
        "subtotal_display": _format_currency(subtotal),
        "shipping": str(shipping),
        "shipping_display": "Бесплатно" if shipping == 0 else _format_currency(shipping),
        "total": str(total),
        "total_display": _format_currency(total),
        "discount": str(discount),
        "discount_display": f"-{_format_currency(discount)}" if discount > 0 else None,
        "promo_code": promo_code,
    }
    return data


@login_required(login_url='accounts:login')
@require_http_methods(['GET'])
def cart_list(request):
    if CartItem is None:
        subtotal = Decimal('0')
        promo_state = _resolve_cart_promo(request, subtotal)
        totals = _cart_totals(subtotal, promo_state)
        empty = {
            "items": [],
            "cart_summary": totals,
            "placeholder_image": PLACEHOLDER_IMAGE,
            "undo_url": reverse('cart_undo'),
            "promo": promo_state,
        }
        payload = {"items": [], "totals": totals, "promo": _promo_payload(promo_state)}
        return JsonResponse(payload) if _wants_json(request) else render(request, 'cart/cart_view.html', empty)
    items, subtotal = _cart_items_and_total(request.user)
    promo_state = _resolve_cart_promo(request, subtotal)
    totals = _cart_totals(subtotal, promo_state)
    if _wants_json(request):
        return JsonResponse({
            "items": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "price": str(item["price"]) if item["price"] is not None else None,
                    "quantity": item["quantity"],
                    "line_total": str(item["line_total"]),
                    "line_total_display": item["line_total_display"],
                } for item in items
            ],
            "totals": totals,
            "promo": _promo_payload(promo_state),
        })
    return render(request, 'cart/cart_view.html', {
        "items": items,
        "cart_summary": totals,
        "promo": promo_state,
        "placeholder_image": PLACEHOLDER_IMAGE,
        "undo_url": reverse('cart_undo'),
    })


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def cart_apply_promo(request):
    is_json = request.headers.get('content-type') == 'application/json'
    if is_json:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = request.POST

    action = payload.get('intent', 'apply')
    destination = payload.get('next', 'cart')
    redirect_url = reverse('checkout') if destination == 'checkout' else reverse('view_cart')
    _, subtotal = _cart_items_and_total(request.user)

    def _respond(message, level='info', status_code=200):
        promo_state = _resolve_cart_promo(request, subtotal)
        totals = _cart_totals(subtotal, promo_state)
        payload = {
            "message": message,
            "totals": totals,
            "promo": _promo_payload(promo_state),
        }
        if _wants_json(request):
            return JsonResponse(payload, status=status_code)
        if level == 'success':
            messages.success(request, message)
        elif level == 'error':
            messages.error(request, message)
        else:
            messages.info(request, message)
        return redirect(redirect_url)

    if action == 'clear':
        _clear_promo_code(request)
        return _respond("Промокод удалён.")

    code = (payload.get('promo') or payload.get('code') or payload.get('promo_code') or '').strip()
    if not code:
        return _respond("Введите промокод.", level='error', status_code=400)
    if subtotal <= 0:
        _clear_promo_code(request)
        return _respond("Добавьте товары в корзину, чтобы применить промокод.", level='error', status_code=400)

    promo = PromoCode.objects.filter(code__iexact=code).first()
    if not promo:
        _clear_promo_code(request)
        return _respond("Промокод не найден.", level='error', status_code=404)

    discount, message, recoverable = _evaluate_promo(promo, subtotal)
    if message and not recoverable:
        _clear_promo_code(request)
        return _respond(message, level='error', status_code=400)

    _store_promo_code(request, promo.code)
    promo_state = _resolve_cart_promo(request, subtotal)
    totals = _cart_totals(subtotal, promo_state)
    payload = {
        "message": message or f"Промокод {promo.code} применён.",
        "totals": totals,
        "promo": _promo_payload(promo_state),
    }
    if _wants_json(request):
        status_code = 200 if not message else 202
        return JsonResponse(payload, status=status_code)
    if message:
        messages.info(request, message)
    else:
        saved_discount = promo_state.get('discount_display')
        suffix = f" {saved_discount}" if saved_discount else ""
        messages.success(request, f"Промокод {promo.code} применён.{suffix}")
    return redirect(redirect_url)


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def cart_add(request):
    if CartItem is None or ProductVariant is None:
        return HttpResponseNotFound("Cart model not available")

    is_json = request.headers.get('content-type') == 'application/json'
    if is_json:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Bad request body")
    else:
        payload = request.POST

    pv_id = payload.get("product_variant_id") or payload.get("variant")
    quantity = payload.get("quantity", 1)
    try:
        quantity = max(1, int(quantity))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid quantity")

    pv = ProductVariant.objects.filter(product_variant_id=pv_id).first() or ProductVariant.objects.filter(pk=pv_id).first()
    if pv is None:
        return HttpResponseBadRequest("Variant not found")

    obj, created = CartItem.objects.get_or_create(
        user=request.user,
        product_variant=pv,
        defaults={"quantity": quantity, "price": getattr(pv, "price", None)}
    )
    if not created:
        obj.quantity = (obj.quantity or 0) + quantity
        obj.price = getattr(pv, "price", obj.price)
        obj.save()

    if is_json or _wants_json(request):
        _, subtotal = _cart_items_and_total(request.user)
        promo_state = _resolve_cart_promo(request, subtotal)
        totals = _cart_totals(subtotal, promo_state)
        line_total = (obj.price or Decimal('0')) * (obj.quantity or 0)
        return JsonResponse({
            "id": obj.pk,
            "quantity": obj.quantity,
            "created": created,
            "line_total": str(line_total),
            "totals": totals,
            "promo": _promo_payload(promo_state),
        })

    messages.success(request, "Товар добавлен в корзину.")
    return redirect('view_cart')


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def cart_update(request, item_id=None):
    if CartItem is None:
        return HttpResponseNotFound("Cart model not available")
    obj = CartItem.objects.filter(pk=item_id, user=request.user).first()
    if obj is None:
        return HttpResponseNotFound("Item not found")
    is_json = request.headers.get('content-type') == 'application/json'
    if is_json:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Bad request body")
        quantity = payload.get('quantity')
    else:
        quantity = request.POST.get('quantity')
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid quantity")
    if quantity <= 0:
        obj.delete()
        if is_json or _wants_json(request):
            _, subtotal = _cart_items_and_total(request.user)
            promo_state = _resolve_cart_promo(request, subtotal)
            totals = _cart_totals(subtotal, promo_state)
            return JsonResponse({
                "deleted": True,
                "totals": totals,
                "promo": _promo_payload(promo_state),
            })
        messages.info(request, "Товар удалён из корзины.")
        return redirect('view_cart')
    obj.quantity = quantity
    obj.save()
    if is_json or _wants_json(request):
        _, subtotal = _cart_items_and_total(request.user)
        promo_state = _resolve_cart_promo(request, subtotal)
        totals = _cart_totals(subtotal, promo_state)
        line_total = (obj.price or Decimal('0')) * obj.quantity
        return JsonResponse({
            "updated": True,
            "item": {
                "id": obj.pk,
                "quantity": obj.quantity,
                "line_total": str(line_total),
                "line_total_display": _format_currency(line_total),
            },
            "totals": totals,
            "promo": _promo_payload(promo_state),
        })
    messages.success(request, "Количество обновлено.")
    return redirect('view_cart')


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def cart_remove(request, item_id=None):
    if CartItem is None:
        return HttpResponseNotFound("Cart model not available")
    obj = CartItem.objects.filter(pk=item_id, user=request.user).first()
    if obj is None:
        return HttpResponseNotFound("Item not found")
    undo_token = None
    if ProductVariant is not None:
        undo_payload = {
            "variant_id": getattr(obj.product_variant, 'product_variant_id', None),
            "quantity": obj.quantity,
            "price": str(obj.price or getattr(obj.product_variant, 'price', Decimal('0'))),
        }
        undo_token = f"{obj.pk}-{timezone.now().timestamp()}"
        store = request.session.get('cart_undo', {})
        store[undo_token] = undo_payload
        request.session['cart_undo'] = store
        request.session.modified = True
    obj.delete()
    if _wants_json(request):
        _, subtotal = _cart_items_and_total(request.user)
        promo_state = _resolve_cart_promo(request, subtotal)
        totals = _cart_totals(subtotal, promo_state)
        return JsonResponse({
            "deleted": True,
            "totals": totals,
            "promo": _promo_payload(promo_state),
            "undo_token": undo_token,
        })
    messages.info(request, "Товар удалён из корзины.")
    return redirect('view_cart')


@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def cart_undo(request):
    if CartItem is None or ProductVariant is None:
        return HttpResponseBadRequest("Cart unavailable")
    is_json = request.headers.get('content-type') == 'application/json'
    if is_json:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = request.POST
    token = payload.get('token')
    if not token:
        return HttpResponseBadRequest("Missing token")
    undo_store = request.session.get('cart_undo', {})
    data = undo_store.pop(token, None)
    request.session['cart_undo'] = undo_store
    request.session.modified = True
    if data is None:
        if _wants_json(request):
            return JsonResponse({"restored": False}, status=400)
        messages.info(request, "Истекло время на отмену.")
        return redirect('view_cart')
    variant_id = data.get('variant_id')
    variant = ProductVariant.objects.filter(product_variant_id=variant_id).first() or ProductVariant.objects.filter(pk=variant_id).first()
    if variant is None:
        if _wants_json(request):
            return JsonResponse({"restored": False}, status=400)
        messages.info(request, "Не удалось вернуть товар.")
        return redirect('view_cart')
    try:
        quantity = max(1, int(data.get('quantity', 1)))
    except (TypeError, ValueError):
        quantity = 1
    try:
        price = Decimal(data.get('price'))
    except (TypeError, InvalidOperation):
        price = getattr(variant, 'price', Decimal('0'))
    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product_variant=variant,
        defaults={"quantity": quantity, "price": price}
    )
    if not created:
        item.quantity = (item.quantity or 0) + quantity
        item.price = price
        item.save()
    _, subtotal = _cart_items_and_total(request.user)
    promo_state = _resolve_cart_promo(request, subtotal)
    totals = _cart_totals(subtotal, promo_state)
    if _wants_json(request):
        line_total = (item.price or Decimal('0')) * item.quantity
        return JsonResponse({
            "restored": True,
            "item": {
                "id": item.pk,
                "quantity": item.quantity,
                "line_total": str(line_total),
                "line_total_display": _format_currency(line_total),
            },
            "totals": totals,
            "promo": _promo_payload(promo_state),
        })
    messages.success(request, "Вернули товар в корзину.")
    return redirect('view_cart')

@login_required(login_url='accounts:login')
@require_http_methods(['POST'])
def cart_clear(request):
    if CartItem is None:
        return HttpResponseNotFound("Cart model not available")
    qs = CartItem.objects.filter(user=request.user)
    cleared = qs.count()
    qs.delete()
    if _wants_json(request):
        return JsonResponse({"cleared": cleared})
    if cleared:
        messages.info(request, "Корзина очищена.")
    else:
        messages.info(request, "В корзине уже пусто.")
    return redirect('view_cart')


def add_to_cart(request):
    return cart_add(request)


def remove_from_cart(request, item_id=None):
    return cart_remove(request, item_id=item_id)


def view_cart(request):
    return cart_list(request)


def get_cart(request):
    return cart_list(request)


@login_required(login_url='accounts:login')
def checkout(request):
    if CartItem is None:
        return HttpResponseNotFound("Cart model not available")
    items = CartItem.objects.filter(user=request.user).select_related(
        'product_variant__product',
        'product_variant__color',
        'product_variant__size'
    ).prefetch_related(
        'product_variant__images',
        'product_variant__product__images'
    )
    summary = []
    total = Decimal('0')
    store_entries = {}
    for it in items:
        line_total = (it.price or Decimal('0')) * (it.quantity or 0)
        total += line_total
        variant = it.product_variant
        store = getattr(variant, 'store', None)
        store_key = _store_key(store)
        if store_key not in store_entries:
            details = _store_details(store)
            store_entries[store_key] = {
                "id": store_key,
                "name": details["name"],
                "display": details["display"],
                "city": details["city"],
                "street": details["street"],
                "store": store,
            }
        product = getattr(variant, 'product', None)
        product_id = getattr(product, 'product_id', getattr(product, 'pk', None))
        summary.append({
            "name": str(product or variant),
            "color": getattr(getattr(variant, 'color', None), 'name_color', ''),
            "size": getattr(getattr(variant, 'size', None), 'size', ''),
            "price": it.price,
            "price_display": _format_currency(it.price) if it.price is not None else None,
            "quantity": it.quantity,
            "photo": _variant_image_url(variant),
            "item_id": it.pk,
            "store_label": store_entries[store_key]["display"],
            "line_total": line_total,
            "line_total_display": _format_currency(line_total),
            "update_url": reverse('cart_update', args=[it.pk]),
            "remove_url": reverse('remove_from_cart', args=[it.pk]),
            "detail_url": reverse('product_detail', args=[product_id]) if product_id else None,
        })

    promo_state = _resolve_cart_promo(request, total)
    cart_summary = _cart_totals(total, promo_state)

    if not store_entries:
        fallback_entry = {
            "id": "virtual-store",
            "name": "Бутик Lumiere Secrète",
            "display": "Бутик Lumiere Secrète, Москва",
            "city": "",
            "street": "",
            "store": None,
        }
        store_entries[fallback_entry["id"]] = fallback_entry
    pickup_choices = list(store_entries.values())
    pickup_lookup = {entry["id"]: entry for entry in pickup_choices}
    real_store_ids = {entry["id"] for entry in pickup_choices if entry["store"] is not None}
    if summary and len(real_store_ids) > 1:
        messages.error(request, "В корзине есть товары из нескольких бутиков. Пожалуйста, оформите отдельный заказ для каждого бутика.")
        return redirect('view_cart')
    default_pickup_id = pickup_choices[0]["id"] if pickup_choices else ""

    saved_card = request.session.get('checkout_card', {})
    form_data = {
        "first_name": getattr(request.user, 'first_name', '') or '',
        "last_name": getattr(request.user, 'last_name', '') or '',
        "phone": getattr(request.user, 'phone', '') if hasattr(request.user, 'phone') else '',
        "address": "",
        "city": "",
        "comment": "",
        "shipping_method": "delivery",
        "pickup_location": default_pickup_id,
        "payment_flow": "now",
        "delivery_payment_method": "card_on_delivery",
        "card_number": saved_card.get("card_number", ""),
        "card_holder": saved_card.get("card_holder", ""),
        "card_expiry": saved_card.get("card_expiry", ""),
        "card_cvv": "",
    }
    form_errors = []
    card_number_raw = ""

    if request.method == 'POST':
        if not summary:
            messages.info(request, "Корзина пуста для оформления.")
            return redirect('view_cart')

        for field in ["first_name", "last_name", "phone", "address", "city", "comment", "shipping_method", "pickup_location"]:
            form_data[field] = request.POST.get(field, '').strip()

        form_data["payment_flow"] = request.POST.get('payment_flow', 'now').strip()
        form_data["delivery_payment_method"] = request.POST.get('delivery_payment_method', 'card_on_delivery').strip()
        form_data["card_number"] = request.POST.get('card_number', '').strip()
        form_data["card_holder"] = request.POST.get('card_holder', '').strip()
        form_data["card_expiry"] = request.POST.get('card_expiry', '').strip()
        form_data["card_cvv"] = request.POST.get('card_cvv', '').strip()
        selected_pickup_entry = pickup_lookup.get(form_data["pickup_location"])

        payment_flow = form_data["payment_flow"] if form_data["payment_flow"] in ("now", "later") else "now"
        form_data["payment_flow"] = payment_flow
        delivery_payment_method = form_data["delivery_payment_method"] if form_data["delivery_payment_method"] in ("card_on_delivery", "cash_on_delivery") else "card_on_delivery"
        form_data["delivery_payment_method"] = delivery_payment_method

        card_number_raw = form_data["card_number"].replace(' ', '').replace('-', '')
        if card_number_raw:
            grouped = ' '.join(card_number_raw[i:i+4] for i in range(0, len(card_number_raw), 4)).strip()
            form_data["card_number"] = grouped
        card_holder = form_data["card_holder"].upper()
        form_data["card_holder"] = card_holder
        card_expiry = form_data["card_expiry"]
        card_cvv = form_data["card_cvv"]

        if not form_data["first_name"]:
            form_errors.append("Укажите имя.")
        if not form_data["last_name"]:
            form_errors.append("Укажите фамилию.")

        if form_data["shipping_method"] not in ("delivery", "pickup"):
            form_data["shipping_method"] = "delivery"

        if form_data["shipping_method"] == "delivery":
            if not form_data["address"]:
                form_errors.append("Укажите адрес доставки.")
            if not form_data["city"]:
                form_errors.append("Укажите город доставки.")
        else:
            if not selected_pickup_entry:
                form_errors.append("Выберите точку самовывоза.")
            else:
                form_data["address"] = selected_pickup_entry["display"]
                form_data["city"] = selected_pickup_entry["city"] or "Самовывоз"

        raw_phone = re.sub(r'\D', '', form_data["phone"])
        if raw_phone.startswith('8'):
            raw_phone = '7' + raw_phone[1:]
        if not raw_phone:
            form_errors.append("Укажите телефон.")
        elif not raw_phone.startswith('7'):
            form_errors.append("Телефон должен начинаться с +7.")
        elif len(raw_phone) != 11:
            form_errors.append("Номер телефона должен содержать 10 цифр после +7.")
        else:
            rest = raw_phone[1:]
            formatted_phone = "+7"
            if rest:
                formatted_phone += f" {rest[:3]}"
            if len(rest) > 3:
                formatted_phone += f" {rest[3:6]}"
            if len(rest) > 6:
                formatted_phone += f"-{rest[6:8]}"
            if len(rest) > 8:
                formatted_phone += f"-{rest[8:10]}"
            form_data["phone"] = formatted_phone

        if payment_flow == "now":
            if not card_holder:
                form_errors.append("Укажите владельца карты.")
            if not card_number_raw.isdigit() or not 12 <= len(card_number_raw) <= 19:
                form_errors.append("Введите корректный номер карты.")
            expiry_match = re.match(r'^(0[1-9]|1[0-2])/(\d{2})$', card_expiry)
            if not expiry_match:
                form_errors.append("Введите срок действия в формате ММ/ГГ.")
            else:
                month = int(expiry_match.group(1))
                year = int(expiry_match.group(2)) + 2000
                expiry_edge = datetime(year, month, 1)
                current_edge = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if expiry_edge < current_edge:
                    form_errors.append("Срок действия карты истёк.")
            if not card_cvv.isdigit() or len(card_cvv) not in (3, 4):
                form_errors.append("CVV должен состоять из 3–4 цифр.")
        else:
            card_number_raw = ""
            form_data["card_number"] = ""
            form_data["card_holder"] = ""
            form_data["card_expiry"] = ""
            form_data["card_cvv"] = ""

        if form_errors:
            return render(request, 'cart/checkout.html', {
                "items": summary,
                "total": total,
                "form_data": form_data,
                "form_errors": form_errors,
                "pickup_choices": pickup_choices,
                "cart_summary": cart_summary,
                "promo": promo_state,
            })

        status_obj, _ = Status.objects.get_or_create(name_status='В обработке')
        selected_pickup_entry = selected_pickup_entry or pickup_choices[0]
        order_store = selected_pickup_entry["store"] if selected_pickup_entry else None
        meta_string = timezone.localtime().strftime("%Y-%m-%d %H:%M")
        meta_pairs = {
            "Имя": form_data["first_name"],
            "Фамилия": form_data["last_name"],
            "Телефон": form_data["phone"],
            "Адрес": form_data["address"],
            "Город": form_data["city"],
            "Комментарий": form_data["comment"],
            "Доставка": "Самовывоз" if form_data["shipping_method"] == "pickup" else "Доставка",
        }
        if selected_pickup_entry and selected_pickup_entry.get("display"):
            meta_pairs["Бутик"] = selected_pickup_entry["display"]
        for label, value in meta_pairs.items():
            if value:
                meta_string += f" | {label}: {value}"

        order = Order.objects.create(
            user=request.user,
            status=status_obj,
            total_amount=Decimal('0'),
            created_at=meta_string,
            store=order_store
        )
        running_total = Decimal('0')
        for it in items:
            price = it.price or Decimal('0')
            OrderItem.objects.create(
                order=order,
                product_variant=it.product_variant,
                quantity=it.quantity,
                price=price
            )
            running_total += price * (it.quantity or 0)
        promo_for_order = promo_state or _resolve_cart_promo(request, running_total)
        discount_value = promo_for_order.get('discount') if promo_for_order.get('is_applied') else Decimal('0')
        promo_instance = promo_for_order.get('instance') if promo_for_order.get('is_applied') else None
        discount_value = min(discount_value or Decimal('0'), running_total)
        payable_total = max(Decimal('0'), running_total - discount_value)
        order.total_amount = payable_total
        order.discount_amount = discount_value
        order.promo_code = promo_instance
        order.save()
        if promo_instance:
            promo_instance.register_use()

        if payment_flow == "now":
            masked_last = card_number_raw[-4:] if card_number_raw else ""
            label_suffix = f" ••••{masked_last}" if masked_last else ""
            payment_label = f"Онлайн оплата картой{label_suffix}"
            payment_status = "В обработке"
            request.session['checkout_card'] = {
                "card_number": form_data["card_number"],
                "card_holder": form_data["card_holder"],
                "card_expiry": form_data["card_expiry"],
            }
            request.session.modified = True
        else:
            if delivery_payment_method == "cash_on_delivery":
                payment_label = "Оплата при получении (наличные)"
            else:
                payment_label = "Оплата при получении (карта)"
            payment_status = "Ожидает оплаты"

        Payment.objects.create(
            order=order,
            method=payment_label,
            amount=payable_total,
            status=payment_status
        )

        items.delete()
        _clear_promo_code(request)
        messages.success(request, f"Спасибо! Ваш заказ №{order.order_id} принят.")
        return redirect('orders:order_history')

    return render(request, 'cart/checkout.html', {
        "items": summary,
        "total": total,
        "form_data": form_data,
        "form_errors": form_errors,
        "pickup_choices": pickup_choices,
        "cart_summary": cart_summary,
        "promo": promo_state,
    })


def checkout_view(request):
    return checkout(request)


def end_checkout(request):
    return checkout(request)
