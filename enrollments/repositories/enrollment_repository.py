from django.db.models import Q
from common.repositories.base_repository import BaseRepository
from enrollments.models import Enrollment

#Only Name sorting is supported (by design - see common.utils.apply_ordering()).
#"name" is the enrolled Student's name.
ORDERING_FIELDS = {
    "name": ("student__user__name",),
}
DEFAULT_ORDERING = "name"


class EnrollmentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Enrollment)

    def get_queryset_for_list(self, search = None, course_offering_id = None):
        #No .order_by() here - final ordering is applied by the service, after
        #apply_data_scope(), via common.utils.apply_ordering() (see ORDERING_FIELDS above).
        queryset = self.model.objects.select_related(
            "student__user", "course_offering__course", "course_offering__section",
            "course_offering__teacher__user",
        ).only(
            "id", "status",
            "student__id", "student__user_id", "student__user__name", "student__user__email",
            "student__user__profile_picture_key",
            "course_offering__id", "course_offering__semester", "course_offering__academic_year",
            "course_offering__course__id", "course_offering__course__name", "course_offering__course__code",
            "course_offering__section__id", "course_offering__section__name",
            "course_offering__teacher__id",
            "course_offering__teacher__user_id", "course_offering__teacher__user__name",
            "course_offering__teacher__user__email", "course_offering__teacher__user__profile_picture_key",
        )

        if search:
            for term in search.split():
                queryset = queryset.filter(
                    Q(student__user__name__icontains = term)
                    | Q(student__user__email__icontains = term)
                    | Q(course_offering__course__name__icontains = term)
                    | Q(course_offering__course__code__icontains = term)
                )

        # Used by the Admin Attendance Add/Edit modal's enrollment picker
        # (?course_offering_id=) to scope student choices to the selected
        # offering only - restricted to ACTIVE so a dropped/completed
        # enrollment isn't offered for marking new attendance.
        if course_offering_id:
            queryset = queryset.filter(
                course_offering_id = course_offering_id,
                status = Enrollment.Status.ACTIVE,
            )

        return queryset

    def get_by_student_and_offering(self, student_id, course_offering_id):
        return self.model.objects.filter(
            student_id = student_id,
            course_offering_id = course_offering_id,
            is_deleted = False,
        ).first()

    def get_active_by_student(self, student_id):
        return self.model.objects.filter(
            student_id = student_id,
            status = Enrollment.Status.ACTIVE,
            is_deleted = False,
        )

    def get_active_by_offering(self, course_offering_id):
        return self.model.objects.filter(
            course_offering_id = course_offering_id,
            status = Enrollment.Status.ACTIVE,
            is_deleted = False,
        )

    def enrollment_exists(self, student_id, course_offering_id, exclude_id = None):
        query = self.model.objects.filter(
            student_id = student_id,
            course_offering_id = course_offering_id,
            is_deleted = False,
        )

        if exclude_id is not None:
            query = query.exclude(id = exclude_id)

        return query.exists()

    def create(self, data):
        enrollment = self.model()
        self.fill(enrollment, data)
        enrollment.save()
        return enrollment

    def update(self, enrollment, data):
        self.fill(enrollment, data)
        enrollment.save()
        return enrollment

    def fill(self, enrollment, data):
        enrollment.student_id = data["student"]
        enrollment.course_offering_id = data["course_offering"]
        enrollment.status = data.get("status", Enrollment.Status.ACTIVE)