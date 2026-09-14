import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from attendance.models import Attendance
from attendance.repositories.attendance_repository import AttendanceRepository
from attendance.services.attendance_service import AttendanceService
from attendance.services.attendance_validator import AttendanceValidator
from common.messages import Messages
from teachers.models import Teacher

attendance_validator = AttendanceValidator()
attendance_repository = AttendanceRepository()
attendance_service = AttendanceService(attendance_validator, attendance_repository)

from common.utils import paginate_queryset


def serialize_attendance(attendance):
    return {
        "id": attendance.id,
        "enrollment": attendance.enrollment_id,
        "date": attendance.date,
        "status": attendance.status,
        "remarks": attendance.remarks,
        "created_at": attendance.created_at,
        "updated_at": attendance.updated_at,
    }



from common.decorators import enforce_permissions
from attendance.mappers.attendance_mapper import AttendanceMapper


#Admin Attendance page filters (Department -> Teacher -> Course Offering ->
#Date). All ORM-level (.filter() on the queryset already scoped by
#apply_data_scope above) - never fetched broadly and filtered in Python.
#Every param is optional and independent so a teacher/student's own scoped
#queryset (from apply_data_scope) is only ever narrowed further, never widened.
def _apply_admin_filters(request, queryset):
    department_id = request.GET.get("department_id", "").strip()
    if department_id:
        queryset = queryset.filter(enrollment__course_offering__teacher__department_id = department_id)

    teacher_id = request.GET.get("teacher_id", "").strip()
    if teacher_id:
        queryset = queryset.filter(enrollment__course_offering__teacher_id = teacher_id)

    course_offering_id = request.GET.get("course_offering_id", "").strip()
    if course_offering_id:
        queryset = queryset.filter(enrollment__course_offering_id = course_offering_id)

    section_id = request.GET.get("section_id", "").strip()
    if section_id:
        queryset = queryset.filter(enrollment__course_offering__section_id = section_id)

    student_id = request.GET.get("student_id", "").strip()
    if student_id:
        queryset = queryset.filter(enrollment__student_id = student_id)

    date = request.GET.get("date", "").strip()
    if date:
        queryset = queryset.filter(date = date)

    return queryset


@csrf_exempt
@enforce_permissions('attendance', 'attendance')
def attendance_api(request, attendance_id = None):
    try:
        from common.permissions import apply_data_scope
        from attendance.models import Attendance
        scoped_qs = apply_data_scope(request.user, Attendance.objects.all(), 'attendance')
        if attendance_id is not None and not scoped_qs.filter(id = attendance_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

        if request.method == "GET":
            if attendance_id is not None:
                attendance = attendance_service.get(attendance_id)
                return JsonResponse(serialize_attendance(attendance))

            attendances = apply_data_scope(request.user, attendance_repository.get_queryset_for_list(), 'attendance')
            attendances = _apply_admin_filters(request, attendances)
            return paginate_queryset(request, attendances, AttendanceMapper.to_list_dto)

        if request.method in ("POST", "PUT", "PATCH"):
            teacher = Teacher.objects.filter(
                user = request.user,
                is_deleted = False,
                is_active = True,
            ).first()

            if not teacher:
                return JsonResponse({"error": Messages.ATTENDANCE_TEACHER_NOT_FOUND}, status = 400)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            attendance = attendance_service.create(data, teacher)
            return JsonResponse(serialize_attendance(attendance), status = 201)

        if request.method == "PUT":
            if attendance_id is None:
                return JsonResponse({"error": Messages.ATTENDANCE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            attendance = attendance_service.update(attendance_id, data, teacher, partial = False)
            return JsonResponse(serialize_attendance(attendance))

        if request.method == "PATCH":
            if attendance_id is None:
                return JsonResponse({"error": Messages.ATTENDANCE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            attendance = attendance_service.update(attendance_id, data, teacher, partial = True)
            return JsonResponse(serialize_attendance(attendance))

        if request.method == "DELETE":
            if attendance_id is None:
                return JsonResponse({"error": Messages.ATTENDANCE_ID_REQUIRED}, status = 400)

            attendance_service.delete(attendance_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Attendance.DoesNotExist:
        return JsonResponse({"error": Messages.ATTENDANCE_NOT_FOUND_BY_ID.format(attendance_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.ATTENDANCE_CANNOT_BE_DELETED.format(attendance_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


def serialize_bulk_attendance(attendance):
    # enrollment_id explicit (unlike serialize_attendance's "enrollment" key)
    # - the frontend needs it to map each created row back to which student's
    # marking-column entry it came from.
    return {
        "id": attendance.id,
        "enrollment_id": attendance.enrollment_id,
        "date": attendance.date,
        "status": attendance.status,
        "remarks": attendance.remarks,
    }


@csrf_exempt
@enforce_permissions('attendance', 'attendance')
def attendance_bulk_api(request):
    # POST /attendance/bulk/ - one class + one date = one logical write,
    # instead of the frontend looping POST /attendance/ once per student.
    # Same authorization shape as attendance_api's own POST branch above
    # (Teacher-profile required, ownership enforced in the service) -
    # deliberately not touched/widened here.
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    try:
        teacher = Teacher.objects.filter(
            user = request.user,
            is_deleted = False,
            is_active = True,
        ).first()

        if not teacher:
            return JsonResponse({"error": Messages.ATTENDANCE_TEACHER_NOT_FOUND}, status = 400)

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        created = attendance_service.create_bulk(
            data.get("course_offering_id"), data.get("date"), data.get("records"), teacher,
        )
        return JsonResponse(
            {"created": [serialize_bulk_attendance(a) for a in created]}, status = 201,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


def my_attendance_api(request):
    # Serves /teachers/me/attendance/ - apply_data_scope's 'attendance' branch
    # scopes to the teacher's own classes. (Students use my_student_attendance_api
    # below, which returns a narrower, student-specific projection.)
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request, apply_data_scope
    user, error = authenticate_request(request)
    if error:
        return error

    qs = apply_data_scope(user, attendance_repository.get_queryset_for_list(), 'attendance')

    # Optional: scope down to one class's attendance history (the Teacher
    # Attendance page always has a class selected). Safe by construction even
    # for a course_offering_id the caller doesn't teach - apply_data_scope
    # above already restricts rows to this teacher's own offerings, so an
    # unrelated id just yields zero additional rows, never someone else's.
    course_offering_id = request.GET.get("course_offering_id")
    if course_offering_id:
        qs = qs.filter(enrollment__course_offering_id = course_offering_id)

    return paginate_queryset(request, qs, AttendanceMapper.to_teacher_list_dto, default_page_size = 10)


def my_student_attendance_api(request):
    # Serves /students/me/attendance/ - returns only the fields the Student
    # Attendance UI uses (no student_id/student_name/course_id, which are
    # redundant echoes of the caller's own identity). Paginated at the
    # project-standard default_page_size = 10 since attendance history grows
    # without bound over a student's enrollment.
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request, apply_data_scope
    user, error = authenticate_request(request)
    if error:
        return error

    qs = apply_data_scope(user, attendance_repository.get_queryset_for_list(), 'attendance')

    # Optional: scope down to one course (the Student Attendance page's course
    # filter). Mirrors my_attendance_api's course_offering_id filter above -
    # apply_data_scope already restricts rows to this student's own
    # enrollments, so an unrelated id just yields zero additional rows.
    course_offering_id = request.GET.get("course_offering_id")
    if course_offering_id:
        qs = qs.filter(enrollment__course_offering_id = course_offering_id)

    # Same idea, but keyed by enrollment id directly - the course-picker
    # dropdown's option values are enrollment ids (matching the existing
    # /students/me/courses/reference/ list), so this avoids needing a second
    # id type just to select one course from that dropdown.
    enrollment_id = request.GET.get("enrollment_id")
    if enrollment_id:
        qs = qs.filter(enrollment_id = enrollment_id)

    return paginate_queryset(request, qs, AttendanceMapper.to_student_list_dto, default_page_size = 10)
