class StudentListDTO:
    def __init__(self, id, first_name, last_name, student_email, is_active, department, section):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.student_email = student_email
        self.is_active = is_active
        self.department = department
        self.section = section

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "student_email": self.student_email,
            "is_active": self.is_active,
            "department": self.department,
            "section": self.section,
        }
