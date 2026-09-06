from common.messages import Messages
from common.permissions import apply_data_scope
from common.utils import build_paginated_payload
from teachers.mappers.teacher_mapper import TeacherMapper

class TeacherService:
    #cache is a TeacherCache (teachers/cache/teacher_cache.py), not a raw CacheService.
    def __init__(self,validator,repository,cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    def get(self,teacher_id):
        return self.cache.get_or_load_detail(teacher_id,lambda: self.repository.get(teacher_id))

    #Serves the real React/API list flow: GET /api/teachers/?page=&page_size=&search=
    #page and page_size must already be normalized (common.utils.resolve_pagination_params)
    #so equivalent requests share one cache entry.
    #The cached value is the finished payload, built AFTER scope filtering, pagination
    #and DTO mapping, so a cache hit skips the database entirely.
    def get_list(self,user,search,page,page_size):
        scope_token = self.cache.scope_token_for(user)

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search)
            queryset = apply_data_scope(user,queryset,'teacher')
            return build_paginated_payload(queryset,page,page_size,TeacherMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token,search,page,page_size,loader)

    #Used only by the legacy server-rendered template view (teachers/views.py).
    #Not cached: it returns an unfiltered, unpaginated, unscoped queryset that the
    #React frontend never requests. Real list caching is get_list().
    def get_all(self): return self.repository.get_all()

    def create(self,data):
        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        email = data["email"].strip()
        employee_id = data["employee_id"].strip()

        if self.repository.email_exists(email):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(email))

        if self.repository.employee_id_exists(employee_id):
            raise ValueError(Messages.EMPLOYEE_ID_EXISTS.format(employee_id))

        result = self.repository.create(data)
        self.cache.invalidate_on_write()
        return result

    def update(self,teacher_id,data,partial = False):
        teacher = self.repository.get(teacher_id)

        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial: data = self._merge_data(teacher,data)

        self.validator.validate(data,teacher_id)

        email = data["email"].strip()
        employee_id = data["employee_id"].strip()

        if self.repository.email_exists(email,teacher_id):
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(email))

        if self.repository.employee_id_exists(employee_id,teacher_id):
            raise ValueError(Messages.EMPLOYEE_ID_EXISTS.format(employee_id))

        result = self.repository.update(teacher,data)
        self.cache.invalidate_on_write(teacher_id)
        return result

    def delete(self,teacher_id):
        result = self.repository.delete(teacher_id)
        self.cache.invalidate_on_write(teacher_id)
        return result

    def _merge_data(self,teacher,data):
        return {
            "first_name":data.get("first_name",teacher.first_name),
            "last_name":data.get("last_name",teacher.last_name),
            "employee_id":data.get("employee_id",teacher.employee_id),
            "email":data.get("email",teacher.email),
            "phone_number":data.get("phone_number",teacher.phone_number),
            "department":data.get("department",teacher.department_id),
            "designation":data.get("designation",teacher.designation),
            "qualification":data.get("qualification",teacher.qualification),
            "gender":data.get("gender",teacher.gender),
            "date_of_birth":data.get("date_of_birth",teacher.date_of_birth),
            "date_of_joining":data.get("date_of_joining",teacher.date_of_joining),
            "salary":data.get("salary",teacher.salary),
            "address":data.get("address",teacher.address),
            "is_active":data.get("is_active",teacher.is_active),
        }