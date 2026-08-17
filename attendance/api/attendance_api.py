import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from attendance.models import Attendance
from attendance.repositories.attendance_repository import AttendanceRepository
from attendance.services.attendance_service import AttendanceService
from attendance.services.attendance_validator import AttendanceValidator
from common.messages import Messages

attendance_validator = AttendanceValidator()
attendance_repository = AttendanceRepository()
attendance_service = AttendanceService(attendance_validator, attendance_repository)


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


@csrf_exempt
def attendance_api(request, attendance_id = None):
    try:
        if request.method == "GET":
            if attendance_id is not None:
                attendance = attendance_service.get(attendance_id)
                return JsonResponse(serialize_attendance(attendance))

            attendances = attendance_service.get_all()
            return JsonResponse([serialize_attendance(attendance) for attendance in attendances], safe = False)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            attendance = attendance_service.create(data)
            return JsonResponse(serialize_attendance(attendance), status = 201)

        if request.method == "PUT":
            if attendance_id is None:
                return JsonResponse({"error": Messages.ATTENDANCE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            attendance = attendance_service.update(attendance_id, data, partial = False)
            return JsonResponse(serialize_attendance(attendance))

        if request.method == "PATCH":
            if attendance_id is None:
                return JsonResponse({"error": Messages.ATTENDANCE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            attendance = attendance_service.update(attendance_id, data, partial = True)
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
