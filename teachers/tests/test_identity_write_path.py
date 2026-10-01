from datetime import date
from django.test import TestCase
from departments.models import Department
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator
from teachers.cache.teacher_cache import TeacherCache
from common.cache.cache_service import CacheService
from users.models import User


#A Teacher always has a User: create() either links a given User (onboarding)
#or creates a new one (admin creation); update() always writes identity to User.
class TeacherIdentityWritePathTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.service = TeacherService(TeacherValidator(), TeacherRepository(), TeacherCache(CacheService()))

        self.user = User.objects.create_user(
            email = "teacher@example.com", name = "Original Name", password = "x", role = "teacher",
        )
        self.user.date_of_birth = date(1980, 1, 1)
        self.user.gender = "M"
        self.user.save(update_fields = ["date_of_birth", "gender"])
        self.teacher = Teacher.objects.create(
            user = self.user, employee_id = "E1", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

    def _base_data(self, **overrides):
        data = {
            "first_name": "First", "last_name": "Last", "employee_id": "E9",
            "email": "new@example.com", "phone_number": "1234567",
            "department": self.department.id, "designation": "Lecturer", "qualification": "MSc",
            "gender": "M", "date_of_birth": date(1980, 1, 1), "date_of_joining": date(2020, 1, 1),
            "salary": 1, "address": "", "is_active": True,
        }
        data.update(overrides)
        return data

    def test_create_without_user_creates_new_user(self):
        teacher = self.service.create(self._base_data(
            first_name = "Brand", last_name = "New", employee_id = "E10", email = "brandnewteacher@example.com",
        ))
        self.assertIsNotNone(teacher.user_id)
        self.assertEqual(teacher.user.name, "Brand New")
        self.assertEqual(teacher.user.email, "brandnewteacher@example.com")
        self.assertEqual(teacher.user.role, "teacher")
        self.assertEqual(teacher.user.status, "approved")
        self.assertTrue(teacher.user.groups.filter(name = "TEACHER").exists())

    def test_create_with_user_links_to_that_user(self):
        onboarding_user = User.objects.create_user(
            email = "onboardteacher@example.com", name = "Onboard Teacher", password = "x", role = "teacher",
        )
        teacher = self.service.create(
            self._base_data(
                first_name = "Onboard", last_name = "Teacher", employee_id = "E11",
                email = "onboardteacher@example.com",
            ),
            user = onboarding_user,
        )
        self.assertEqual(teacher.user_id, onboarding_user.id)
        self.assertEqual(User.objects.filter(email__iexact = "onboardteacher@example.com").count(), 1)

    def test_update_writes_identity_to_user(self):
        data = self._base_data(
            first_name = "Updated", last_name = "Name", employee_id = "E1", email = "updated@example.com",
        )
        self.service.update(self.teacher.id, data)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Updated Name")
        self.assertEqual(self.user.email, "updated@example.com")

    def test_partial_update_omitting_name_does_not_change_user_name(self):
        self.service.update(self.teacher.id, {"salary": 9999}, partial = True)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Original Name")

    def test_email_uniqueness_enforced_against_user_email(self):
        User.objects.create_user(
            email = "taken@example.com", name = "Other", password = "x", role = "teacher",
        )
        data = self._base_data(employee_id = "E1", email = "taken@example.com")
        with self.assertRaises(ValueError):
            self.service.update(self.teacher.id, data)

    def test_employee_id_uniqueness_still_enforced(self):
        Teacher.objects.create(
            user = User.objects.create_user(
                email = "e9@example.com", name = "Other Teacher", password = "x", role = "teacher",
            ),
            employee_id = "E9", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )
        data = self._base_data(employee_id = "E9", email = "teacher@example.com")
        with self.assertRaises(ValueError):
            self.service.update(self.teacher.id, data)

    def test_no_unrelated_fields_modified_on_update(self):
        data = self._base_data(first_name = "Changed", last_name = "Person", employee_id = "E1", email = "teacher@example.com")
        self.service.update(self.teacher.id, data)

        teacher = Teacher.objects.get(id = self.teacher.id)
        self.assertEqual(teacher.designation, "Lecturer")
        self.assertEqual(teacher.department_id, self.department.id)
        self.assertTrue(teacher.is_active)
