import json
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from common.messages import Messages


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


def paginate_queryset(request, #Contains: ?page=2&page_size=10
                      queryset, #This is the database data to paginate like students.objects.all()
                      serializer_func, 
                      default_page_size = 50, 
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
        #Suppose: Total pages = 5 User requests: ?page=100 Instead of an error: Return last page = Page 5
        page_obj = paginator.page(paginator.num_pages)


    #Now the API sends the final result to the frontend
    return JsonResponse({
        "total_count": paginator.count,
        "current_page": page_obj.number,
        "page_size": page_size,
        "total_pages": paginator.num_pages,
        "results": [serializer_func(item) for item in page_obj],
    })