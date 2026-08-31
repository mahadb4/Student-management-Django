class StudentReferenceDTO:
    def __init__(self, id, name, student_email):
        self.id = id
        self.name = name
        self.student_email = student_email

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
        }
