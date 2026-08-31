class StudentListDTO:
    def __init__(self, id, name, student_email, is_active, department_id, department_name, section_id, section_name):
        self.id = id
        self.name = name
        self.student_email = student_email
        self.is_active = is_active
        self.department_id = department_id
        self.department_name = department_name
        self.section_id = section_id
        self.section_name = section_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
            "is_active": self.is_active,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "section_id": self.section_id,
            "section_name": self.section_name,
        }
