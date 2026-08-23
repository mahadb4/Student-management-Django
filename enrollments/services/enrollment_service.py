from common.messages import Messages


class EnrollmentService:
    def __init__(self,validator,repository):
        self.validator = validator
        self.repository = repository

    def get(self,enrollment_id):
        return self.repository.get(enrollment_id)

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

        return self.repository.create(data)

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

        return self.repository.update(enrollment,data)

    def delete(self,enrollment_id):
        self.repository.delete(enrollment_id)

    def _validate_student_section(self,student_id,course_offering_id):
        from students.models import Student
        from course_offerings.models import CourseOffering

        student = Student.objects.get(id = student_id,is_deleted = False)
        course_offering = CourseOffering.objects.get(id = course_offering_id,is_deleted = False)

        if student.section_id != course_offering.section_id:
            raise ValueError(Messages.ENROLLMENT_SECTION_MISMATCH)

        if not student.is_active:
            raise ValueError(Messages.STUDENT_INACTIVE)

        if not course_offering.is_active:
            raise ValueError(Messages.COURSE_OFFERING_INACTIVE)

    def _merge_data(self,enrollment,data):
        return {
            "student":data.get("student",enrollment.student_id),
            "course_offering":data.get("course_offering",enrollment.course_offering_id),
            "status":data.get("status",enrollment.status),
        }