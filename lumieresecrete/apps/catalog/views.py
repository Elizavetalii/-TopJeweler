from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Min, Q
from django.http import JsonResponse, HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ProductReviewForm

try:
    from .models import Product, Category, ProductImage, Favorite, ProductReview
except Exception:
    Product = None
    Category = None
    ProductImage = None
    Favorite = None
    ProductReview = None

try:
    from apps.product_variants.models import ProductVariant, Colors, Sizes
except Exception:
    ProductVariant = None
    Colors = None
    Sizes = None

try:
    from apps.stores.models import Store
except Exception:
    Store = None

try:
    from apps.cart.models import CartItem
except Exception:
    CartItem = None

try:
    from apps.orders.models import OrderItem
except Exception:
    OrderItem = None

try:
    from apps.accounts.models import UserSettings
except Exception:
    UserSettings = None

PALETTE = {
    "cream": "#F1ECE6",
    "sand": "#DDD5CD",
    "taupe": "#B6A697",
    "wine": "#7D4047",
    "charcoal": "#2E2E2E",
}
PLACEHOLDER_IMAGE = "https://placehold.co/600x400/F1ECE6/2E2E2E?text=Lumiere"


def _product_gallery_payload(product, include_placeholder=False):
    gallery = []
    if ProductImage is not None and hasattr(product, 'images'):
        for idx, image in enumerate(product.images.all()):
            url = getattr(image, 'image_url', None)
            if not url:
                continue
            gallery.append({
                "id": getattr(image, 'image_id', None),
                "url": url,
                "alt": image.alt_text or getattr(product, 'name', ''),
                "is_primary": idx == 0,
            })
    if include_placeholder and not gallery:
        gallery.append({
            "id": None,
            "url": PLACEHOLDER_IMAGE,
            "alt": getattr(product, 'name', ''),
            "is_primary": True,
        })
    return gallery

def _session_wishlist_ids(request):
    ids = []
    for value in request.session.get("wishlist", []):
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _sync_favorite_ids(request):
    session_ids = _session_wishlist_ids(request)
    if request.user.is_authenticated and Favorite is not None and Product is not None:
        if session_ids:
            products = Product.objects.filter(product_id__in=session_ids)
            for product in products:
                Favorite.objects.get_or_create(user=request.user, product=product)
            request.session.pop("wishlist", None)
            request.session.modified = True
        return set(Favorite.objects.filter(user=request.user).values_list('product_id', flat=True))
    return set(session_ids)


def _clear_favorites(request, product_ids=None):
    if request.user.is_authenticated and Favorite is not None:
        qs = Favorite.objects.filter(user=request.user)
        if product_ids is not None:
            qs = qs.filter(product__product_id__in=product_ids)
        deleted, _ = qs.delete()
        return deleted
    wishlist = _session_wishlist_ids(request)
    if product_ids is not None:
        keep = [pid for pid in wishlist if pid not in set(product_ids)]
    else:
        keep = []
    removed = len(wishlist) - len(keep)
    request.session["wishlist"] = keep
    request.session.modified = True
    return removed


def _serialize_variant(variant, fallback_name="Универсальный", fallback_gallery=None):
    color = getattr(variant, "color", None)
    size = getattr(variant, "size", None)
    store = getattr(variant, "store", None)
    color_id = getattr(color, "gemstone_id", None)
    size_id = getattr(size, "size_id", None)
    image_payload = variant.get_image_payload(fallback=False)
    if not image_payload and fallback_gallery:
        image_payload = [dict(item) for item in fallback_gallery]
    primary_image = None
    for image in image_payload:
        if image.get("is_primary"):
            primary_image = image.get("url")
            break
    if not primary_image and image_payload:
        primary_image = image_payload[0].get("url")
    return {
        "id": getattr(variant, "product_variant_id", getattr(variant, "id", None)),
        "price": getattr(variant, "price", None),
        "color_id": color_id or f"default-{getattr(variant, 'product_variant_id', '')}",
        "color_name": getattr(color, "name_color", fallback_name),
        "color_code": getattr(color, "color_code", "#b6a697"),
        "size_id": size_id or f"size-{getattr(variant, 'product_variant_id', '')}",
        "size_label": getattr(size, "size", "One Size"),
        "quantity": getattr(variant, "quantity", 0) or 0,
        "structure": getattr(variant, "structure", ""),
        "store_id": getattr(store, "store_id", None),
        "store": getattr(store, "name", "Lumiere Secrète"),
        "primary_image": primary_image,
        "images": image_payload,
        "is_available": (getattr(variant, "quantity", 0) or 0) > 0,
    }


def _collect_variant_data(product):
    if ProductVariant is None:
        return [], [], [], [], None
    payload = []
    colors = {}
    sizes = {}
    stores = {}
    fallback_gallery = _product_gallery_payload(product)
    def _store_key(store_id, store_name):
        if store_id is not None:
            return str(store_id)
        normalized = (store_name or "Lumiere Secrète").strip().lower()
        return f"name:{normalized or 'default'}"
    queryset = ProductVariant.objects.filter(product=product).select_related('color', 'size', 'store').prefetch_related('images')
    for variant in queryset:
        data = _serialize_variant(variant, fallback_name=product.name, fallback_gallery=fallback_gallery)
        store_key = _store_key(data.get("store_id"), data.get("store"))
        data["store_key"] = store_key
        payload.append(data)
        color_key = data["color_id"]
        if color_key not in colors:
            colors[color_key] = {
                "id": color_key,
                "name": data["color_name"],
                "code": data["color_code"],
                "in_stock": data["is_available"],
            }
        else:
            colors[color_key]["in_stock"] = colors[color_key]["in_stock"] or data["is_available"]
        size_key = data["size_id"]
        if size_key not in sizes:
            sizes[size_key] = {
                "id": size_key,
                "label": data["size_label"],
                "in_stock": data["is_available"],
            }
        else:
            sizes[size_key]["in_stock"] = sizes[size_key]["in_stock"] or data["is_available"]
        if store_key not in stores:
            stores[store_key] = {
                "id": store_key,
                "label": data.get("store") or "Lumiere Secrète",
                "in_stock": data["is_available"],
            }
        else:
            stores[store_key]["in_stock"] = stores[store_key]["in_stock"] or data["is_available"]
    selected = next((entry for entry in payload if entry["is_available"]), payload[0] if payload else None)
    return payload, list(colors.values()), list(sizes.values()), list(stores.values()), selected


def _product_to_dict(p):
    try:
        return {
            "id": getattr(p, "product_id", getattr(p, "id", None)),
            "name": getattr(p, "name", None),
        }
    except Exception:
        return {"id": None, "name": None}

def catalog_list(request):
    wants_partial = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('partial') == '1'
    if Product is None:
        empty = {"products": []}
        if wants_partial:
            return JsonResponse(empty)
        return render(request, "catalog/catalog_list.html", {
            "products_page": [],
            "filters": {},
        })

    query_params = request.GET.copy()
    search_query = query_params.get("q", "").strip()
    category_param = query_params.getlist("category")
    color_param = [cid for value in query_params.getlist("color") for cid in value.split(",") if value]
    size_param = [sid for value in query_params.getlist("size") for sid in value.split(",") if value]
    store_param = [sid for value in query_params.getlist("store") for sid in value.split(",") if value]
    structure_param = [st for value in query_params.getlist("structure") for st in value.split(",") if value]
    in_stock = query_params.get("in_stock")
    price_min_qs = query_params.get("price_min")
    price_max_qs = query_params.get("price_max")
    sort = query_params.get("sort", "newest")

    products = Product.objects.all().prefetch_related(
        'images',
        'variants__color',
        'variants__size',
        'variants__store',
        'variants__images'
    ).annotate(
        popularity=Count('variants__orderitem', distinct=True),
        latest_variant=Max('variants__product_variant_id')
    )

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(variants__description__icontains=search_query)
        )

    if category_param:
        products = products.filter(category__category_id__in=category_param)

    if color_param:
        products = products.filter(variants__color__gemstone_id__in=color_param)

    if size_param:
        products = products.filter(variants__size__size_id__in=size_param)

    if store_param:
        products = products.filter(variants__store__store_id__in=store_param)

    if structure_param:
        products = products.filter(variants__structure__in=structure_param)

    if in_stock == '1':
        products = products.filter(variants__quantity__gt=0)

    def _safe_decimal(value):
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            return None

    price_bounds = ProductVariant.objects.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    price_min = _safe_decimal(price_min_qs)
    price_max = _safe_decimal(price_max_qs)
    if price_min is not None:
        products = products.filter(variants__price__gte=price_min)
    if price_max is not None:
        products = products.filter(variants__price__lte=price_max)

    sort_map = {
        'price_asc': 'variants__price',
        'price_desc': '-variants__price',
        'popular': '-popularity',
        'newest': '-latest_variant',
    }
    order_field = sort_map.get(sort, '-latest_variant')
    products = products.order_by(order_field, '-product_id').distinct()

    per_page = _user_page_size(request, 24)
    paginator = Paginator(products, per_page)
    page_number = query_params.get('page')
    page_obj = paginator.get_page(page_number)

    favorite_ids = _sync_favorite_ids(request)

    newest_ids = list(
        Product.objects.order_by('-product_id').values_list('product_id', flat=True)[:5]
    )

    product_cards = []
    for product in page_obj.object_list:
        variants = list(product.variants.all())
        prices = [v.price for v in variants if v.price is not None]
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        swatches = []
        for v in variants:
            color = getattr(v, 'color', None)
            if color:
                swatch = {
                    "name": color.name_color,
                    "code": color.color_code or "#7d4047",
                }
                if swatch not in swatches:
                    swatches.append(swatch)
        size_labels = sorted({getattr(v.size, 'size', '') for v in variants if v.size})
        structures = sorted({(v.structure or '').strip() for v in variants if v.structure})
        flat_images = []
        for v in variants:
            flat_images.extend(v.get_image_payload(fallback=False))
        if not flat_images:
            flat_images = _product_gallery_payload(product, include_placeholder=True)
        primary_photo = next((img["url"] for img in flat_images if img.get("is_primary")), None)
        if not primary_photo and flat_images:
            primary_photo = flat_images[0].get("url")
        if not primary_photo:
            primary_photo = PLACEHOLDER_IMAGE
        hover_photo = None
        if len(flat_images) > 1:
            hover_photo = next((img["url"] for img in flat_images if img.get("url") != primary_photo), None)
        hover_photo = hover_photo or primary_photo
        has_sale = any(v.previous_price and v.previous_price > v.price for v in variants)
        is_new = product.product_id in newest_ids
        in_stock_flag = any((v.quantity or 0) > 0 for v in variants)
        product_cards.append({
            "id": product.product_id,
            "name": product.name,
            "category": getattr(product.category, "name", "Без категории"),
            "price_min": min_price,
            "price_max": max_price,
            "photo": primary_photo,
            "hover_photo": hover_photo,
            "colors": swatches[:6],
            "sizes": size_labels[:6],
            "structures": structures,
            "is_new": is_new,
            "has_sale": has_sale,
            "in_stock": in_stock_flag,
            "favorite_url": reverse('favorite_toggle', args=[product.product_id]),
            "quick_view_url": reverse('product_detail', args=[product.product_id]),
            "detail_url": reverse('product_detail', args=[product.product_id]),
            "is_favorite": product.product_id in favorite_ids,
        })

    structure_values = set()
    if ProductVariant is not None:
        for value in ProductVariant.objects.exclude(structure__isnull=True).values_list('structure', flat=True):
            if value:
                structure_values.add(value.strip())

    size_groups = []
    if ProductVariant is not None and Category is not None and Sizes is not None:
        group_map = {}
        size_rows = ProductVariant.objects.filter(size__isnull=False).values(
            'product__category__category_id',
            'product__category__name',
            'size__size_id',
            'size__size',
        ).distinct()
        for row in size_rows:
            cat_id = row['product__category__category_id']
            cat_key = str(cat_id) if cat_id is not None else 'none'
            group = group_map.setdefault(cat_key, {
                "category_id": cat_id,
                "category_name": row['product__category__name'] or "Без категории",
                "sizes": [],
            })
            if not any(size['size_id'] == row['size__size_id'] for size in group["sizes"]):
                group["sizes"].append({
                    "size_id": row['size__size_id'],
                    "size": row['size__size'],
                })
        for group in group_map.values():
            group["sizes"].sort(key=lambda item: (item["size"] or "").lower())
        size_groups = sorted(group_map.values(), key=lambda item: (item["category_name"] or "").lower())

    filters_data = {
        "categories": Category.objects.all().order_by('name') if Category else [],
        "colors": Colors.objects.all().order_by('name_color') if Colors else [],
        "sizes": Sizes.objects.all().order_by('size') if Sizes else [],
        "size_groups": size_groups,
        "stores": Store.objects.all().order_by('name') if Store else [],
        "structures": sorted(structure_values),
        "price": price_bounds,
    }

    active_filters = []
    if search_query:
        active_filters.append({"label": f"Поиск: {search_query}", "param": "q"})
    for cid in category_param:
        cat_name = next((c.name for c in filters_data["categories"] if str(c.category_id) == str(cid)), "Категория")
        active_filters.append({"label": cat_name, "param": "category", "value": cid})
    for color_id in color_param:
        color = next((c for c in filters_data["colors"] if str(c.gemstone_id) == color_id), None)
        if color:
            active_filters.append({"label": f"Цвет: {color.name_color}", "param": "color", "value": color_id})
    for size_id in size_param:
        size = next((s for s in filters_data["sizes"] if str(s.size_id) == size_id), None)
        if size:
            active_filters.append({"label": f"Размер: {size.size}", "param": "size", "value": size_id})
    for store_id in store_param:
        store = next((s for s in filters_data["stores"] if str(s.store_id) == store_id), None)
        if store:
            active_filters.append({"label": f"Магазин: {store.name}", "param": "store", "value": store_id})
    for structure in structure_param:
        active_filters.append({"label": f"Структура: {structure}", "param": "structure", "value": structure})
    if in_stock == '1':
        active_filters.append({"label": "В наличии", "param": "in_stock", "value": "1"})
    if price_min:
        active_filters.append({"label": f"Мин. цена: {price_min}", "param": "price_min", "value": price_min})
    if price_max:
        active_filters.append({"label": f"Макс. цена: {price_max}", "param": "price_max", "value": price_max})

    recommendations = []
    top_products = Product.objects.annotate(popularity=Count('variants__orderitem')).order_by('-popularity')[:3]
    for rec in top_products:
        rec_image = rec.images.first().image_url if hasattr(rec, 'images') and rec.images.first() else PLACEHOLDER_IMAGE
        recommendations.append({
            "id": rec.product_id,
            "name": rec.name,
            "photo": rec_image,
            "detail_url": reverse('product_detail', args=[rec.product_id]),
        })

    context = {
        "products_page": page_obj,
        "product_cards": product_cards,
        "filters_data": filters_data,
        "active_filters": active_filters,
        "selected": {
            "search": search_query,
            "categories": category_param,
            "colors": color_param,
            "sizes": size_param,
            "stores": store_param,
            "structures": structure_param,
            "in_stock": in_stock,
            "price_min": price_min_qs or "",
            "price_max": price_max_qs or "",
            "sort": sort,
        },
        "recommendations": recommendations,
        "palette": PALETTE,
        "placeholder_image": PLACEHOLDER_IMAGE,
        "show_favorites": True,
        "favorite_ids": list(favorite_ids),
        "query_string": query_params.urlencode(),
        "per_page": per_page,
    }
    base_querydict = query_params.copy()
    if 'page' in base_querydict:
        base_querydict.pop('page')
    context["base_query"] = base_querydict.urlencode()

    if wants_partial:
        cards_html = render_to_string(
            "catalog/partials/product_cards.html",
            context | {"product_cards": product_cards, "products_page": page_obj, "favorite_ids": list(favorite_ids)},
            request=request
        )
        pagination_html = render_to_string("catalog/partials/pagination.html", {"products_page": page_obj, "base_query": context.get("base_query", "")}, request=request)
        active_filters_html = render_to_string("catalog/partials/active_filters.html", {"active_filters": active_filters}, request=request)
        return JsonResponse({
            "products_html": cards_html,
            "pagination_html": pagination_html,
            "active_filters_html": active_filters_html,
        })

    return render(request, "catalog/catalog_list.html", context)

def product_detail(request, pk=None):
    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json'
    if Product is None:
        if wants_json:
            return JsonResponse({"detail": "Product model not available"}, status=404)
        return HttpResponseNotFound("Product model not available")

    product = Product.objects.filter(product_id=pk).first() or Product.objects.filter(pk=pk).first()
    if not product:
        if wants_json:
            return JsonResponse({"detail": "Product not found"}, status=404)
        return HttpResponseNotFound("Product not found")

    favorite_ids = _sync_favorite_ids(request)
    product_gallery = _product_gallery_payload(product, include_placeholder=True)
    variant_data, color_options, size_options, store_options, selected_variant = _collect_variant_data(product)
    favorite_toggle_url = reverse('favorite_toggle', args=[product.product_id])
    detail_url = reverse('product_detail', args=[product.product_id])

    initial_gallery = []
    if selected_variant:
        initial_gallery = list(selected_variant.get("images") or [])
    if not initial_gallery:
        initial_gallery = [dict(item) for item in product_gallery] if product_gallery else [{
            "id": None,
            "url": PLACEHOLDER_IMAGE,
            "alt": product.name,
            "is_primary": True,
        }]
    primary_photo = initial_gallery[0]["url"]

    prices = [entry["price"] for entry in variant_data if entry["price"] is not None]
    price_min = min(prices) if prices else None
    price_max = max(prices) if prices else None

    reviews = []
    reviews_summary = {"rating": 0, "count": 0}
    review_form = None
    user_can_review = False
    existing_review = None
    purchased = False
    if ProductReview is not None:
        reviews_qs = ProductReview.objects.filter(product=product, is_public=True).select_related('user')
        agg = reviews_qs.aggregate(avg=Avg('rating'), count=Count('id'))
        reviews_summary = {
            "rating": round(agg['avg'], 1) if agg['avg'] else 0,
            "count": agg['count'] or 0,
        }
        reviews = list(reviews_qs)
        if request.user.is_authenticated:
            if OrderItem is not None:
                purchased = OrderItem.objects.filter(
                    order__user=request.user,
                    product_variant__product=product
                ).exists()
            existing_review = ProductReview.objects.filter(product=product, user=request.user).first()
            user_can_review = purchased and existing_review is None
        if request.method == 'POST' and request.POST.get('intent') == 'add_review':
            if not request.user.is_authenticated:
                messages.error(request, "Войдите, чтобы оставить отзыв.")
                return redirect(f"{reverse('accounts:login')}?next={request.get_full_path()}")
            if not purchased:
                messages.error(request, "Вы можете оставить отзыв только после покупки.")
                return redirect(request.path)
            form = ProductReviewForm(request.POST, product=product)
            if form.is_valid():
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.is_public = False
                if review.variant and getattr(review.variant, 'product_id', None) != product.product_id:
                    review.variant = None
                review.save()
                messages.success(request, "Спасибо! Отзыв отправлен на модерацию и появится после проверки.")
                return redirect(request.path)
            review_form = form
        elif user_can_review:
            review_form = ProductReviewForm(product=product)

    def variant_value(key, default):
        if selected_variant:
            value = selected_variant.get(key)
            if value:
                return value
        return default

    available_sizes = sorted({size["label"] for size in size_options if size.get("label")})
    available_colors = sorted({color.get("name") for color in color_options if color.get("name")})

    specifications = [
        {"label": "Артикул", "value": f"LS-{product.product_id:05d}", "key": "sku"},
        {"label": "Категория", "value": getattr(product.category, "name", "Без категории"), "key": "category"},
        {"label": "Структура", "value": variant_value("structure", "Уточнить"), "key": "structure"},
        {"label": "Бутик", "value": variant_value("store", "Lumiere Secrète"), "key": "store"},
    ]
    created_attr = getattr(product, "created_at", None)
    if created_attr:
        specifications.append({
            "label": "Создан",
            "value": _format_with_user_date(request, created_attr),
            "key": "created",
        })
    characteristics = [
        {"label": "Размер", "value": variant_value("size_label", ", ".join(available_sizes) or "One Size"), "key": "size"},
        {"label": "Материал", "value": variant_value("structure", "Гипоаллергенный сплав"), "key": "material"},
        {"label": "Цвет", "value": variant_value("color_name", ", ".join(available_colors) or "монохром"), "key": "color"},
    ]

    related_candidates = Product.objects.exclude(product_id=product.product_id)
    if product.category_id:
        related_candidates = related_candidates.filter(category_id=product.category_id)
    related_candidates = related_candidates.prefetch_related('variants__color', 'variants__size', 'variants__images', 'images')
    related_list = list(related_candidates[:4])
    if len(related_list) < 4:
        extra = Product.objects.exclude(product_id__in=[product.product_id] + [rel.product_id for rel in related_list])\
            .prefetch_related('variants__color', 'variants__size', 'variants__images', 'images')[:4 - len(related_list)]
        related_list.extend(extra)
    related_products = []
    for rel in related_list:
        rel_variants = list(rel.variants.all())
        rel_prices = [rv.price for rv in rel_variants if rv.price is not None]
        rel_image = None
        for variant in rel_variants:
            rel_image = variant.get_primary_image_url()
            if rel_image:
                break
        if not rel_image:
            fallback_gallery = _product_gallery_payload(rel, include_placeholder=True)
            rel_image = fallback_gallery[0]["url"] if fallback_gallery else PLACEHOLDER_IMAGE
        related_products.append({
            "id": rel.product_id,
            "name": rel.name,
            "photo": rel_image or PLACEHOLDER_IMAGE,
            "price": rel_prices[0] if rel_prices else None,
            "detail_url": reverse('product_detail', args=[rel.product_id]),
        })

    if wants_json:
        variant_param = request.GET.get('variant')
        if variant_param:
            match = next((entry for entry in variant_data if str(entry["id"]) == str(variant_param)), None)
            if match:
                gallery_payload = match.get("images") or product_gallery or [{
                    "id": None,
                    "url": PLACEHOLDER_IMAGE,
                    "alt": product.name,
                    "is_primary": True,
                }]
                return JsonResponse({"variant": match, "gallery": gallery_payload})
        data = _product_to_dict(product)
        data.update({
            "price_min": price_min,
            "price_max": price_max,
            "variants": variant_data,
            "selected_variant": selected_variant,
            "gallery": initial_gallery,
            "image": primary_photo,
            "favorite_url": favorite_toggle_url,
            "is_favorite": product.product_id in favorite_ids,
            "detail_url": detail_url,
            "reviews": [
                {
                    "author": (review.user.get_full_name() or review.user.username) if hasattr(review, 'user') else '',
                    "rating": review.rating,
                    "comment": review.comment,
                    "created_at": review.created_at.isoformat(),
                } for review in reviews
            ],
            "reviews_summary": reviews_summary,
        })
        return JsonResponse(data)

    # favorite_toggle_url already computed above
    selected_store_key = None
    if selected_variant:
        selected_store_key = selected_variant.get("store_key")

    context = {
        "product": product,
        "variant_data": variant_data,
        "color_options": color_options,
        "size_options": size_options,
        "store_options": store_options,
        "selected_variant": selected_variant,
        "selected_color_id": selected_variant["color_id"] if selected_variant else None,
        "selected_size_id": selected_variant["size_id"] if selected_variant else None,
        "selected_store_id": selected_store_key,
        "price_min": price_min,
        "price_max": price_max,
        "primary_photo": primary_photo,
        "gallery": initial_gallery,
        "product_gallery": product_gallery,
        "specifications": specifications,
        "characteristics": characteristics,
        "reviews": reviews,
        "reviews_summary": reviews_summary,
        "review_form": review_form,
        "can_review": user_can_review,
        "existing_review": existing_review,
        "related_products": related_products,
        "is_favorite": product.product_id in favorite_ids,
        "favorite_toggle_url": favorite_toggle_url,
        "cart_add_url": reverse('add_to_cart'),
        "can_add_to_cart": request.user.is_authenticated,
        "login_url": f"{reverse('accounts:login')}?next={request.get_full_path()}",
        "palette": PALETTE,
        "placeholder_image": PLACEHOLDER_IMAGE,
    }
    return render(request, "catalog/product_detail.html", context)

def category_list(request):
    if Category is None:
        return JsonResponse({"categories": []})
    qs = Category.objects.all()[:100]
    data = [{"id": getattr(c, "category_id", getattr(c, "id", None)), "name": getattr(c, "name", None)} for c in qs]
    return JsonResponse({"categories": data})

def category_detail(request, category_id=None):
    if Category is None:
        return HttpResponseNotFound("Category model not available")
    try:
        obj = Category.objects.filter(category_id=category_id).first() or Category.objects.filter(pk=category_id).first()
        if not obj:
            return HttpResponseNotFound("Category not found")
        data = {"id": getattr(obj, "category_id", None), "name": getattr(obj, "name", None)}
        return JsonResponse(data)
    except Exception:
        return HttpResponseNotFound("Category lookup error")

def variants_for_product(request, product_pk=None):
    if ProductVariant is None or Product is None:
        return JsonResponse({"variants": []})
    try:
        product = Product.objects.filter(product_id=product_pk).first() or Product.objects.filter(pk=product_pk).first()
        if not product:
            return JsonResponse({"variants": []})
        qs = ProductVariant.objects.filter(product=product)[:200]
        data = []
        for v in qs:
            data.append({
                "id": getattr(v, "variant_id", getattr(v, "id", None)),
                "price": getattr(v, "price", None),
                "size": getattr(v, "size", None),
                "color": getattr(v, "color", None),
                "quantity": getattr(v, "quantity", None),
            })
        return JsonResponse({"variants": data})
    except Exception:
        return JsonResponse({"variants": []})


def favorites_list(request):
    if Product is None:
        return render(request, "catalog/favorites_list.html", {"items": [], "palette": PALETTE})

    favorite_ids = list(_sync_favorite_ids(request))
    query_params = request.GET.copy()
    only_stock = query_params.get('in_stock') == '1'
    store_filter = query_params.get('store', '').strip()
    sort = query_params.get('sort', 'newest')
    search_query = query_params.get('q', '').strip()
    search_query = query_params.get('q', '').strip()
    page_number = query_params.get('page')

    base_qs = Product.objects.filter(product_id__in=favorite_ids).prefetch_related(
        'variants__color', 'variants__size', 'variants__store', 'variants__images', 'images'
    )
    if search_query:
        base_qs = base_qs.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    if store_filter:
        base_qs = base_qs.filter(variants__store__store_id=store_filter)
    if only_stock:
        base_qs = base_qs.filter(variants__quantity__gt=0)
    if search_query:
        base_qs = base_qs.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    base_qs = base_qs.annotate(min_price=Min('variants__price'))

    sort_map = {
        'cheap': 'min_price',
        'expensive': '-min_price',
        'newest': '-product_id',
    }
    order = sort_map.get(sort, '-product_id')
    products = base_qs.order_by(order, '-product_id').distinct()

    per_page = _user_page_size(request, 12)
    paginator = Paginator(products, per_page)
    page_obj = paginator.get_page(page_number)

    store_options = []
    if Store is not None and favorite_ids:
        store_qs = Store.objects.filter(product_variants__product__product_id__in=favorite_ids).distinct().order_by('name')
        for store in store_qs:
            store_options.append({
                "id": getattr(store, "store_id", getattr(store, "id", None)),
                "name": getattr(store, "name", "Бутик"),
            })

    cards = []
    for product in page_obj.object_list:
        variants = list(product.variants.all())
        if store_filter:
            variants = [v for v in variants if str(getattr(getattr(v, 'store', None), 'store_id', '')) == store_filter]
        selected = None
        if only_stock:
            selected = next((v for v in variants if (v.quantity or 0) > 0), None)
        if selected is None:
            selected = next((v for v in variants if (v.quantity or 0) > 0), None)
        if selected is None and variants:
            selected = variants[0]
        if selected is None:
            continue
        image = selected.get_primary_image_url() if selected else None
        if not image:
            fallback_gallery = _product_gallery_payload(product, include_placeholder=True)
            image = fallback_gallery[0]["url"] if fallback_gallery else PLACEHOLDER_IMAGE
        store_obj = getattr(selected, 'store', None)
        image = image or PLACEHOLDER_IMAGE
        cards.append({
            "product_id": product.product_id,
            "name": product.name,
            "image": image,
            "price": getattr(selected, 'price', None),
            "color": getattr(getattr(selected, 'color', None), 'name_color', ''),
            "size": getattr(getattr(selected, 'size', None), 'size', ''),
            "store_name": getattr(store_obj, 'name', 'Бутик'),
            "store_id": getattr(store_obj, 'store_id', None),
            "in_stock": (getattr(selected, 'quantity', 0) or 0) > 0,
            "variant_id": getattr(selected, 'product_variant_id', getattr(selected, 'id', None)),
            "detail_url": reverse('product_detail', args=[product.product_id]),
            "favorite_url": reverse('favorite_toggle', args=[product.product_id]),
        })

    base_querydict = query_params.copy()
    if 'page' in base_querydict:
        base_querydict.pop('page')
    base_query = base_querydict.urlencode()
    next_page_url = None
    if page_obj.has_next():
        next_params = base_querydict.copy()
        next_params['page'] = page_obj.next_page_number()
        next_page_url = f"?{next_params.urlencode()}" if next_params else f"?page={page_obj.next_page_number()}"

    context = {
        "items": cards,
        "page_obj": page_obj,
        "next_page_url": next_page_url,
        "palette": PALETTE,
        "cart_add_url": reverse('add_to_cart') if request.user.is_authenticated else None,
        "bulk_add_url": reverse('favorites_add_all_to_cart') if request.user.is_authenticated and cards else None,
        "clear_url": reverse('favorite_clear'),
        "login_url": f"{reverse('accounts:login')}?next={request.path}",
        "wishlist_count": len(favorite_ids),
        "filters": {
            "in_stock": only_stock,
            "store": store_filter,
            "sort": sort,
            "stores": store_options,
            "search": search_query,
        },
        "query_string": query_params.urlencode(),
        "base_query": base_query,
        "can_checkout": request.user.is_authenticated,
        "per_page": per_page,
    }
    return render(request, "catalog/favorites_list.html", context)


@require_http_methods(["POST"])
def favorite_toggle(request, pk=None):
    if Product is None:
        return HttpResponseBadRequest("Favorites unavailable")
    product = Product.objects.filter(product_id=pk).first() or Product.objects.filter(pk=pk).first()
    if not product:
        return HttpResponseBadRequest("Product not found")

    state = "added"
    count = 0
    if request.user.is_authenticated and Favorite is not None:
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
        if not created:
            favorite.delete()
            state = "removed"
        count = Favorite.objects.filter(user=request.user).count()
    else:
        wishlist = _session_wishlist_ids(request)
        if product.product_id in wishlist:
            wishlist = [pid for pid in wishlist if pid != product.product_id]
            state = "removed"
        else:
            wishlist.append(product.product_id)
            state = "added"
        request.session["wishlist"] = wishlist
        request.session.modified = True
        count = len(wishlist)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"state": state, "count": count})

    message = "Товар добавлен в избранное." if state == "added" else "Товар убран из избранного."
    if request.user.is_authenticated:
        if state == "added":
            messages.success(request, message)
        else:
            messages.info(request, message)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('catalog_list')
    return redirect(next_url)


@login_required(login_url='accounts:login')
@require_http_methods(["POST"])
def favorites_add_all_to_cart(request):
    if CartItem is None or ProductVariant is None or Product is None:
        return HttpResponseBadRequest("Cart unavailable")
    favorite_ids = list(_sync_favorite_ids(request))
    total = len(favorite_ids)
    products = Product.objects.filter(product_id__in=favorite_ids)
    added = 0
    for product in products:
        variant = ProductVariant.objects.filter(product=product, quantity__gt=0).order_by('-quantity').first()
        if not variant:
            variant = ProductVariant.objects.filter(product=product).first()
        if not variant:
            continue
        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product_variant=variant,
            defaults={"quantity": 1, "price": getattr(variant, "price", None)}
        )
        if not created:
            item.quantity = (item.quantity or 0) + 1
        item.price = getattr(variant, "price", item.price)
        item.save()
        added += 1
    _clear_favorites(request)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"added": added, "total": total})
    if added:
        messages.success(request, f"Добавили {added} товара в корзину.")
    else:
        messages.info(request, "Нет доступных товаров для добавления.")
    return redirect('favorites_list')


@require_http_methods(["POST"])
def favorite_clear(request):
    if Product is None:
        return HttpResponseBadRequest("Favorites unavailable")
    cleared = _clear_favorites(request)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({"cleared": cleared})
    if cleared:
        messages.info(request, "Список избранного очищен.")
    else:
        messages.info(request, "В избранном и так пусто.")
    return redirect('favorites_list')
def _user_page_size(request, default):
    size = default
    if UserSettings is not None and request.user.is_authenticated:
        try:
            settings_obj = request.user.usersettings
            value = settings_obj.page_size or default
            size = max(1, min(60, int(value)))
        except (UserSettings.DoesNotExist, ValueError, TypeError):
            size = default
    return size
def _format_with_user_date(request, value):
    if not value:
        return ""
    fmt = "%d.%m.%Y %H:%M"
    if UserSettings is not None and request.user.is_authenticated:
        try:
            fmt = request.user.usersettings.date_format or fmt
        except UserSettings.DoesNotExist:
            fmt = fmt
    try:
        return timezone.localtime(value).strftime(fmt)
    except Exception:
        try:
            return value.strftime(fmt)
        except Exception:
            return str(value)
