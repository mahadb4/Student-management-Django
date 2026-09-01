class SectionReferenceDTO:
    def __init__(self, id, name, department_name):
        self.id = id
        self.name = name
        self.department_name = department_name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "department_name": self.department_name,
        }
