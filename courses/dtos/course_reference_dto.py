class CourseReferenceDTO:
    def __init__(self, id, name, code, semester_number, department_id, department_name):
        self.id = id
        self.name = name
        self.code = code
        self.semester_number = semester_number
        self.department_id = department_id
        self.department_name = department_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "semester_number": self.semester_number,
            "department_id": self.department_id,
            "department_name": self.department_name,
        }
