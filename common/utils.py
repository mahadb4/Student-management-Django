import json
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from common.constants import PROFILE_PICTURE_CONTENT_TYPES
from common.messages import Messages


def split_display_name(full_name):
    parts = (full_name or "").strip().split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def build_full_name(first_name, last_name):
    return f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()


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


# Normalizes ?page=/?page_size= into safe integers so callers that cache a
# paginated payload key on the normalized values, not the raw query string.
def resolve_pagination_params(request,
                              default_page_size = 10,
                              max_page_size = 500):
    try:
        page_size = int(
            request.GET.get("page_size", default_page_size)
            )

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

    return page_number, page_size


# Normalizes ?ordering= against an allowlist (falls back to `default` if missing/
# invalid) so cached paginated payloads don't fragment on the raw query string.
def resolve_ordering_param(request, allowed_fields, default):
    raw = request.GET.get("ordering", "").strip()
    key = raw[1:] if raw.startswith("-") else raw

    if key in allowed_fields:
        return raw

    return default


# Applies a normalized ordering value, appending "id" as a deterministic
# secondary sort so rows with an equal primary value still paginate stably.
def apply_ordering(queryset, ordering, allowed_fields):
    descending = ordering.startswith("-")
    key = ordering[1:] if descending else ordering
    fields = allowed_fields[key]

    if descending:
        fields = tuple(f"-{field}" for field in fields)

    return queryset.order_by(*fields, "-id" if descending else "id")


# Kept separate from paginate_queryset() so a service layer can cache the
# payload before it is turned into a JsonResponse.
def build_paginated_payload(queryset,
                            page_number,
                            page_size,
                            serializer_func):
    paginator = Paginator(queryset, page_size)

    if paginator.count == 0:
        return {
            "total_count": 0,
            "current_page": 1,
            "page_size": page_size,
            "total_pages": 0,
            "results": [],
        }

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        # Out-of-range page number falls back to the last page instead of erroring.
        page_obj = paginator.page(paginator.num_pages)

    return {
        "total_count": paginator.count,
        "current_page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "results": [serializer_func(item) for item in page_obj],
    }


def extension_for_content_type(content_type):
    normalized = (content_type or "").strip().lower()

    if normalized not in PROFILE_PICTURE_CONTENT_TYPES:
        raise ValueError(Messages.PROFILE_PICTURE_INVALID_CONTENT_TYPE.format(content_type))

    return PROFILE_PICTURE_CONTENT_TYPES[normalized]


# Generic version of extension_for_content_type() - added rather than
# generalizing that one in place, so profile pictures (the only existing
# caller) are left untouched. Used by assignments for both the attachment
# and the submission upload flows, which accept a different set of types.
def extension_for_allowed_content_type(content_type, allowed_types, invalid_message):
    normalized = (content_type or "").strip().lower()

    if normalized not in allowed_types:
        raise ValueError(invalid_message.format(content_type))

    return allowed_types[normalized]


# Called after the cache lookup, so signed S3 URLs never get written to Redis.
def attach_profile_picture_urls(results, s3_service):
    for item in results:
        key = item.pop("profile_picture_key", None)
        item["profile_picture_url"] = s3_service.generate_view_url(key) if key else None

    return results


def paginate_queryset(request,
                      queryset,
                      serializer_func,
                      default_page_size = 10,
                      max_page_size = 500):
    page_number, page_size = resolve_pagination_params(request, default_page_size, max_page_size)

    return JsonResponse(
        build_paginated_payload(queryset, page_number, page_size, serializer_func)
    )