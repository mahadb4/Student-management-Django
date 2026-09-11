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
        course_offering_id,
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
        self.course_offering_id = course_offering_id
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
            "course_offering_id": self.course_offering_id,
            "profile_picture_key": self.profile_picture_key,
        }
