from django.http import JsonResponse, HttpResponseNotFound, HttpResponseNotAllowed
from django.views.decorators.http import require_http_methods
from .models import Store


def _store_to_dict(store: Store):
    return {
        "store_id": store.store_id,
        "name": store.name,
        "business_hours": store.business_hours,
        "photo": store.photo,
        "address_id": store.address_id,
    }


@require_http_methods(["GET"])
def store_list(request):
    data = [_store_to_dict(store) for store in Store.objects.select_related("address")[:100]]
    return JsonResponse({"stores": data})


@require_http_methods(["GET"])
def store_detail(request, pk=None):
    store = Store.objects.filter(store_id=pk).first() or Store.objects.filter(pk=pk).first()
    if not store:
        return HttpResponseNotFound("Store not found")
    return JsonResponse(_store_to_dict(store))


def store_create(request):
    return HttpResponseNotAllowed(["GET"])


def store_update(request, pk=None):
    return HttpResponseNotAllowed(["GET"])


def store_delete(request, pk=None):
    return HttpResponseNotAllowed(["GET"])
