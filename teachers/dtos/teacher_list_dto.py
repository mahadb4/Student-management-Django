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
            #Raw S3 key only - never a URL. The API layer converts this into a
            #fresh presigned profile_picture_url AFTER this dict leaves the list
            #cache, so a signed URL is never itself written to Redis.
            "profile_picture_key": self.profile_picture_key,
        }
