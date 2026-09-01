from common.decorators import enforce_permissions
import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from courses.models import Course
from courses.repositories.course_repository import CourseRepository
from courses.services.course_service import CourseService
from courses.services.course_validator import CourseValidator

course_validator = CourseValidator()
course_repository = CourseRepository()
course_service = CourseService(course_validator, course_repository)

from common.utils import paginate_queryset
from courses.mappers.course_mapper import CourseMapper

def serialize_course(course):
    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "description": course.description,
        "credits": course.credits,
        "department": course.department_id,
        "teacher": course.teacher_id,
        "is_active": course.is_active,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
    }

@csrf_exempt
@enforce_permissions('courses', 'course')
def course_api(request, course_id = None):
    try:
        if request.method == "GET":
            if course_id is not None:
                course = course_service.get(course_id)
                return JsonResponse(serialize_course(course))

            search = request.GET.get("search", "").strip() or None
            courses = course_repository.get_queryset_for_list(search = search)
            return paginate_queryset(request, courses, CourseMapper.to_list_dto)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            course = course_service.create(data)
            return JsonResponse(serialize_course(course), status = 201)

        if request.method == "PUT":
            if course_id is None:
                return JsonResponse({"error": Messages.COURSE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            course = course_service.update(course_id, data, partial = False)
            return JsonResponse(serialize_course(course))

        if request.method == "PATCH":
            if course_id is None:
                return JsonResponse({"error": Messages.COURSE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            course = course_service.update(course_id, data, partial = True)
            return JsonResponse(serialize_course(course))

        if request.method == "DELETE":
            if course_id is None:
                return JsonResponse({"error": Messages.COURSE_ID_REQUIRED}, status = 400)

            course_service.delete(course_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Course.DoesNotExist:
        return JsonResponse({"error": Messages.COURSE_NOT_FOUND_BY_ID.format(course_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.COURSE_CANNOT_BE_DELETED.format(course_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('courses', 'course')
def course_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    department_id = request.GET.get("department_id") or None
    courses = course_repository.get_queryset_for_reference(department_id = department_id)
    return paginate_queryset(request, courses, CourseMapper.to_reference_dto, default_page_size = 10)
