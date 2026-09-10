class EnrollmentTeacherListDTO:
    def __init__(
        self,
        enrollment_id,
        student_id,
        student_name,
        student_email,
        course_name,
        course_code,
        section_name,
        status,
        profile_picture_key = None,
    ):
        self.enrollment_id = enrollment_id
        self.student_id = student_id
        self.student_name = student_name
        self.student_email = student_email
        self.course_name = course_name
        self.course_code = course_code
        self.section_name = section_name
        self.status = status
        self.profile_picture_key = profile_picture_key

    def to_dict(self):
        return {
            "enrollment_id": self.enrollment_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "section_name": self.section_name,
            "status": self.status,
            #Raw S3 key only - the API layer converts this into a fresh
            #presigned profile_picture_url after this dict leaves paginate_queryset.
            "profile_picture_key": self.profile_picture_key,
        }
