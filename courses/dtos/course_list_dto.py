class CourseListDTO:
    def __init__(self, id, code, name, credits, department_name, teacher_name):
        self.id = id
        self.code = code
        self.name = name
        self.credits = credits
        self.department_name = department_name
        self.teacher_name = teacher_name

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "credits": self.credits,
            "department_name": self.department_name,
            "teacher_name": self.teacher_name,
        }
