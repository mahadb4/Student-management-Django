from datetime import date
from django.test import TestCase
from departments.models import Department
from sections.models import Section
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from students.cache.student_cache import StudentCache
from common.cache.cache_service import CacheService
from users.models import User


#A Student always has a User: create() either links a given User (onboarding)
#or creates a new one (admin creation); update() always writes identity to User.
class StudentIdentityWritePathTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        self.service = StudentService(StudentValidator(), StudentRepository(), StudentCache(CacheService()))

        self.user = User.objects.create_user(
            email = "student@example.com", name = "Original Name", password = "x", role = "student",
        )
        self.user.date_of_birth = date(2000, 1, 1)
        self.user.gender = "M"
        self.user.save(update_fields = ["date_of_birth", "gender"])
        self.student = Student.objects.create(
            user = self.user, parents_phone_number = "1234567",
            department = self.department, section = self.section,
        )

    def _base_data(self, **overrides):
        data = {
            "first_name": "First", "last_name": "Last", "student_email": "new@example.com",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id, "is_active": True,
        }
        data.update(overrides)
        return data

    def test_create_without_user_creates_new_user(self):
        student = self.service.create(self._base_data(
            first_name = "Brand", last_name = "New", student_email = "brandnew@example.com",
        ))
        self.assertIsNotNone(student.user_id)
        self.assertEqual(student.user.name, "Brand New")
        self.assertEqual(student.user.email, "brandnew@example.com")
        self.assertEqual(student.user.role, "student")
        self.assertEqual(student.user.status, "approved")
        self.assertTrue(student.user.groups.filter(name = "STUDENT").exists())

    def test_create_with_user_links_to_that_user(self):
        onboarding_user = User.objects.create_user(
            email = "onboard@example.com", name = "Onboard Person", password = "x", role = "student",
        )
        student = self.service.create(
            self._base_data(first_name = "Onboard", last_name = "Person", student_email = "onboard@example.com"),
            user = onboarding_user,
        )
        self.assertEqual(student.user_id, onboarding_user.id)
        self.assertEqual(User.objects.filter(email__iexact = "onboard@example.com").count(), 1)

    def test_update_writes_identity_to_user(self):
        data = self._base_data(first_name = "Updated", last_name = "Name", student_email = "updated@example.com")
        self.service.update(self.student.id, data)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Updated Name")
        self.assertEqual(self.user.email, "updated@example.com")

    def test_partial_update_omitting_name_does_not_change_user_name(self):
        self.service.update(self.student.id, {"address": "New Address"}, partial = True)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_email_uniqueness_enforced_against_user_email(self):
        User.objects.create_user(
            email = "taken@example.com", name = "Other", password = "x", role = "student",
        )
        data = self._base_data(student_email = "taken@example.com")
        with self.assertRaises(ValueError):
            self.service.update(self.student.id, data)

    def test_no_unrelated_fields_modified_on_update(self):
        data = self._base_data(first_name = "Changed", last_name = "Person")
        self.service.update(self.student.id, data)

        student = Student.objects.select_related("user").get(id = self.student.id)
        self.assertEqual(student.user.gender, "M")
        self.assertEqual(student.department_id, self.department.id)
        self.assertEqual(student.section_id, self.section.id)
        self.assertTrue(student.is_active)
