class StudentEnrollmentListDTO:
    def __init__(
        self,
        id,
        status,
        semester,
        academic_year,
        course_name,
        course_code,
        teacher_name,
        section_name,
        teacher_id = None,
        profile_picture_key = None,
    ):
        self.id = id
        self.status = status
        self.semester = semester
        self.academic_year = academic_year
        self.course_name = course_name
        self.course_code = course_code
        self.teacher_name = teacher_name
        self.section_name = section_name
        self.teacher_id = teacher_id
        self.profile_picture_key = profile_picture_key

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "teacher_name": self.teacher_name,
            "section_name": self.section_name,
            "teacher_id": self.teacher_id,
            #Raw S3 key only - the API layer converts this into a fresh
            #presigned profile_picture_url after this dict leaves paginate_queryset.
            "profile_picture_key": self.profile_picture_key,
        }
