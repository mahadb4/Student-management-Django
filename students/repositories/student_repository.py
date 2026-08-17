from common.repositories.base_repository import BaseRepository
from students.models import Student

class StudentRepository(BaseRepository):
    def __init__(self):
        super().__init__(Student)

    def email_exists(self, email, exclude_id=None):
        query = self.model.objects.filter(student_email=email)

        if exclude_id is not None:
            query = query.exclude(id=exclude_id)

        return query.exists()

    def create(self, data):
        student = self.model()
        self.fill(student, data)
        student.save()
        return student

    def update(self, student, data):
        self.fill(student, data)
        student.save()
        return student

    def fill(self, student, data):
        student.first_name = data["first_name"].strip()
        student.last_name = data["last_name"].strip()
        student.student_email = data["student_email"].strip()
        student.parents_phone_number = data["parents_phone_number"].strip()
        student.date_of_birth = data["date_of_birth"]
        student.gender = data["gender"]
        student.address = (data.get("address") or "").strip()
        student.student_group = data["student_group"].strip()
        student.department_id = data.get("department")
        student.teacher_id = data.get("teacher")
        student.is_active = data.get("is_active", True) in (True, "on", "true", "True")