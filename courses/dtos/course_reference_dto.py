class CourseReferenceDTO:
    def __init__(self, id, name, code, department_id, department_name):
        self.id = id
        self.name = name
        self.code = code
        self.department_id = department_id
        self.department_name = department_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "department_id": self.department_id,
            "department_name": self.department_name,
        }
