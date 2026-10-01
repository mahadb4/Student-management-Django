class EnrollmentAttendancePickerDTO:
    def __init__(self, id, student_name, course_code):
        self.id = id
        self.student_name = student_name
        self.course_code = course_code

    def to_dict(self):
        return {
            "id": self.id,
            "student_name": self.student_name,
            "course_code": self.course_code,
        }
