class StudentListDTO:
    def __init__(self, id, name, student_email, department_name, section_name, placement_confirmed, profile_picture_key = None):
        self.id = id
        self.name = name
        self.student_email = student_email
        self.department_name = department_name
        self.section_name = section_name
        # Lets the Admin Students list show which rows still need academic
        # placement reviewed, without a separate list/endpoint.
        self.placement_confirmed = placement_confirmed
        self.profile_picture_key = profile_picture_key

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "student_email": self.student_email,
            "department_name": self.department_name,
            "section_name": self.section_name,
            "placement_confirmed": self.placement_confirmed,
            "profile_picture_key": self.profile_picture_key,
        }
