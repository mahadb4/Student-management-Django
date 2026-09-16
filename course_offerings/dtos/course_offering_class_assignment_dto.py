class CourseOfferingClassAssignmentDTO:
    def __init__(self, id, course_name, course_code, teacher_name, section_name):
        self.id = id
        self.course_name = course_name
        self.course_code = course_code
        self.teacher_name = teacher_name
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "teacher_name": self.teacher_name,
            "section_name": self.section_name,
        }
