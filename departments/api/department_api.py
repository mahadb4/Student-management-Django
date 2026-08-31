from common.decorators import enforce_permissions
import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from departments.models import Department
from departments.repositories.department_repository import DepartmentRepository
from departments.services.department_service import DepartmentService
from departments.services.department_validator import DepartmentValidator
from departments.mappers.department_mapper import DepartmentMapper

department_validator = DepartmentValidator()
department_repository = DepartmentRepository()
department_service = DepartmentService(department_validator, department_repository)

from common.utils import paginate_queryset


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
            departments = department_repository.get_queryset_for_list(search = search)
            return paginate_queryset(request, departments, DepartmentMapper.to_list_dto)

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