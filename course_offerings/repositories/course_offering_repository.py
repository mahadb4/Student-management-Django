from django.db.models import Count, Q
from common.repositories.base_repository import BaseRepository
from course_offerings.models import CourseOffering

#Only Name sorting is supported (by design - see common.utils.apply_ordering()).
#"name" here means the offering's Course name, its only meaningful "name" field.
ORDERING_FIELDS = {
    "name": ("course__name",),
}
DEFAULT_ORDERING = "name"


class CourseOfferingRepository(BaseRepository):
    def __init__(self):
        super().__init__(CourseOffering)

    def get_queryset_for_teacher_list(self, teacher_id):
        # "My Classes" - the teacher's own offerings, with enrolled_students_count
        # computed server-side (distinct active enrollments) instead of the
        # frontend downloading every enrollment row just to count them.
        return self.model.objects.filter(teacher_id = teacher_id, is_deleted = False).select_related(
            "course", "section",
        ).only(
            "id", "semester", "academic_year", "is_active",
            "course__id", "course__name", "course__code",
            "section__id", "section__name",
        ).annotate(
            enrolled_students_count = Count(
                "enrollments",
                filter = Q(enrollments__status = "ACTIVE", enrollments__is_deleted = False),
                distinct = True,
            )
        ).order_by("id")

    def get_queryset_for_list(self, search = None, section_id = None, active_only = False):
        # order_by("id") here is only a default fallback for callers that don't
        # apply their own ordering afterward (e.g. get_queryset_for_discovery()
        # below, which is out of scope for sorting). CourseOfferingService.get_list()
        # calls common.utils.apply_ordering() on the result, which fully replaces
        # this with the requested ordering (see ORDERING_FIELDS above).
        queryset = self.model.objects.select_related("course", "teacher", "teacher__user", "section").only(
            "id", "semester", "academic_year", "is_active",
            "course__id", "course__name", "course__code",
            "teacher__id",
            "teacher__user_id", "teacher__user__name", "teacher__user__email",
            "section__id", "section__name",
        ).order_by("id")

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(course__name__icontains = term)
                    | Q(course__code__icontains = term)
                    | Q(teacher__user__name__icontains = term)
                    | Q(teacher__user__email__icontains = term)
                    | Q(section__name__icontains = term)
                )

        # Mirrors enrollment_service._validate_student_section's own
        # student.section_id != course_offering.section_id comparison exactly -
        # an exact-match filter (including passing None through to match
        # section-less offerings) so the dropdown only ever shows offerings
        # that would actually pass that validation, without embedding any new
        # business rule of its own.
        if section_id is not None:
            queryset = queryset.filter(section_id = section_id)

        # Opt-in: the admin CourseOfferings management table needs to keep
        # showing inactive offerings (default False, unchanged), but a picker
        # used to select an offering for a NEW Enrollment should not offer
        # inactive ones - see Enrollments.tsx's Course Offering PaginatedSelect.
        if active_only:
            queryset = queryset.filter(is_active = True)

        return queryset

    def get_queryset_for_discovery(self, section_id, search = None):
        # Offerings a student could browse and enrol in. Deliberately NOT narrowed
        # by apply_data_scope's 'courseoffering' student branch, which restricts to
        # offerings the student is ALREADY enrolled in - correct for reading their
        # own data, but it made the "Available Offerings" tab permanently empty.
        #
        # The narrowing here is an EXACT section match, mirroring
        # enrollment_service._validate_student_section's
        # `student.section_id != course_offering.section_id` comparison - including
        # section_id = None, where only section-less offerings match. It embeds no
        # rule of its own; enrolment itself is still authorised by that validator.
        #
        # is_deleted is filtered explicitly because this path bypasses
        # apply_data_scope, which is what normally supplies that filter.
        # is_active is filtered server-side for the same reason a student
        # shouldn't be able to select an inactive offering to enrol in - the
        # frontend already discards inactive rows client-side (belt-and-braces
        # left in place), but the backend is the actual source of truth.
        return self.get_queryset_for_list(search = search).filter(
            is_deleted = False,
            is_active = True,
            section_id = section_id,
        )

    def course_offering_exists(self,course_id,teacher_id,semester,academic_year,section_id,exclude_id = None):
        query = self.model.objects.filter(
            course_id = course_id,
            teacher_id = teacher_id,
            semester = semester,
            academic_year = academic_year,
            section_id = section_id,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self,data):
        offering = self.model()
        self.fill(offering,data)
        offering.save()
        return offering

    def update(self,offering,data):
        self.fill(offering,data)
        offering.save()
        return offering

    def fill(self,offering,data):
        offering.course_id = data["course"]
        offering.teacher_id = data["teacher"]
        offering.semester = data["semester"]
        offering.academic_year = data["academic_year"]
        offering.section_id = data["section"]
        offering.is_active = data.get("is_active",True) in (True,"on","true","True")