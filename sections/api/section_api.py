from common.decorators import enforce_permissions
import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from sections.models import Section
from sections.repositories.section_repository import SectionRepository
from sections.services.section_service import SectionService
from sections.services.section_validator import SectionValidator

section_validator = SectionValidator()
section_repository = SectionRepository()
section_service = SectionService(section_validator, section_repository)

from common.utils import paginate_queryset
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

            sections = section_repository.get_queryset_for_list()
            return paginate_queryset(request, sections, SectionMapper.to_list_dto)

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
