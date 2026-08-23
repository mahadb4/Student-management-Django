class TeacherListDTO:
    def __init__(self, id, employee_id, first_name, last_name, email, designation, department):
        self.id = id
        self.employee_id = employee_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.designation = designation
        self.department = department

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "designation": self.designation,
            "department": self.department,
        }
