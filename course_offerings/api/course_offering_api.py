import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from course_offerings.models import CourseOffering
from course_offerings.repositories.course_offering_repository import CourseOfferingRepository
from course_offerings.services.course_offering_service import CourseOfferingService
from course_offerings.services.course_offering_validator import CourseOfferingValidator

course_offering_validator = CourseOfferingValidator()
course_offering_repository = CourseOfferingRepository()
course_offering_service = CourseOfferingService(course_offering_validator, course_offering_repository)


def serialize_course_offering(offering):
    return {
        "id": offering.id,
        "course": offering.course_id,
        "teacher": offering.teacher_id,
        "semester": offering.semester,
        "academic_year": offering.academic_year,
        "section": offering.section,
        "is_active": offering.is_active,
        "created_at": offering.created_at,
        "updated_at": offering.updated_at,
    }



from common.decorators import enforce_permissions

@csrf_exempt
@enforce_permissions('course_offerings', 'courseoffering')
def course_offering_api(request, offering_id = None):
    try:
        from common.permissions import apply_data_scope
        from course_offerings.models import CourseOffering
        scoped_qs = apply_data_scope(request.user, CourseOffering.objects.all(), 'courseoffering')
        if offering_id is not None and not scoped_qs.filter(id=offering_id).exists():
            return JsonResponse({"error": "Forbidden"}, status=403)

        if request.method == "GET":
            if offering_id is not None:
                offering = course_offering_service.get(offering_id)
                return JsonResponse(serialize_course_offering(offering))

            offerings = scoped_qs
            return JsonResponse([serialize_course_offering(offering) for offering in offerings], safe = False)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            offering = course_offering_service.create(data)
            return JsonResponse(serialize_course_offering(offering), status = 201)

        if request.method == "PUT":
            if offering_id is None:
                return JsonResponse({"error": Messages.COURSE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            offering = course_offering_service.update(offering_id, data, partial = False)
            return JsonResponse(serialize_course_offering(offering))

        if request.method == "PATCH":
            if offering_id is None:
                return JsonResponse({"error": Messages.COURSE_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            offering = course_offering_service.update(offering_id, data, partial = True)
            return JsonResponse(serialize_course_offering(offering))

        if request.method == "DELETE":
            if offering_id is None:
                return JsonResponse({"error": Messages.COURSE_ID_REQUIRED}, status = 400)

            course_offering_service.delete(offering_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except CourseOffering.DoesNotExist:
        return JsonResponse({"error": Messages.NOT_FOUND}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.COURSE_CANNOT_BE_DELETED.format(offering_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)
