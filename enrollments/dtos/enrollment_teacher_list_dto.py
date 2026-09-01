class EnrollmentTeacherListDTO:
    def __init__(
        self,
        enrollment_id,
        course_offering_id,
        student_name,
        student_email,
        course_name,
        course_code,
        section_name,
        status,
    ):
        self.enrollment_id = enrollment_id
        self.course_offering_id = course_offering_id
        self.student_name = student_name
        self.student_email = student_email
        self.course_name = course_name
        self.course_code = course_code
        self.section_name = section_name
        self.status = status

    def to_dict(self):
        return {
            "enrollment_id": self.enrollment_id,
            "course_offering_id": self.course_offering_id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "section_name": self.section_name,
            "status": self.status,
        }
