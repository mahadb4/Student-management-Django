class EnrollmentReferenceDTO:
    def __init__(self, id, course_code, course_name):
        self.id = id
        self.course_code = course_code
        self.course_name = course_name

    def to_dict(self):
        return {
            "id": self.id,
            "course_code": self.course_code,
            "course_name": self.course_name,
        }
