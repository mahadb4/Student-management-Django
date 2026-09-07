from common.messages import Messages
from common.permissions import apply_data_scope
from common.utils import apply_ordering, build_paginated_payload
from students.mappers.student_mapper import StudentMapper
from students.repositories.student_repository import ORDERING_FIELDS

class StudentService:
    #cache is a StudentCache (students/cache/student_cache.py), not a raw CacheService.
    def __init__(self,validator,repository,cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    def get(self,student_id):
        return self.cache.get_or_load_detail(student_id,lambda: self.repository.get(student_id))

    #Serves the real React/API list flow: GET /api/students/?page=&page_size=&search=&department=&ordering=
    #page, page_size and ordering must already be normalized (common.utils.resolve_pagination_params/
    #resolve_ordering_param) so equivalent requests share one cache entry.
    #The cached value is the finished payload, built AFTER scope filtering, ordering and pagination,
    #and DTO mapping, so a cache hit skips the database entirely.
    def get_list(self,user,search,page,page_size,department_id=None,ordering=None):
        scope_token = self.cache.scope_token_for(user)
        filters = {"department_id": department_id, "ordering": ordering}

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search, department_id = department_id)
            queryset = apply_data_scope(user,queryset,'student')
            queryset = apply_ordering(queryset,ordering,ORDERING_FIELDS)
            return build_paginated_payload(queryset,page,page_size,StudentMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token,search,page,page_size,loader,filters=filters)

    #Used only by the legacy server-rendered template view (students/views.py).
    #Deliberately NOT cached: the old "students:all" key cached an unfiltered,
    #unpaginated, unscoped list that the React frontend never requested, which made
    #it look like list caching worked when it did not. Real list caching is get_list().
    def get_all(self):
        return self.repository.get_all()

    def create(self,data):
        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)
        self.validator.validate(data)

        if self.repository.email_exists(data["student_email"]):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(data["student_email"]))

        result = self.repository.create(data)
        self.cache.invalidate_on_write()
        return result

    def update(self,student_id,data,partial = False):
        student = self.repository.get(student_id)

        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial: data = self._merge_data(student,data)

        self.validator.validate(data)

        if self.repository.email_exists(data["student_email"],student_id):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(data["student_email"]))

        result = self.repository.update(student,data)
        self.cache.invalidate_on_write(student_id)
        return result

    def delete(self,student_id):
        result = self.repository.delete(student_id)
        self.cache.invalidate_on_write(student_id)
        return result

    def _merge_data(self,student,data):
        return {
            "first_name":data.get("first_name",student.first_name),
            "last_name":data.get("last_name",student.last_name),
            "student_email":data.get("student_email",student.student_email),
            "parents_phone_number":data.get("parents_phone_number",student.parents_phone_number),
            "date_of_birth":data.get("date_of_birth",student.date_of_birth),
            "gender":data.get("gender",student.gender),
            "address":data.get("address",student.address),
            "department":data.get("department",student.department_id),
            "section":data.get("section",student.section_id),
            "is_active":data.get("is_active",student.is_active),
        }