class CourseOfferingReferenceDTO:
    def __init__(
        self,
        id,
        semester,
        academic_year,
        is_active,
        course_name,
        course_code,
        teacher_name,
        section_name,
    ):
        self.id = id
        self.semester = semester
        self.academic_year = academic_year
        self.is_active = is_active
        self.course_name = course_name
        self.course_code = course_code
        self.teacher_name = teacher_name
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "is_active": self.is_active,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "teacher_name": self.teacher_name,
            "section_name": self.section_name,
        }
