from common.repositories.base_repository import BaseRepository
from enrollments.models import Enrollment


class EnrollmentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Enrollment)

    def enrollment_exists(self, student_id, course_offering_id, exclude_id = None):
        query = self.model.objects.filter(student_id = student_id, course_offering_id = course_offering_id)

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
