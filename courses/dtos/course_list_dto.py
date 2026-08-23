class CourseListDTO:
    def __init__(self, id, code, name, credits, department, teacher):
        self.id = id
        self.code = code
        self.name = name
        self.credits = credits
        self.department = department
        self.teacher = teacher

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "credits": self.credits,
            "department": self.department,
            "teacher": self.teacher,
        }
