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

from common.utils import paginate_queryset


def serialize_course_offering(offering):
    return {
        "id": offering.id,
        "course": offering.course_id,
        "teacher": offering.teacher_id,
        "semester": offering.semester,
        "academic_year": offering.academic_year,
        "section": offering.section_id,
        "is_active": offering.is_active,
        "created_at": offering.created_at,
        "updated_at": offering.updated_at,
    }



from common.decorators import enforce_permissions
from course_offerings.mappers.course_offering_mapper import CourseOfferingMapper

@csrf_exempt
@enforce_permissions('course_offerings', 'courseoffering')
def course_offering_api(request, offering_id = None):
    try:
        from common.permissions import apply_data_scope
        from course_offerings.models import CourseOffering
        scoped_qs = apply_data_scope(request.user, CourseOffering.objects.all(), 'courseoffering')
        if offering_id is not None and not scoped_qs.filter(id = offering_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

        if request.method == "GET":
            if offering_id is not None:
                offering = course_offering_service.get(offering_id)
                return JsonResponse(serialize_course_offering(offering))

            search = request.GET.get("search", "").strip() or None

            # Optional dependent-dropdown filter: when a student is selected in
            # the Admin Enrollment form, only offerings matching that student's
            # own section should be selectable. Absent -> unfiltered (existing
            # behavior unchanged).
            section_id_param = request.GET.get("section_id", "").strip()
            section_id = int(section_id_param) if section_id_param.isdigit() else None

            offerings = apply_data_scope(
                request.user,
                course_offering_repository.get_queryset_for_list(search = search, section_id = section_id),
                'courseoffering',
            )
            return paginate_queryset(request, offerings, CourseOfferingMapper.to_list_dto)

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


@csrf_exempt
@enforce_permissions('course_offerings', 'courseoffering')
def course_offering_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope
    search = request.GET.get("search", "").strip() or None
    # Same scoping as the full list endpoint above - this is a field
    # projection, not a different visibility rule.
    offerings = apply_data_scope(request.user, course_offering_repository.get_queryset_for_list(search = search), 'courseoffering')
    return paginate_queryset(request, offerings, CourseOfferingMapper.to_reference_dto, default_page_size = 10)


def my_course_offerings_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND}, status = 404)

    qs = course_offering_repository.get_queryset_for_teacher_list(teacher.id)
    return paginate_queryset(request, qs, CourseOfferingMapper.to_teacher_list_dto, default_page_size = 10)
