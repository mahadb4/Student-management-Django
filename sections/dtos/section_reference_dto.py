class SectionReferenceDTO:
    def __init__(self, id, name, semester_number, department_name):
        self.id = id
        self.name = name
        self.semester_number = semester_number
        self.department_name = department_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "semester_number": self.semester_number,
            "department_name": self.department_name,
        }
