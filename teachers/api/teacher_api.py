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

def serialize_teacher_profile(teacher):
    return {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "employee_id": teacher.employee_id,
        "email": teacher.email,
        "department_name": teacher.department.name if teacher.department_id else None,
        "designation": teacher.designation,
    }


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
        if teacher_id is not None and not scoped_qs.filter(id = teacher_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

        if request.method == "GET":
            if teacher_id is not None:
                teacher = teacher_service.get(teacher_id)
                return JsonResponse(serialize_teacher(teacher))

            search = request.GET.get("search", "").strip() or None
            list_qs = apply_data_scope(request.user, teacher_repository.get_queryset_for_list(search = search), 'teacher')
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


@csrf_exempt
@enforce_permissions('teachers', 'teacher')
def teacher_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope
    department_id = request.GET.get("department_id") or None
    teachers = apply_data_scope(request.user, teacher_repository.get_queryset_for_reference(department_id = department_id), 'teacher')
    return paginate_queryset(request, teachers, TeacherMapper.to_reference_dto, default_page_size = 10)


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

    return JsonResponse(serialize_teacher_profile(teacher))


def my_students_api(request):
    # Returns one row per enrollment (student + which of the teacher's own
    # classes/section they're in), which is what the Teacher Students page
    # actually renders - not bare Student records with no class context.
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request, apply_data_scope
    from enrollments.repositories.enrollment_repository import EnrollmentRepository
    from enrollments.mappers.enrollment_mapper import EnrollmentMapper

    user, error = authenticate_request(request)
    if error:
        return error

    # Reuses apply_data_scope's existing teacher branch for 'enrollment':
    # enrollments in this teacher's own course offerings - the same scoping
    # rule already used by the general /enrollments/ list, just resolved for `me`.
    qs = apply_data_scope(user, EnrollmentRepository().get_queryset_for_list(), 'enrollment')

    # Optional: scope down to one class's roster (e.g. for marking attendance,
    # where every student in the selected class must be selectable, not just
    # whichever page of the teacher's full cross-class enrollment list happens
    # to be loaded).
    course_offering_id = request.GET.get("course_offering_id")
    if course_offering_id:
        qs = qs.filter(course_offering_id = course_offering_id)

    return paginate_queryset(request, qs, EnrollmentMapper.to_teacher_list_dto, default_page_size = 10)


def my_dashboard_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND}, status = 404)

    from course_offerings.models import CourseOffering
    from enrollments.models import Enrollment

    active_classes = CourseOffering.objects.filter(
        teacher_id = teacher.id, is_deleted = False, is_active = True,
    ).count()

    total_students = Enrollment.objects.filter(
        course_offering__teacher_id = teacher.id,
        course_offering__is_deleted = False,
        is_deleted = False,
        status = Enrollment.Status.ACTIVE,
    ).values("student_id").distinct().count()

    return JsonResponse({
        "active_classes": active_classes,
        "total_students": total_students,
    })