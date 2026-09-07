class UserDetailDTO:
    def __init__(self, id, name, email, role, status, permissions, student_id, teacher_id):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.status = status
        self.permissions = permissions
        self.student_id = student_id
        self.teacher_id = teacher_id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "permissions": self.permissions,
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
        }
