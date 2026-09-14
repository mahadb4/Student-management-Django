from django.contrib.auth.models import Group
from django.db import transaction
from common.constants import MAX_PROFILE_PICTURE_SIZE_BYTES, PROFILE_PICTURE_URL_EXPIRY_SECONDS
from common.messages import Messages
from common.permissions import apply_data_scope
from common.services.image_service import ImageProcessingError, generate_avatar_thumbnail
from common.utils import apply_ordering, build_full_name, build_paginated_payload, extension_for_content_type
from students.mappers.student_mapper import StudentMapper
from students.repositories.student_repository import ORDERING_FIELDS
from users.models import User

DEFAULT_TEMP_PASSWORD = "Abcd1234"

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

    #user: an already-authenticated User to link (onboarding). Omit to have
    #a new User created for this Student (direct admin creation) - either
    #way, the Student is never saved without one.
    def create(self,data,user = None):
        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)
        self.validator.validate(data)

        email = data["student_email"].strip()
        exclude_id = user.id if user else None

        if User.objects.filter(email__iexact = email).exclude(id = exclude_id or 0).exists():
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(email))

        with transaction.atomic():
            if user is None:
                user = User.objects.create_user(
                    email = email,
                    name = build_full_name(data["first_name"], data["last_name"]),
                    password = DEFAULT_TEMP_PASSWORD,
                    role = "student",
                    status = "approved",
                )
                group, _ = Group.objects.get_or_create(name = "STUDENT")
                user.groups.add(group)

            result = self.repository.create(data,user)

        self.cache.invalidate_on_write()
        return result

    def update(self,student_id,data,partial = False):
        student = self.repository.get(student_id)

        if not isinstance(data,dict): raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial: data = self._merge_data(student,data)

        self.validator.validate(data)

        new_email = data["student_email"].strip()

        if User.objects.filter(email__iexact = new_email).exclude(id = student.user_id).exists():
            raise ValueError(Messages.EMAIL_ALREADY_EXISTS.format(new_email))

        result = self.repository.update(student,data)
        self.cache.invalidate_on_write(student_id)
        return result

    def delete(self,student_id):
        result = self.repository.delete(student_id)
        self.cache.invalidate_on_write(student_id)
        return result

    def generate_profile_picture_upload_url(self,student_id,content_type,s3_service):
        self.repository.get(student_id)

        extension = extension_for_content_type(content_type)
        key = f"students/{student_id}/profile.{extension}"
        upload_url = s3_service.generate_upload_url(key,content_type,expires_in = PROFILE_PICTURE_URL_EXPIRY_SECONDS)

        return {"upload_url":upload_url,"key":key,"content_type":content_type}

    def confirm_profile_picture_upload(self,student_id,key,s3_service):
        student = self.repository.get(student_id)

        expected_prefix = f"students/{student_id}/profile."
        if not key or not key.startswith(expected_prefix):
            raise ValueError(Messages.PROFILE_PICTURE_KEY_MISMATCH)

        metadata = s3_service.head_object(key)
        if metadata is None:
            raise ValueError(Messages.PROFILE_PICTURE_UPLOAD_NOT_FOUND)

        content_length = metadata.get("content_length") or 0
        if content_length > MAX_PROFILE_PICTURE_SIZE_BYTES:
            s3_service.delete_object(key)
            raise ValueError(Messages.PROFILE_PICTURE_TOO_LARGE.format(MAX_PROFILE_PICTURE_SIZE_BYTES // (1024 * 1024)))

        # Replace the just-uploaded original with a small square thumbnail -
        # see TeacherService.confirm_profile_picture_upload for why.
        try:
            thumbnail_bytes, thumbnail_content_type = generate_avatar_thumbnail(
                s3_service.get_object_bytes(key), metadata.get("content_type"),
            )
        except ImageProcessingError as e:
            s3_service.delete_object(key)
            raise ValueError(str(e))

        s3_service.put_object_bytes(key, thumbnail_bytes, thumbnail_content_type)

        old_key = student.user.profile_picture_key
        self.repository.update_profile_picture_key(student,key)
        self.cache.invalidate_on_write(student_id)

        if old_key and old_key != key:
            s3_service.delete_object(old_key)

        return student

    def get_profile_picture_view_url(self,student_id,s3_service):
        student = self.get(student_id)
        if not student.user.profile_picture_key:
            return None

        return s3_service.generate_view_url(student.user.profile_picture_key,expires_in = PROFILE_PICTURE_URL_EXPIRY_SECONDS)

    def delete_profile_picture(self,student_id,s3_service):
        student = self.repository.get(student_id)
        if not student.user.profile_picture_key:
            return

        s3_service.delete_object(student.user.profile_picture_key)
        self.repository.update_profile_picture_key(student,None)
        self.cache.invalidate_on_write(student_id)

    def _merge_data(self,student,data):
        return {
            "first_name":data.get("first_name",student.effective_first_name),
            "last_name":data.get("last_name",student.effective_last_name),
            "student_email":data.get("student_email",student.effective_email),
            "parents_phone_number":data.get("parents_phone_number",student.parents_phone_number),
            "date_of_birth":data.get("date_of_birth",student.user.date_of_birth),
            "gender":data.get("gender",student.user.gender),
            "address":data.get("address",student.user.address),
            "department":data.get("department",student.department_id),
            "section":data.get("section",student.section_id),
            "is_active":data.get("is_active",student.is_active),
        }