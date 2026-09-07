from common.messages import Messages
from common.utils import apply_ordering, build_paginated_payload
from courses.mappers.course_mapper import CourseMapper
from courses.repositories.course_repository import ORDERING_FIELDS
from courses.services.course_validator import CourseValidator


class CourseService:
    #cache is a CourseCache (courses/cache/course_cache.py).
    def __init__(self, validator, repository, cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    #Cached: the React admin page fetches the full record to populate its edit form.
    def get(self, course_id):
        return self.cache.get_or_load_detail(course_id, lambda: self.repository.get(course_id))

    #GET /api/courses/?page=&page_size=&search=&ordering=
    #page/page_size/ordering must already be normalized (common.utils.resolve_pagination_params/
    #resolve_ordering_param).
    def get_list(self, user, search, page, page_size, ordering = None):
        scope_token = self.cache.scope_token_for(user)
        filters = {"ordering": ordering}

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search)
            queryset = apply_ordering(queryset, ordering, ORDERING_FIELDS)
            return build_paginated_payload(queryset, page, page_size, CourseMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token, search, page, page_size, loader, filters = filters)

    #GET /api/courses/reference/ - dropdown projection, narrowed by department
    #and/or program semester. Values must arrive already normalized ("" -> None).
    def get_reference_list(self, user, department_id, semester_number, page, page_size):
        scope_token = self.cache.scope_token_for(user)
        filters = self.cache.reference_filters(department_id, semester_number)

        def loader():
            queryset = self.repository.get_queryset_for_reference(
                department_id = department_id,
                semester_number = semester_number,
            )
            return build_paginated_payload(queryset, page, page_size, CourseMapper.to_reference_dto)

        return self.cache.get_or_load_list(
            scope_token, None, page, page_size, loader, filters = filters,
        )

    #Used only by the legacy server-rendered template view (courses/views.py).
    def get_all(self):
        return self.repository.get_all()

    def create(self, data):
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        code = data["code"].strip()

        if self.repository.code_exists(code):
            raise ValueError(Messages.COURSE_CODE_EXISTS.format(code))

        result = self.repository.create(data)
        self.cache.invalidate_on_write()
        return result

    def update(self, course_id, data, partial = False):
        course = self.repository.get(course_id)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(course, data)

        self.validator.validate(data)

        code = data["code"].strip()

        if self.repository.code_exists(code, course_id):
            raise ValueError(Messages.COURSE_CODE_EXISTS.format(code))

        result = self.repository.update(course, data)
        self.cache.invalidate_on_write(course_id)
        return result

    def delete(self, course_id):
        self.repository.delete(course_id)
        self.cache.invalidate_on_write(course_id)

    def _merge_data(self, course, data):
        return {
            "name": data.get("name", course.name),
            "code": data.get("code", course.code),
            "description": data.get("description", course.description),
            "credits": data.get("credits", course.credits),
            "department": data.get("department", course.department_id),
            "teacher": data.get("teacher", course.teacher_id),
            "is_active": data.get("is_active", course.is_active),
        }
