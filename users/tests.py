from datetime import date
from django.test import TestCase
from departments.models import Department
from sections.models import Section
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from students.cache.student_cache import StudentCache
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator
from teachers.cache.teacher_cache import TeacherCache
from common.cache.cache_service import CacheService
from common.permissions import get_scope_identity
from users.api.user_api import _create_own_profile, resolve_authenticated_display_name
from users.models import User
from users.repositories.user_repository import UserRepository
from users.services.user_service import UserService
from users.services.user_validator import UserValidator


#Onboarding creates a Student/Teacher and links it to the already-authenticated User.
class OnboardingIdentityWritePathTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

    def test_student_onboarding_creates_and_links_to_the_registered_user(self):
        user = User.objects.create_user(
            email = "onboard@example.com", name = "Registered Name", password = "x", role = "student",
        )

        student = _create_own_profile(user, {
            "first_name": "Onboard", "last_name": "Person",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })

        student.refresh_from_db()
        self.assertEqual(student.user_id, user.id)
        self.assertEqual(User.objects.filter(email__iexact = "onboard@example.com").count(), 1)

    def test_teacher_onboarding_creates_and_links_to_the_registered_user(self):
        user = User.objects.create_user(
            email = "onboardteacher@example.com", name = "Registered Name", password = "x", role = "teacher",
        )

        teacher = _create_own_profile(user, {
            "first_name": "Onboard", "last_name": "Teacher", "employee_id": "E100",
            "phone_number": "1234567", "department": self.department.id, "designation": "Lecturer",
            "qualification": "MSc", "gender": "M", "date_of_birth": date(1980, 1, 1),
            "date_of_joining": date(2020, 1, 1), "salary": 1,
        })

        teacher.refresh_from_db()
        self.assertEqual(teacher.user_id, user.id)

    def test_onboarded_student_user_name_reflects_submission_not_registration(self):
        user = User.objects.create_user(
            email = "stu@example.com", name = "Registered Name", password = "x", role = "student",
        )
        _create_own_profile(user, {
            "first_name": "Actual", "last_name": "Identity",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })
        user.refresh_from_db()
        self.assertEqual(user.name, "Actual Identity")

    def test_onboarded_teacher_user_name_reflects_submission_not_registration(self):
        user = User.objects.create_user(
            email = "tch@example.com", name = "Registered Name", password = "x", role = "teacher",
        )
        _create_own_profile(user, {
            "first_name": "Actual", "last_name": "Identity", "employee_id": "E200",
            "phone_number": "1234567", "department": self.department.id, "designation": "Lecturer",
            "qualification": "MSc", "gender": "M", "date_of_birth": date(1980, 1, 1),
            "date_of_joining": date(2020, 1, 1), "salary": 1,
        })
        user.refresh_from_db()
        self.assertEqual(user.name, "Actual Identity")

    def test_onboarded_student_effective_identity_matches_user(self):
        user = User.objects.create_user(
            email = "eff@example.com", name = "Registered Name", password = "x", role = "student",
        )
        student = _create_own_profile(user, {
            "first_name": "Effective", "last_name": "Test",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })
        student = Student.objects.select_related("user").get(id = student.id)
        self.assertEqual(student.effective_first_name, "Effective")
        self.assertEqual(student.effective_last_name, "Test")
        self.assertEqual(student.effective_email, "eff@example.com")

    def test_onboarded_teacher_effective_identity_matches_user(self):
        user = User.objects.create_user(
            email = "efft@example.com", name = "Registered Name", password = "x", role = "teacher",
        )
        teacher = _create_own_profile(user, {
            "first_name": "Effective", "last_name": "Teacher", "employee_id": "E300",
            "phone_number": "1234567", "department": self.department.id, "designation": "Lecturer",
            "qualification": "MSc", "gender": "M", "date_of_birth": date(1980, 1, 1),
            "date_of_joining": date(2020, 1, 1), "salary": 1,
        })
        teacher = Teacher.objects.select_related("user").get(id = teacher.id)
        self.assertEqual(teacher.effective_first_name, "Effective")
        self.assertEqual(teacher.effective_last_name, "Teacher")
        self.assertEqual(teacher.effective_email, "efft@example.com")

    def test_profile_update_after_onboarding_updates_user_identity(self):
        user = User.objects.create_user(
            email = "postonboard@example.com", name = "Registered Name", password = "x", role = "student",
        )
        student = _create_own_profile(user, {
            "first_name": "First", "last_name": "Version",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })

        service = StudentService(StudentValidator(), StudentRepository(), StudentCache(CacheService()))
        service.update(student.id, {
            "first_name": "Second", "last_name": "Version", "student_email": "updated@example.com",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id, "is_active": True,
        })

        user.refresh_from_db()
        self.assertEqual(user.name, "Second Version")
        self.assertEqual(user.email, "updated@example.com")

    def test_partial_update_after_onboarding_does_not_change_user_name(self):
        user = User.objects.create_user(
            email = "patchcheck@example.com", name = "Registered Name", password = "x", role = "teacher",
        )
        teacher = _create_own_profile(user, {
            "first_name": "Original", "last_name": "Teacher", "employee_id": "E400",
            "phone_number": "1234567", "department": self.department.id, "designation": "Lecturer",
            "qualification": "MSc", "gender": "M", "date_of_birth": date(1980, 1, 1),
            "date_of_joining": date(2020, 1, 1), "salary": 1,
        })

        service = TeacherService(TeacherValidator(), TeacherRepository(), TeacherCache(CacheService()))
        service.update(teacher.id, {"salary": 9999}, partial = True)

        user.refresh_from_db()
        teacher.refresh_from_db()
        self.assertEqual(user.name, "Original Teacher")
        self.assertEqual(teacher.salary, 9999)


class AuthAndDisplayNameTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )
        self.user_service = UserService(UserValidator(), UserRepository())

    def test_display_name_for_user_with_student_profile(self):
        user = User.objects.create_user(
            email = "dispstu@example.com", name = "Reg Name", password = "x", role = "student",
        )
        _create_own_profile(user, {
            "first_name": "Display", "last_name": "Student",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })
        user.refresh_from_db()
        self.assertEqual(resolve_authenticated_display_name(user), "Display Student")

    def test_display_name_for_user_with_teacher_profile(self):
        user = User.objects.create_user(
            email = "disptch@example.com", name = "Reg Name", password = "x", role = "teacher",
        )
        _create_own_profile(user, {
            "first_name": "Display", "last_name": "Teacher", "employee_id": "E500",
            "phone_number": "1234567", "department": self.department.id, "designation": "Lecturer",
            "qualification": "MSc", "gender": "M", "date_of_birth": date(1980, 1, 1),
            "date_of_joining": date(2020, 1, 1), "salary": 1,
        })
        user.refresh_from_db()
        self.assertEqual(resolve_authenticated_display_name(user), "Display Teacher")

    def test_display_name_for_user_without_profile(self):
        user = User.objects.create_user(
            email = "noprofile@example.com", name = "Standalone Name", password = "x", role = "admin",
        )
        self.assertEqual(resolve_authenticated_display_name(user), "Standalone Name")

    def test_login_still_works_and_returns_correct_display_name(self):
        user = User.objects.create_user(
            email = "loginflow@example.com", name = "Reg Name", password = "secret123", role = "student",
        )
        user.status = "approved"
        user.save(update_fields = ["status"])

        _create_own_profile(user, {
            "first_name": "Logged", "last_name": "In",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })

        result = self.user_service.login({"email": "loginflow@example.com", "password": "secret123"})
        self.assertIn("access", result)
        self.assertIn("refresh", result)
        self.assertEqual(resolve_authenticated_display_name(result["user"]), "Logged In")

    def test_role_and_group_behavior_unchanged_on_approve(self):
        user = User.objects.create_user(
            email = "approveme@example.com", name = "Approve Me", password = "x", role = "student",
        )
        repo = UserRepository()
        approved = repo.approve(user)
        self.assertEqual(approved.status, "approved")
        self.assertTrue(approved.groups.filter(name = "STUDENT").exists())

    def test_scope_identity_unaffected_by_identity_migration(self):
        user = User.objects.create_user(
            email = "scopecheck@example.com", name = "Reg Name", password = "x", role = "student",
        )
        student = _create_own_profile(user, {
            "first_name": "Scope", "last_name": "Check",
            "parents_phone_number": "1234567", "date_of_birth": date(2000, 1, 1), "gender": "M",
            "department": self.department.id, "section": self.section.id,
        })
        user.refresh_from_db()
        kind, profile = get_scope_identity(user)
        self.assertEqual(kind, "student")
        self.assertEqual(profile.id, student.id)
