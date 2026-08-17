import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from enrollments.models import Enrollment
from enrollments.repositories.enrollment_repository import EnrollmentRepository
from enrollments.services.enrollment_service import EnrollmentService
from enrollments.services.enrollment_validator import EnrollmentValidator

enrollment_validator = EnrollmentValidator()
enrollment_repository = EnrollmentRepository()
enrollment_service = EnrollmentService(enrollment_validator, enrollment_repository)


def serialize_enrollment(enrollment):
    return {
        "id": enrollment.id,
        "student": enrollment.student_id,
        "course_offering": enrollment.course_offering_id,
        "status": enrollment.status,
        "enrolled_at": enrollment.enrolled_at,
        "updated_at": enrollment.updated_at,
    }


@csrf_exempt
def enrollment_api(request, enrollment_id = None):
    try:
        if request.method == "GET":
            if enrollment_id is not None:
                enrollment = enrollment_service.get(enrollment_id)
                return JsonResponse(serialize_enrollment(enrollment))

            enrollments = enrollment_service.get_all()
            return JsonResponse([serialize_enrollment(enrollment) for enrollment in enrollments], safe = False)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            enrollment = enrollment_service.create(data)
            return JsonResponse(serialize_enrollment(enrollment), status = 201)

        if request.method == "PUT":
            if enrollment_id is None:
                return JsonResponse({"error": Messages.ENROLLMENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            enrollment = enrollment_service.update(enrollment_id, data, partial = False)
            return JsonResponse(serialize_enrollment(enrollment))

        if request.method == "PATCH":
            if enrollment_id is None:
                return JsonResponse({"error": Messages.ENROLLMENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            enrollment = enrollment_service.update(enrollment_id, data, partial = True)
            return JsonResponse(serialize_enrollment(enrollment))

        if request.method == "DELETE":
            if enrollment_id is None:
                return JsonResponse({"error": Messages.ENROLLMENT_ID_REQUIRED}, status = 400)

            enrollment_service.delete(enrollment_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Enrollment.DoesNotExist:
        return JsonResponse({"error": Messages.ENROLLMENT_NOT_FOUND_BY_ID.format(enrollment_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.ENROLLMENT_CANNOT_BE_DELETED.format(enrollment_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)
