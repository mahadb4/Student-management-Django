class CourseReferenceDTO:
    def __init__(self, id, name, code):
        self.id = id
        self.name = name
        self.code = code

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
        }
