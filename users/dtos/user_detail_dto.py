class UserDetailDTO:
    def __init__(self, id, name, email, role, status, student_id, teacher_id, academic_review_pending):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.status = status
        self.student_id = student_id
        self.teacher_id = teacher_id
        # Student-only: True once onboarding has created the Student record
        # but an admin hasn't yet confirmed Department/Section. Drives the
        # frontend's redirect to the "Application Under Review" page instead
        # of the dashboard - never a raw status string, just this one flag.
        self.academic_review_pending = academic_review_pending

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
            "academic_review_pending": self.academic_review_pending,
        }
