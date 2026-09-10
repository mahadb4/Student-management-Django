from datetime import date
from django.test import TestCase
from departments.models import Department
from teachers.mappers.teacher_mapper import TeacherMapper
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from users.models import User


#Teacher identity (name/email) is read from User.
class TeacherIdentityReadPathTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")

        self.user = User.objects.create_user(
            email = "teacher@example.com", name = "Some Teacher", password = "x", role = "teacher",
        )
        self.teacher = Teacher.objects.create(
            user = self.user, employee_id = "E1", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

    def test_teacher_reads_identity_from_user(self):
        teacher = Teacher.objects.select_related("user").get(id = self.teacher.id)
        self.assertEqual(teacher.effective_first_name, "Some")
        self.assertEqual(teacher.effective_last_name, "Teacher")
        self.assertEqual(teacher.effective_email, "teacher@example.com")

    def test_mapper_output_uses_effective_identity(self):
        dto = TeacherMapper.to_list_dto(
            Teacher.objects.select_related("user", "department").get(id = self.teacher.id)
        )
        self.assertEqual(dto["name"], "Some Teacher")
        self.assertEqual(dto["email"], "teacher@example.com")
        self.assertEqual(
            set(dto.keys()),
            {"id", "employee_id", "name", "email", "designation", "department_name", "profile_picture_key"},
        )

    def test_teacher_name_sorting_uses_user_name(self):
        other_user = User.objects.create_user(
            email = "another@example.com", name = "Another Teacher", password = "x", role = "teacher",
        )
        other_teacher = Teacher.objects.create(
            user = other_user, employee_id = "E2", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )
        repo = TeacherRepository()
        ids_in_order = list(
            repo.get_queryset_for_list().order_by("user__name").values_list("id", flat = True)
        )
        self.assertEqual(ids_in_order, [other_teacher.id, self.teacher.id])

    def test_search_matches_user_name_and_email(self):
        repo = TeacherRepository()
        results = repo.get_queryset_for_list(search = "Some Teacher")
        self.assertIn(self.teacher.id, results.values_list("id", flat = True))
