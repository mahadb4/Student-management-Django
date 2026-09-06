from common.decorators import enforce_permissions
import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.cache.cache_service import CacheService
from common.messages import Messages
from sections.cache.section_cache import SectionCache
from sections.models import Section
from sections.repositories.section_repository import SectionRepository
from sections.services.section_service import SectionService
from sections.services.section_validator import SectionValidator

section_validator = SectionValidator()
section_repository = SectionRepository()
section_cache = SectionCache(CacheService())
section_service = SectionService(section_validator, section_repository, section_cache)

from common.utils import paginate_queryset, resolve_pagination_params
from sections.mappers.section_mapper import SectionMapper


def serialize_section(section):
    return {
        "id": section.id,
        "name": section.name,
        "department": section.department_id,
        "semester_number": section.semester_number,
        "academic_year": section.academic_year,
        "is_active": section.is_active,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
    }


@csrf_exempt
@enforce_permissions('sections', 'section')
def section_api(request, section_id = None):
    try:
        if request.method == "GET":
            if section_id is not None:
                section = section_service.get(section_id)
                return JsonResponse(serialize_section(section))

            search = request.GET.get("search", "").strip() or None
            #Normalize paging first so the cache key reflects the effective page,
            #not the raw query string. Pagination and DTO mapping happen inside
            #the service, behind the Redis list cache.
            page_number, page_size = resolve_pagination_params(request)
            return JsonResponse(
                section_service.get_list(request.user, search, page_number, page_size)
            )

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            section = section_service.create(data)
            return JsonResponse(serialize_section(section), status = 201)

        if request.method == "PUT":
            if section_id is None:
                return JsonResponse({"error": Messages.SECTION_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            section = section_service.update(section_id, data, partial = False)
            return JsonResponse(serialize_section(section))

        if request.method == "PATCH":
            if section_id is None:
                return JsonResponse({"error": Messages.SECTION_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            section = section_service.update(section_id, data, partial = True)
            return JsonResponse(serialize_section(section))

        if request.method == "DELETE":
            if section_id is None:
                return JsonResponse({"error": Messages.SECTION_ID_REQUIRED}, status = 400)

            section_service.delete(section_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Section.DoesNotExist:
        return JsonResponse({"error": Messages.SECTION_NOT_FOUND_BY_ID.format(section_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.SECTION_CANNOT_BE_DELETED.format(section_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('sections', 'section')
def section_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    #"" -> None here, BEFORE the values reach the cache key, so that requests
    #selecting the same rows share one entry.
    department_id = request.GET.get("department_id") or None
    semester_number = request.GET.get("semester_number") or None
    academic_year = request.GET.get("academic_year") or None

    #default_page_size = 10 must match what the service caches under, so the key
    #reflects the page size actually served.
    page_number, page_size = resolve_pagination_params(request, default_page_size = 10)

    return JsonResponse(
        section_service.get_reference_list(
            request.user, department_id, semester_number, academic_year, page_number, page_size,
        )
    )
