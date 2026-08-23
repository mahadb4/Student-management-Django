import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator

teacher_validator = TeacherValidator()
teacher_repository = TeacherRepository()
teacher_service = TeacherService(teacher_validator, teacher_repository)

from common.utils import paginate_queryset

def serialize_teacher(teacher):
    return {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "employee_id": teacher.employee_id,
        "email": teacher.email,
        "phone_number": teacher.phone_number,
        "department": teacher.department_id,
        "designation": teacher.designation,
        "qualification": teacher.qualification,
        "gender": teacher.gender,
        "date_of_birth": teacher.date_of_birth,
        "date_of_joining": teacher.date_of_joining,
        "salary": teacher.salary,
        "address": teacher.address,
        "is_active": teacher.is_active,
        "created_at": teacher.created_at,
        "updated_at": teacher.updated_at,
    }


from common.decorators import enforce_permissions
from teachers.mappers.teacher_mapper import TeacherMapper

@csrf_exempt
@enforce_permissions('teachers', 'teacher')
def teacher_api(request, teacher_id = None):
    try:
        from common.permissions import apply_data_scope
        from teachers.models import Teacher
        scoped_qs = apply_data_scope(request.user, Teacher.objects.all(), 'teacher')
        if teacher_id is not None and not scoped_qs.filter(id=teacher_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status=403)

        if request.method == "GET":
            if teacher_id is not None:
                teacher = teacher_service.get(teacher_id)
                return JsonResponse(serialize_teacher(teacher))

            list_qs = apply_data_scope(request.user, teacher_repository.get_queryset_for_list(), 'teacher')
            return paginate_queryset(request, list_qs, TeacherMapper.to_list_dto)

        if request.method == "POST":
            teacher = teacher_service.create(json.loads(request.body))
            return JsonResponse(serialize_teacher(teacher), status = 201)

        if request.method == "PUT":
            if teacher_id is None:
                return JsonResponse({"error": Messages.TEACHER_ID_REQUIRED}, status = 400)

            teacher = teacher_service.update(teacher_id, json.loads(request.body))
            return JsonResponse(serialize_teacher(teacher))

        if request.method == "PATCH":
            if teacher_id is None:
                return JsonResponse({"error": Messages.TEACHER_ID_REQUIRED}, status = 400)

            teacher = teacher_service.update(teacher_id, json.loads(request.body), partial = True)
            return JsonResponse(serialize_teacher(teacher))

        if request.method == "DELETE":
            if teacher_id is None:
                return JsonResponse({"error": Messages.TEACHER_ID_REQUIRED}, status = 400)

            teacher_service.delete(teacher_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Teacher.DoesNotExist:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND_BY_ID.format(teacher_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.TEACHER_CANNOT_BE_DELETED.format(teacher_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


def my_profile_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND}, status = 404)

    return JsonResponse(serialize_teacher(teacher))


def my_students_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request, apply_data_scope
    from students.repositories.student_repository import StudentRepository
    from students.mappers.student_mapper import StudentMapper

    user, error = authenticate_request(request)
    if error:
        return error

    # Reuses apply_data_scope's existing teacher branch for 'student': students
    # enrolled in this teacher's own course offerings - the same scoping rule
    # already used by the general /students/ list, just resolved for `me`.
    qs = apply_data_scope(user, StudentRepository().get_queryset_for_list(), 'student')
    return paginate_queryset(request, qs, StudentMapper.to_list_dto)