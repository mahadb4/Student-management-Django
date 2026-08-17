from common.messages import Messages
from common.validators import CommonValidator
from enrollments.models import Enrollment
from students.models import Student
from course_offerings.models import CourseOffering


class EnrollmentValidator:
    def validate(self, data):
        CommonValidator.validate_required(data, [
            "student",
            "course_offering",
        ])

        student_id = data["student"]
        course_offering_id = data["course_offering"]

        if not Student.objects.filter(id = student_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_STUDENT.format(student_id))

        if not CourseOffering.objects.filter(id = course_offering_id, is_active = True).exists():
            raise ValueError(Messages.INVALID_COURSE_OFFERING.format(course_offering_id))

        status = data.get("status")

        if status is not None:
            valid = [choice[0] for choice in Enrollment.Status.choices]
            if status not in valid:
                raise ValueError(f"Invalid enrollment status. Must be one of: {', '.join(valid)}.")