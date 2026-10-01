class EnrollmentListDTO:
    def __init__(
        self,
        id,
        status,
        student_name,
        student_email,
        semester,
        academic_year,
        course_name,
        course_code,
        section_name,
    ):
        self.id = id
        self.status = status
        self.student_name = student_name
        self.student_email = student_email
        self.semester = semester
        self.academic_year = academic_year
        self.course_name = course_name
        self.course_code = course_code
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "section_name": self.section_name,
        }
