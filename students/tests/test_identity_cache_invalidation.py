from datetime import date
from django.test import TestCase
from common.cache.cache_service import CacheService
from departments.models import Department
from sections.models import Section
from students.cache.student_cache import StudentCache
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from users.models import User


class FakeAdmin:
    is_authenticated = True
    is_superuser = True


#Identity updates must invalidate the Student cache.
class StudentIdentityCacheInvalidationTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        self.cache = StudentCache(CacheService())
        self.service = StudentService(StudentValidator(), StudentRepository(), self.cache)
        self.admin = FakeAdmin()

        self.user = User.objects.create_user(
            email = "cache-student@example.com", name = "Before Update", password = "x", role = "student",
        )
        self.student = Student.objects.create(
            user = self.user, parents_phone_number = "1234567",
            date_of_birth = date(2000, 1, 1), gender = "M",
            department = self.department, section = self.section,
        )

    def _full_update_data(self, student, **overrides):
        data = {
            "first_name": student.effective_first_name,
            "last_name": student.effective_last_name,
            "student_email": student.effective_email,
            "parents_phone_number": student.parents_phone_number,
            "date_of_birth": student.date_of_birth,
            "gender": student.gender,
            "address": student.address,
            "department": student.department_id,
            "section": student.section_id,
            "is_active": student.is_active,
        }
        data.update(overrides)
        return data

    def test_identity_update_invalidates_detail_cache(self):
        # Warm the detail cache with the OLD name.
        before = self.service.get(self.student.id)
        self.assertEqual(before.effective_first_name, "Before")

        data = self._full_update_data(self.student, first_name = "After", last_name = "Update")
        self.service.update(self.student.id, data)

        # A stale cache would still return "Before" here.
        after = self.service.get(self.student.id)
        self.assertEqual(after.effective_first_name, "After")

    def test_identity_update_invalidates_list_cache(self):
        self.service.get_list(self.admin, None, 1, 10, ordering = "name")  # warm list cache

        data = self._full_update_data(self.student, first_name = "ListUpdated", last_name = "Name")
        self.service.update(self.student.id, data)

        result = self.service.get_list(self.admin, None, 1, 10, ordering = "name")
        names = [row["name"] for row in result["results"]]
        self.assertIn("ListUpdated Name", names)

    def test_student_update_does_not_invalidate_unrelated_teacher_namespace(self):
        from teachers.cache.teacher_cache import TeacherCache
        from teachers.models import Teacher

        teacher = Teacher.objects.create(
            user = User.objects.create_user(
                email = "cacheteacher@example.com", name = "Untouched Teacher", password = "x", role = "teacher",
            ),
            employee_id = "CACHE1", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            gender = "M", date_of_birth = date(1980, 1, 1), date_of_joining = date(2020, 1, 1), salary = 1,
        )
        teacher_cache = TeacherCache(CacheService())
        # Warm the Teacher detail cache directly (bypassing the DB) so we can
        # prove a Student write never touches the teacher:* namespace.
        teacher_cache.cache.set(teacher_cache.detail_key(teacher.id), {"marker": "untouched"}, None)

        data = self._full_update_data(self.student, first_name = "Whatever", last_name = "Name")
        self.service.update(self.student.id, data)

        self.assertEqual(
            teacher_cache.cache.get(teacher_cache.detail_key(teacher.id)),
            {"marker": "untouched"},
        )
