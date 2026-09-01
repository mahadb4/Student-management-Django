class StudentReferenceDTO:
    def __init__(self, id, name, student_email, section_id):
        self.id = id
        self.name = name
        self.student_email = student_email
        self.section_id = section_id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
            "section_id": self.section_id,
        }
