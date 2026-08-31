class StudentListDTO:
    def __init__(self, id, name, student_email, is_active, department, section):
        self.id = id
        self.name = name
        self.student_email = student_email
        self.is_active = is_active
        self.department = department
        self.section = section

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
            "is_active": self.is_active,
            "department": self.department,
            "section": self.section,
        }
