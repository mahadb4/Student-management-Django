from common.messages import Messages
from common.utils import apply_ordering, build_paginated_payload
from sections.mappers.section_mapper import SectionMapper
from sections.repositories.section_repository import ORDERING_FIELDS


class SectionService:
    #cache is a SectionCache (sections/cache/section_cache.py).
    def __init__(self, validator, repository, cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    #Not cached: the React admin page never calls the detail endpoint (it edits
    #straight from the list row), and update() needs a fresh instance anyway.
    def get(self, section_id):
        return self.repository.get(section_id)

    #Serves the real React/API list flow: GET /api/sections/?page=&page_size=&search=&ordering=
    #page, page_size and ordering must already be normalized (common.utils.resolve_pagination_params/
    #resolve_ordering_param).
    def get_list(self, user, search, page, page_size, ordering = None):
        scope_token = self.cache.scope_token_for(user)
        filters = {"ordering": ordering}

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search)
            queryset = apply_ordering(queryset, ordering, ORDERING_FIELDS)
            return build_paginated_payload(queryset, page, page_size, SectionMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token, search, page, page_size, loader, filters = filters)

    #Serves the dropdown/reference flow: GET /api/sections/reference/
    #The three filters are optional and callers send different subsets of them, so
    #all of them go into the cache key - see SectionCache.reference_filters().
    #Values must arrive already normalized ("" -> None) from the view.
    def get_reference_list(self, user, department_id, semester_number, academic_year, page, page_size):
        scope_token = self.cache.scope_token_for(user)
        filters = self.cache.reference_filters(department_id, semester_number, academic_year)

        def loader():
            queryset = self.repository.get_queryset_for_reference(
                department_id = department_id,
                semester_number = semester_number,
                academic_year = academic_year,
            )
            return build_paginated_payload(queryset, page, page_size, SectionMapper.to_reference_dto)

        return self.cache.get_or_load_list(
            scope_token, None, page, page_size, loader, filters = filters,
        )

    #Used only by the legacy server-rendered template view (sections/views.py).
    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        name = data["name"].strip()
        department_id = data["department"]
        semester_number = data["semester_number"]
        academic_year = data["academic_year"]

        if self.repository.section_exists(name, department_id, semester_number, academic_year):
            raise ValueError(Messages.SECTION_EXISTS)

        result = self.repository.create(data)
        #No object id: there is no detail cache to drop, only the list/reference ones.
        self.cache.invalidate_on_write()
        return result

    def update(self, section_id, data, partial = False):
        section = self.repository.get(section_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(section, data)

        self.validator.validate(data)

        name = data["name"].strip()
        department_id = data["department"]
        semester_number = data["semester_number"]
        academic_year = data["academic_year"]

        if self.repository.section_exists(name, department_id, semester_number, academic_year, section_id):
            raise ValueError(Messages.SECTION_EXISTS)

        result = self.repository.update(section, data)
        self.cache.invalidate_on_write()
        return result

    def delete(self, section_id):
        self.repository.delete(section_id)
        self.cache.invalidate_on_write()

    def _merge_data(self, section, data):
        return {
            "name": data.get("name", section.name),
            "department": data.get("department", section.department_id),
            "semester_number": data.get("semester_number", section.semester_number),
            "academic_year": data.get("academic_year", section.academic_year),
            "is_active": data.get("is_active", section.is_active),
        }
