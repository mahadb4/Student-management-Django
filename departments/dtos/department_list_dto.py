class DepartmentListDTO:
    def __init__(self, id, name, code, description, is_active):
        self.id = id
        self.name = name
        self.code = code
        self.description = description
        self.is_active = is_active

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
        }
