class CourseOfferingAttendanceReferenceDTO:
    def __init__(self, id, course_code, section_name):
        self.id = id
        self.course_code = course_code
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "course_code": self.course_code,
            "section_name": self.section_name,
        }
