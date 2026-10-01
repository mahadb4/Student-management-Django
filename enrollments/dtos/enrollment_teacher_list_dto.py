class EnrollmentTeacherListDTO:
    def __init__(
        self,
        enrollment_id,
        student_id,
        student_name,
        student_email,
        status,
        profile_picture_key = None,
    ):
        self.enrollment_id = enrollment_id
        self.student_id = student_id
        self.student_name = student_name
        self.student_email = student_email
        self.status = status
        self.profile_picture_key = profile_picture_key

    def to_dict(self):
        return {
            "enrollment_id": self.enrollment_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "status": self.status,
            "profile_picture_key": self.profile_picture_key,
        }
