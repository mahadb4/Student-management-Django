import json
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from common.messages import Messages


#Splits a full name into (first_name, rest).
def split_display_name(full_name):
    parts = (full_name or "").strip().split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


#Joins first_name/last_name into a single display name.
def build_full_name(first_name, last_name):
    return f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()


def parse_json_request(request):
    try:
        if not request.body:
            return {}

        #This converts JSON into Python data
        data = json.loads(request.body)

        #Checks whether the received data is a Python dictionary
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        return data

    except json.JSONDecodeError:
        raise ValueError(Messages.INVALID_JSON)


#Reads ?page= and ?page_size= and normalizes them into safe integers.
#Extracted so that callers which cache a paginated payload key their cache on the
#NORMALIZED values ("?page=abc", "?page=-3" and "?page=" must not each create a
#separate cache entry for what is really page 1).
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

    #min() chooses the smaller value
    page_size = min(page_size, max_page_size)

    try:
        page_number = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_number = 1

    if page_number < 1:
        page_number = 1

    return page_number, page_size


#Reads ?ordering= and normalizes it into a safe, allowlisted value. Currently only
#"name"/"-name" sorting is supported anywhere in the project (see each entity
#repository's ORDERING_FIELDS), so allowed_fields is always a single-key map, but
#this stays generic in case a second sortable field is ever genuinely needed.
#
#Extracted for the same reason as resolve_pagination_params(): callers which cache
#a paginated payload key their cache on the NORMALIZED value, so an invalid/missing
#?ordering= always falls back to the same default rather than fragmenting the cache.
#
#allowed_fields: dict mapping a public ordering key (no leading "-") to a tuple of
#real ORM field lookups in ascending order, e.g. {"name": ("first_name","last_name")}.
#default: the public key to use (ascending) when ?ordering= is missing or not present
#in allowed_fields. Never raises - an invalid value is treated the same as a missing one.
def resolve_ordering_param(request, allowed_fields, default):
    raw = request.GET.get("ordering", "").strip()
    key = raw[1:] if raw.startswith("-") else raw

    if key in allowed_fields:
        return raw

    return default


#Applies an ALREADY-normalized ordering value (from resolve_ordering_param) to a
#queryset, translating the public key to its real ORM field(s) via allowed_fields,
#and appending "id" as a deterministic secondary sort so rows with an equal primary
#value still paginate stably - direction-matched to the primary field, e.g.
#"name" -> id ASC, "-name" -> id DESC.
def apply_ordering(queryset, ordering, allowed_fields):
    descending = ordering.startswith("-")
    key = ordering[1:] if descending else ordering
    fields = allowed_fields[key]

    if descending:
        fields = tuple(f"-{field}" for field in fields)

    return queryset.order_by(*fields, "-id" if descending else "id")


#Builds the plain paginated payload dict. Takes ALREADY-normalized page/page_size.
#Kept separate from paginate_queryset() so a service layer can cache the payload
#before it is turned into a JsonResponse.
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
        #Suppose: Total pages = 5 User requests: ?page=100 Instead of an error: Return last page = Page 5
        page_obj = paginator.page(paginator.num_pages)

    return {
        "total_count": paginator.count,
        "current_page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "results": [serializer_func(item) for item in page_obj],
    }


def paginate_queryset(request, #Contains: ?page=2&page_size=10
                      queryset, #This is the database data to paginate like students.objects.all()
                      serializer_func,
                      default_page_size = 10,
                      max_page_size = 500):
    page_number, page_size = resolve_pagination_params(request, default_page_size, max_page_size)

    #Now the API sends the final result to the frontend
    return JsonResponse(
        build_paginated_payload(queryset, page_number, page_size, serializer_func)
    )