from django.contrib.auth.models import Group
from django.db import transaction
from common.constants import MAX_PROFILE_PICTURE_SIZE_BYTES, PROFILE_PICTURE_URL_EXPIRY_SECONDS
from common.messages import Messages
from common.permissions import apply_data_scope
from common.utils import apply_ordering, build_full_name, build_paginated_payload, extension_for_content_type
from teachers.mappers.teacher_mapper import TeacherMapper
from teachers.repositories.teacher_repository import ORDERING_FIELDS
from users.models import User

DEFAULT_TEMP_PASSWORD = "Abcd1234"

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
    def get_list(self,user,search,page,page_size,department_id=None,ordering=None):
        scope_token = self.cache.scope_token_for(user)
        filters = {"department_id": department_id, "ordering": ordering}

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search, department_id = department_id)
            queryset = apply_data_scope(user,queryset,'teacher')
            queryset = apply_ordering(queryset,ordering,ORDERING_FIELDS)
            return build_paginated_payload(queryset,page,page_size,TeacherMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token,search,page,page_size,loader,filters=filters)

    #Used only by the legacy server-rendered template view (teachers/views.py).
    #Not cached: it returns an unfiltered, unpaginated, unscoped queryset that the
    #React frontend never requests. Real list caching is get_list().
    def get_all(self): return self.repository.get_all()

    #user: an already-authenticated User to link (onboarding). Omit to have
    #a new User created for this Teacher (direct admin creation) - either
    #way, the Teacher is never saved without one.
    def create(self,data,user = None):
        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data, exclude_user_id = user.id if user else None)

        email = data["email"].strip()
        employee_id = data["employee_id"].strip()

        if self.repository.employee_id_exists(employee_id):
            raise ValueError(Messages.EMPLOYEE_ID_EXISTS.format(employee_id))

        with transaction.atomic():
            if user is None:
                user = User.objects.create_user(
                    email = email,
                    name = build_full_name(data["first_name"], data["last_name"]),
                    password = DEFAULT_TEMP_PASSWORD,
                    role = "teacher",
                    status = "approved",
                )
                group, _ = Group.objects.get_or_create(name = "TEACHER")
                user.groups.add(group)

            result = self.repository.create(data,user)

        self.cache.invalidate_on_write()
        return result

    def update(self,teacher_id,data,partial = False):
        teacher = self.repository.get(teacher_id)

        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial: data = self._merge_data(teacher,data)

        self.validator.validate(data,teacher_id,exclude_user_id = teacher.user_id)

        email = data["email"].strip()
        employee_id = data["employee_id"].strip()

        if User.objects.filter(email__iexact = email).exclude(id = teacher.user_id).exists():
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

    def generate_profile_picture_upload_url(self,teacher_id,content_type,s3_service):
        self.repository.get(teacher_id)

        extension = extension_for_content_type(content_type)
        key = f"teachers/{teacher_id}/profile.{extension}"
        upload_url = s3_service.generate_upload_url(key,content_type,expires_in = PROFILE_PICTURE_URL_EXPIRY_SECONDS)

        return {"upload_url":upload_url,"key":key,"content_type":content_type}

    def confirm_profile_picture_upload(self,teacher_id,key,s3_service):
        teacher = self.repository.get(teacher_id)

        expected_prefix = f"teachers/{teacher_id}/profile."
        if not key or not key.startswith(expected_prefix):
            raise ValueError(Messages.PROFILE_PICTURE_KEY_MISMATCH)

        metadata = s3_service.head_object(key)
        if metadata is None:
            raise ValueError(Messages.PROFILE_PICTURE_UPLOAD_NOT_FOUND)

        content_length = metadata.get("content_length") or 0
        if content_length > MAX_PROFILE_PICTURE_SIZE_BYTES:
            s3_service.delete_object(key)
            raise ValueError(Messages.PROFILE_PICTURE_TOO_LARGE.format(MAX_PROFILE_PICTURE_SIZE_BYTES // (1024 * 1024)))

        old_key = teacher.user.profile_picture_key
        self.repository.update_profile_picture_key(teacher,key)
        self.cache.invalidate_on_write(teacher_id)

        if old_key and old_key != key:
            s3_service.delete_object(old_key)

        return teacher

    def get_profile_picture_view_url(self,teacher_id,s3_service):
        teacher = self.get(teacher_id)
        if not teacher.user.profile_picture_key:
            return None

        return s3_service.generate_view_url(teacher.user.profile_picture_key,expires_in = PROFILE_PICTURE_URL_EXPIRY_SECONDS)

    def delete_profile_picture(self,teacher_id,s3_service):
        teacher = self.repository.get(teacher_id)
        if not teacher.user.profile_picture_key:
            return

        s3_service.delete_object(teacher.user.profile_picture_key)
        self.repository.update_profile_picture_key(teacher,None)
        self.cache.invalidate_on_write(teacher_id)

    def _merge_data(self,teacher,data):
        return {
            "first_name":data.get("first_name",teacher.effective_first_name),
            "last_name":data.get("last_name",teacher.effective_last_name),
            "employee_id":data.get("employee_id",teacher.employee_id),
            "email":data.get("email",teacher.effective_email),
            "phone_number":data.get("phone_number",teacher.phone_number),
            "department":data.get("department",teacher.department_id),
            "designation":data.get("designation",teacher.designation),
            "qualification":data.get("qualification",teacher.qualification),
            "gender":data.get("gender",teacher.user.gender),
            "date_of_birth":data.get("date_of_birth",teacher.user.date_of_birth),
            "date_of_joining":data.get("date_of_joining",teacher.date_of_joining),
            "salary":data.get("salary",teacher.salary),
            "address":data.get("address",teacher.user.address),
            "is_active":data.get("is_active",teacher.is_active),
        }