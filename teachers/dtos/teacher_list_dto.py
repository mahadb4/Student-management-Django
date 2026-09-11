class TeacherListDTO:
    def __init__(self, id, employee_id, name, email, designation, department_name, profile_picture_key = None):
        self.id = id
        self.employee_id = employee_id
        self.name = name
        self.email = email
        self.designation = designation
        self.department_name = department_name
        self.profile_picture_key = profile_picture_key

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "designation": self.designation,
            "department_name": self.department_name,
            "profile_picture_key": self.profile_picture_key,
        }
