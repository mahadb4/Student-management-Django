import json
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from common.messages import Messages


def parse_json_request(request):
    try:
        if not request.body:
            return {}

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        return data

    except json.JSONDecodeError:
        raise ValueError(Messages.INVALID_JSON)


def paginate_queryset(request, queryset, serializer_func, default_page_size = 50, max_page_size = 500):
    try:
        page_size = int(request.GET.get("page_size", default_page_size))
    except (TypeError, ValueError):
        page_size = default_page_size

    if page_size < 1:
        page_size = default_page_size

    page_size = min(page_size, max_page_size)

    try:
        page_number = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_number = 1

    if page_number < 1:
        page_number = 1

    paginator = Paginator(queryset, page_size)

    if paginator.count == 0:
        return JsonResponse({
            "total_count": 0,
            "current_page": 1,
            "page_size": page_size,
            "total_pages": 0,
            "results": [],
        })

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return JsonResponse({
        "total_count": paginator.count,
        "current_page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "results": [serializer_func(item) for item in page_obj],
    })