class TeacherListDTO:
    def __init__(self, id, employee_id, name, email, designation, department):
        self.id = id
        self.employee_id = employee_id
        self.name = name
        self.email = email
        self.designation = designation
        self.department = department

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "designation": self.designation,
            "department": self.department,
        }
