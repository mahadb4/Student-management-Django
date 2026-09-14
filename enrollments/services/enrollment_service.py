from common.messages import Messages
from common.permissions import apply_data_scope
from common.utils import apply_ordering, build_paginated_payload
from enrollments.mappers.enrollment_mapper import EnrollmentMapper
from enrollments.repositories.enrollment_repository import ORDERING_FIELDS


class EnrollmentService:
    #cache is an EnrollmentCache (enrollments/cache/enrollment_cache.py).
    def __init__(self,validator,repository,cache):
        self.validator = validator
        self.repository = repository
        self.cache = cache

    #Not cached: the React admin page edits from the list row and never calls
    #the detail endpoint.
    def get(self,enrollment_id):
        return self.repository.get(enrollment_id)

    #GET /api/enrollments/?page=&page_size=&search=
    #Scoped per user: admin sees all, a teacher those in their own offerings,
    #a student their own.
    def get_list(self,user,search,page,page_size,ordering=None,course_offering_id=None):
        scope_token = self.cache.scope_token_for(user)
        filters = {"ordering": ordering, "course_offering_id": course_offering_id}

        def loader():
            queryset = self.repository.get_queryset_for_list(search = search, course_offering_id = course_offering_id)
            queryset = apply_data_scope(user,queryset,'enrollment')
            queryset = apply_ordering(queryset,ordering,ORDERING_FIELDS)
            return build_paginated_payload(queryset,page,page_size,EnrollmentMapper.to_list_dto)

        return self.cache.get_or_load_list(scope_token,search,page,page_size,loader,filters=filters)

    #Used only by the legacy server-rendered template view.
    def get_all(self):
        return self.repository.get_all()

    def create(self,data):
        if not isinstance(data,dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        self.validator.validate(data)
        self._validate_student_section(data["student"],data["course_offering"])

        student_id = data["student"]
        course_offering_id = data["course_offering"]

        if self.repository.enrollment_exists(student_id,course_offering_id):
            raise ValueError(Messages.ENROLLMENT_ALREADY_EXISTS.format(student_id,course_offering_id))

        result = self.repository.create(data)
        self.cache.invalidate_on_write()
        return result

    def update(self,enrollment_id,data,partial = False):
        enrollment = self.repository.get(enrollment_id)

        if not isinstance(data,dict):
            raise ValueError(Messages.REQUEST_DATA_MUST_BE_JSON_OBJECT)

        if partial:
            data = self._merge_data(enrollment,data)

        self.validator.validate(data)
        self._validate_student_section(data["student"],data["course_offering"])

        student_id = data["student"]
        course_offering_id = data["course_offering"]

        if self.repository.enrollment_exists(student_id,course_offering_id,enrollment_id):
            raise ValueError(Messages.ENROLLMENT_ALREADY_EXISTS.format(student_id,course_offering_id))

        result = self.repository.update(enrollment,data)
        self.cache.invalidate_on_write()
        return result

    def delete(self,enrollment_id):
        self.repository.delete(enrollment_id)
        self.cache.invalidate_on_write()

    def _validate_student_section(self,student_id,course_offering_id):
        from students.models import Student
        from course_offerings.models import CourseOffering

        student = Student.objects.get(id = student_id,is_deleted = False)
        course_offering = CourseOffering.objects.select_related(
            "course","teacher","section",
        ).get(id = course_offering_id,is_deleted = False)

        if student.section_id != course_offering.section_id:
            raise ValueError(Messages.ENROLLMENT_SECTION_MISMATCH)

        if not student.is_active:
            raise ValueError(Messages.STUDENT_INACTIVE)

        if not course_offering.is_active:
            raise ValueError(Messages.COURSE_OFFERING_INACTIVE)

        # A CourseOffering's own is_active flag isn't recomputed when its
        # Course/Teacher/Section is later deactivated (no cascade in this
        # system - see department/course/section/teacher services), so it can
        # go stale relative to its parents. Re-check them here rather than
        # only trusting the offering's own flag.
        if not course_offering.course.is_active:
            raise ValueError(Messages.COURSE_OFFERING_COURSE_INACTIVE)

        if not course_offering.teacher.is_active:
            raise ValueError(Messages.COURSE_OFFERING_TEACHER_INACTIVE)

        if course_offering.section_id and not course_offering.section.is_active:
            raise ValueError(Messages.COURSE_OFFERING_SECTION_INACTIVE)

    def _merge_data(self,enrollment,data):
        return {
            "student":data.get("student",enrollment.student_id),
            "course_offering":data.get("course_offering",enrollment.course_offering_id),
            "status":data.get("status",enrollment.status),
        }