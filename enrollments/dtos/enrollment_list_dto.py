class EnrollmentListDTO:
    def __init__(self, id, status, student, course_offering):
        self.id = id
        self.status = status
        self.student = student
        self.course_offering = course_offering

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "student": self.student,
            "course_offering": self.course_offering,
        }
