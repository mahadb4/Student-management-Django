class SectionListDTO:
    def __init__(self, id, name, semester_number, academic_year, is_active, department_id, department_name):
        self.id = id
        self.name = name
        self.semester_number = semester_number
        self.academic_year = academic_year
        self.is_active = is_active
        self.department_id = department_id
        self.department_name = department_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "semester_number": self.semester_number,
            "academic_year": self.academic_year,
            "is_active": self.is_active,
            "department_id": self.department_id,
            "department_name": self.department_name,
        }
