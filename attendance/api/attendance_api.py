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


def my_attendance_api(request):
    # Serves both /students/me/attendance/ and /teachers/me/attendance/ -
    # apply_data_scope's 'attendance' branch already scopes correctly for
    # whichever role request.user turns out to be, so one view covers both.
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request, apply_data_scope
    user, error = authenticate_request(request)
    if error:
        return error

    qs = apply_data_scope(user, attendance_repository.get_queryset_for_list(), 'attendance')
    return paginate_queryset(request, qs, AttendanceMapper.to_list_dto)
