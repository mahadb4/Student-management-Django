class UserListDTO:
    def __init__(self, id, name, email, role, status):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
        }
