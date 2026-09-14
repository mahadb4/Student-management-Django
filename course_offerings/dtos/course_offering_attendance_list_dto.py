class CourseOfferingAttendanceListDTO:
    def __init__(self, id, course_name, section_name):
        self.id = id
        self.course_name = course_name
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "course_name": self.course_name,
            "section_name": self.section_name,
        }
