from common.messages import Messages
from common.permissions import apply_data_scope, get_scope_identity
from common.utils import build_paginated_payload
from course_offerings.mappers.course_offering_mapper import CourseOfferingMapper


class CourseOfferingService:
    #cache is a CourseOfferingCache (course_offerings/cache/course_offering_cache.py).
    def __init__(self,validator,repository,cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    #Not cached: the React admin page edits from the list row and never calls
    #the detail endpoint.
    def get(self,offering_id):
        return self.repository.get(offering_id)

    #GET /api/course_offerings/?page=&page_size=&search=&section_id=
    #Scoped per user: admin sees all, a teacher their own, a student those they
    #are enrolled in.
    def get_list(self,user,search,section_id,page,page_size):
        scope_token = self.cache.scope_token_for(user)
        filters = {"section_id": section_id}

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search, section_id = section_id)
            queryset = apply_data_scope(user,queryset,'courseoffering')
            return build_paginated_payload(queryset,page,page_size,CourseOfferingMapper.to_list_dto)

        return self.cache.get_or_load_list(
            scope_token,search,page,page_size,loader,filters = filters,
        )

    #GET /api/course_offerings/reference/
    #Serves two different questions through one endpoint:
    #  * admin/teacher -> a lookup over the offerings they are entitled to see,
    #    so their normal data scope still applies.
    #  * student -> the "Available Offerings" discovery tab, which is NOT their
    #    own data. Narrowed by an exact section match instead, mirroring
    #    enrollment_service._validate_student_section. Enrolment itself is still
    #    authorised by that validator on POST; this only widens what is visible
    #    to browse, never what may be enrolled in.
    def get_reference_list(self,user,search,page,page_size):
        scope_token = self.cache.reference_scope_token_for(user)

        def loader():
            queryset = self._reference_queryset(user,search)
            return build_paginated_payload(queryset,page,page_size,CourseOfferingMapper.to_reference_dto)

        return self.cache.get_or_load_list(
            scope_token,search,page,page_size,loader,
            filters = self.cache.REFERENCE_FILTERS,
        )

    def _reference_queryset(self,user,search):
        kind,profile = get_scope_identity(user)

        if kind == "student":
            return self.repository.get_queryset_for_discovery(
                section_id = profile.section_id, search = search,
            )

        return apply_data_scope(
            user,self.repository.get_queryset_for_list(search = search),'courseoffering',
        )

    #Used only by the legacy server-rendered template view.
    def get_all(self):
        return self.repository.get_all()

    def create(self,data):
        if not isinstance(data,dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)

        course_id = data["course"]
        teacher_id = data["teacher"]
        semester = data["semester"]
        academic_year = data["academic_year"]
        section_id = data["section"]

        if self.repository.course_offering_exists(
            course_id,
            teacher_id,
            semester,
            academic_year,
            section_id,
        ):
            raise ValueError(Messages.COURSE_OFFERING_EXISTS)

        result = self.repository.create(data)
        self.cache.invalidate_on_write()
        return result

    def update(self,offering_id,data,partial = False):
        offering = self.repository.get(offering_id)

        if not isinstance(data,dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(offering,data)

        self.validator.validate(data)

        course_id = data["course"]
        teacher_id = data["teacher"]
        semester = data["semester"]
        academic_year = data["academic_year"]
        section_id = data["section"]

        if self.repository.course_offering_exists(
            course_id,
            teacher_id,
            semester,
            academic_year,
            section_id,
            offering_id,
        ):
            raise ValueError(Messages.COURSE_OFFERING_EXISTS)

        result = self.repository.update(offering,data)
        self.cache.invalidate_on_write()
        return result

    def delete(self,offering_id):
        self.repository.delete(offering_id)
        self.cache.invalidate_on_write()

    def _merge_data(self,offering,data):
        return {
            "course":data.get("course",offering.course_id),
            "teacher":data.get("teacher",offering.teacher_id),
            "semester":data.get("semester",offering.semester),
            "academic_year":data.get("academic_year",offering.academic_year),
            "section":data.get("section",offering.section_id),
            "is_active":data.get("is_active",offering.is_active),
        }