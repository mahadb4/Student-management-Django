from common.repositories.base_repository import BaseRepository
from enrollments.models import Enrollment


class EnrollmentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Enrollment)

    def get_queryset_for_list(self):
        return self.model.objects.select_related("student", "course_offering__course", "course_offering__section").only(
            "id", "status",
            "student__id", "student__first_name", "student__last_name", "student__student_email",
            "course_offering__id", "course_offering__semester", "course_offering__academic_year",
            "course_offering__course__id", "course_offering__course__name", "course_offering__course__code",
            "course_offering__section__id", "course_offering__section__name",
        )

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