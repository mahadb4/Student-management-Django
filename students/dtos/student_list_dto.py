class StudentListDTO:
    def __init__(self, id, name, student_email, department_name, section_name, profile_picture_key = None):
        self.id = id
        self.name = name
        self.student_email = student_email
        self.department_name = department_name
        self.section_name = section_name
        self.profile_picture_key = profile_picture_key

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
            "department_name": self.department_name,
            "section_name": self.section_name,
            #Raw S3 key only - never a URL. The API layer converts this into a
            #fresh presigned profile_picture_url AFTER this dict leaves the list
            #cache, so a signed URL is never itself written to Redis.
            "profile_picture_key": self.profile_picture_key,
        }
