from common.decorators import enforce_permissions
import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.cache.cache_service import CacheService
from common.messages import Messages
from departments.cache.department_cache import DepartmentCache
from departments.models import Department
from departments.repositories.department_repository import DepartmentRepository
from departments.services.department_service import DepartmentService
from departments.services.department_validator import DepartmentValidator
from departments.mappers.department_mapper import DepartmentMapper

department_validator = DepartmentValidator()
department_repository = DepartmentRepository()
department_cache = DepartmentCache(CacheService())
department_service = DepartmentService(department_validator, department_repository, department_cache)

from common.utils import paginate_queryset, resolve_pagination_params


def serialize_department(department):
    return {
        "id": department.id,
        "name": department.name,
        "code": department.code,
        "description": department.description,
        "is_active": department.is_active,
        # "created_at": department.created_at,
        # "updated_at": department.updated_at,
    }


@csrf_exempt
@enforce_permissions('departments', 'department')
def department_api(request, department_id = None):
    try:
        if request.method == "GET":
            if department_id is not None:
                department = department_service.get(department_id)
                return JsonResponse(serialize_department(department))

            search = request.GET.get("search", "").strip() or None
            #Normalize paging first so the cache key reflects the effective page,
            #not the raw query string. Pagination and DTO mapping happen inside
            #the service, behind the Redis list cache.
            page_number, page_size = resolve_pagination_params(request)
            return JsonResponse(
                department_service.get_list(request.user, search, page_number, page_size)
            )

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            department = department_service.create(data)
            return JsonResponse(serialize_department(department), status = 201)

        if request.method == "PUT":
            if department_id is None:
                return JsonResponse({"error": Messages.DEPARTMENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            department = department_service.update(department_id, data, partial = False)
            return JsonResponse(serialize_department(department))

        if request.method == "PATCH":
            if department_id is None:
                return JsonResponse({"error": Messages.DEPARTMENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            department = department_service.update(department_id, data, partial = True)
            return JsonResponse(serialize_department(department))

        if request.method == "DELETE":
            if department_id is None:
                return JsonResponse({"error": Messages.DEPARTMENT_ID_REQUIRED}, status = 400)

            department_service.delete(department_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Department.DoesNotExist:
        return JsonResponse({"error": Messages.DEPARTMENT_NOT_FOUND_BY_ID.format(department_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.DEPARTMENT_CANNOT_BE_DELETED.format(department_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('departments', 'department')
def department_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    #default_page_size = 10 must match what the service caches under, so the key
    #reflects the page size actually served.
    page_number, page_size = resolve_pagination_params(request, default_page_size = 10)
    return JsonResponse(
        department_service.get_reference_list(request.user, page_number, page_size)
    )