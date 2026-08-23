class CourseOfferingListDTO:
    def __init__(self, id, semester, academic_year, is_active, course, teacher, section):
        self.id = id
        self.semester = semester
        self.academic_year = academic_year
        self.is_active = is_active
        self.course = course
        self.teacher = teacher
        self.section = section

    def to_dict(self):
        return {
            "id": self.id,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "is_active": self.is_active,
            "course": self.course,
            "teacher": self.teacher,
            "section": self.section,
        }
