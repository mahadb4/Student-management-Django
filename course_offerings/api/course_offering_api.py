import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.cache.cache_service import CacheService
from common.messages import Messages
from course_offerings.cache.course_offering_cache import CourseOfferingCache
from course_offerings.models import CourseOffering
from course_offerings.repositories.course_offering_repository import DEFAULT_ORDERING, ORDERING_FIELDS, CourseOfferingRepository
from course_offerings.services.course_offering_service import CourseOfferingService
from course_offerings.services.course_offering_validator import CourseOfferingValidator

course_offering_validator = CourseOfferingValidator()
course_offering_repository = CourseOfferingRepository()
course_offering_cache = CourseOfferingCache(CacheService())
course_offering_service = CourseOfferingService(course_offering_validator, course_offering_repository, course_offering_cache)

from common.utils import paginate_queryset, resolve_ordering_param, resolve_pagination_params


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

            # Opt-in, default unchanged: only a picker selecting an offering
            # for a NEW Enrollment sends this (see Enrollments.tsx) - the
            # CourseOfferings management table still needs inactive rows.
            active_only = request.GET.get("active_only", "").strip().lower() == "true"

            #Normalize paging/ordering before they reach the cache key. Scope
            #filtering, ordering, pagination and DTO mapping happen inside the service.
            page_number, page_size = resolve_pagination_params(request)
            ordering = resolve_ordering_param(request, ORDERING_FIELDS, DEFAULT_ORDERING)
            return JsonResponse(
                course_offering_service.get_list(
                    request.user, search, section_id, page_number, page_size, active_only, ordering,
                )
            )

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

    search = request.GET.get("search", "").strip() or None

    # Admins and teachers keep their normal data scope here. Students get
    # section-matched DISCOVERY instead of their enrolment-based scope, which
    # otherwise made the "Available Offerings" tab permanently empty (it returned
    # only offerings they were already enrolled in, which the frontend then
    # subtracted). Enrolment authorisation is unchanged - it is enforced by
    # enrollment_service._validate_student_section on POST. See
    # CourseOfferingService.get_reference_list().
    page_number, page_size = resolve_pagination_params(request, default_page_size = 10)

    return JsonResponse(
        course_offering_service.get_reference_list(
            request.user, search, page_number, page_size,
        )
    )


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
