class EnrollmentReferenceDTO:
    def __init__(self, id, course_code, course_name, semester, academic_year, section_name):
        self.id = id
        self.course_code = course_code
        self.course_name = course_name
        self.semester = semester
        self.academic_year = academic_year
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "section_name": self.section_name,
        }
