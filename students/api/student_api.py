import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator

student_validator = StudentValidator()
student_repository = StudentRepository()
student_service = StudentService(student_validator, student_repository)

from common.utils import paginate_queryset

def serialize_student(student):
    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "student_email": student.student_email,
        "parents_phone_number": student.parents_phone_number,
        "date_of_birth": str(student.date_of_birth),
        "gender": student.gender,
        "address": student.address,
        "department": student.department_id,
        "section": student.section_id,
        "date_of_enrollment": str(student.date_of_enrollment),
        "is_active": student.is_active,
    }


from common.decorators import enforce_permissions
from students.mappers.student_mapper import StudentMapper

@csrf_exempt
@enforce_permissions('students', 'student')
def student_api(request, student_id = None):
    try:
        from common.permissions import apply_data_scope
        # List responses use a projected, JOINed queryset (id/name fields + department/section
        # names only) so the Students list never needs separate Department/Section round trips.
        scoped_qs = apply_data_scope(request.user, student_repository.get_queryset_for_list(), 'student')
        if student_id is not None and not scoped_qs.filter(id = student_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

        if request.method == "GET":
            if student_id is not None:
                student = student_service.get(student_id)
                return JsonResponse(serialize_student(student))

            search = request.GET.get("search", "").strip() or None
            students = apply_data_scope(request.user, student_repository.get_queryset_for_list(search = search), 'student')
            return paginate_queryset(request, students, StudentMapper.to_list_dto)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student = student_service.create(data)
            return JsonResponse(serialize_student(student), status = 201)

        if request.method == "PUT":
            if student_id is None:
                return JsonResponse({"error": Messages.STUDENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student = student_service.update(student_id, data, partial = False)
            return JsonResponse(serialize_student(student))

        if request.method == "PATCH":
            if student_id is None:
                return JsonResponse({"error": Messages.STUDENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student = student_service.update(student_id, data, partial = True)
            return JsonResponse(serialize_student(student))

        if request.method == "DELETE":
            if student_id is None:
                return JsonResponse({"error": Messages.STUDENT_ID_REQUIRED}, status = 400)

            student_service.delete(student_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Student.DoesNotExist:
        return JsonResponse({"error": Messages.STUDENT_NOT_FOUND_BY_ID.format(student_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.STUDENT_CANNOT_BE_DELETED.format(student_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('students', 'student')
def student_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope
    students = apply_data_scope(request.user, student_repository.get_queryset_for_reference(), 'student')
    return JsonResponse(
        [StudentMapper.to_reference_dto(student) for student in students],
        safe = False,
    )


def my_profile_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    student = getattr(user, "student_profile", None)
    if not student:
        return JsonResponse({"error": Messages.STUDENT_NOT_FOUND}, status = 404)

    return JsonResponse(serialize_student(student))