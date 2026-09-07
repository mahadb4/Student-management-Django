class StudentListDTO:
    def __init__(self, id, name, student_email, department_name, section_name):
        self.id = id
        self.name = name
        self.student_email = student_email
        self.department_name = department_name
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
            "department_name": self.department_name,
            "section_name": self.section_name,
        }
