class CourseOfferingTeacherListDTO:
    def __init__(
        self,
        id,
        course_name,
        course_code,
        semester,
        academic_year,
        section_name,
        is_active,
        enrolled_students_count,
    ):
        self.id = id
        self.course_name = course_name
        self.course_code = course_code
        self.semester = semester
        self.academic_year = academic_year
        self.section_name = section_name
        self.is_active = is_active
        self.enrolled_students_count = enrolled_students_count

    def to_dict(self):
        return {
            "id": self.id,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "section_name": self.section_name,
            "is_active": self.is_active,
            "enrolled_students_count": self.enrolled_students_count,
        }
