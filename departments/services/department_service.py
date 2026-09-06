from common.messages import Messages
from common.utils import build_paginated_payload
from departments.mappers.department_mapper import DepartmentMapper


class DepartmentService:
    #cache is a DepartmentCache (departments/cache/department_cache.py).
    def __init__(self, validator, repository, cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    #Not cached: the React admin page never calls the detail endpoint (it edits
    #straight from the list row), and update() needs a fresh instance anyway.
    def get(self, department_id):
        return self.repository.get(department_id)

    #Serves the real React/API list flow: GET /api/departments/?page=&page_size=&search=
    #page and page_size must already be normalized (common.utils.resolve_pagination_params).
    def get_list(self, user, search, page, page_size):
        scope_token = self.cache.scope_token_for(user)

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search)
            return build_paginated_payload(queryset, page, page_size, DepartmentMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token, search, page, page_size, loader)

    #Serves the dropdown/reference flow: GET /api/departments/reference/
    #Used by 7 call sites across 6 admin pages, so this is the highest-value
    #department cache. Same rows as get_list(), narrower projection, hence the
    #variant filter - see DepartmentCache.REFERENCE_FILTERS.
    def get_reference_list(self, user, page, page_size):
        scope_token = self.cache.scope_token_for(user)

        def loader():
            queryset = self.repository.get_queryset_for_reference()
            return build_paginated_payload(queryset, page, page_size, DepartmentMapper.to_reference_dto)

        return self.cache.get_or_load_list(
            scope_token, None, page, page_size, loader,
            filters = self.cache.REFERENCE_FILTERS,
        )

    #Used only by the legacy server-rendered template view (departments/views.py).
    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        name = data["name"].strip()
        code = data["code"].strip()

        if self.repository.name_exists(name):
            raise ValueError(Messages.DEPARTMENT_NAME_EXISTS.format(name))

        if self.repository.code_exists(code):
            raise ValueError(Messages.DEPARTMENT_CODE_EXISTS.format(code))

        result = self.repository.create(data)
        #No object id: there is no detail cache to drop, only the list/reference ones.
        self.cache.invalidate_on_write()
        return result

    def update(self, department_id, data, partial = False):
        department = self.repository.get(department_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(department, data)

        self.validator.validate(data)

        name = data["name"].strip()
        code = data["code"].strip()

        if self.repository.name_exists(name, department_id):
            raise ValueError(Messages.DEPARTMENT_NAME_EXISTS.format(name))

        if self.repository.code_exists(code, department_id):
            raise ValueError(Messages.DEPARTMENT_CODE_EXISTS.format(code))

        result = self.repository.update(department, data)
        self.cache.invalidate_on_write()
        return result

    def delete(self, department_id):
        self.repository.delete(department_id)
        self.cache.invalidate_on_write()

    def _merge_data(self, department, data):
        return {
            "name": data.get("name", department.name),
            "code": data.get("code", department.code),
            "description": data.get("description", department.description),
            "is_active": data.get("is_active", department.is_active),
        }