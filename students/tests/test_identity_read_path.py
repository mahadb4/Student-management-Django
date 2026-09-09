from datetime import date
from django.test import TestCase
from departments.models import Department
from sections.models import Section
from students.mappers.student_mapper import StudentMapper
from students.models import Student
from students.repositories.student_repository import StudentRepository
from users.models import User


#Student identity (name/email) is read from User.
class StudentIdentityReadPathTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        self.user = User.objects.create_user(
            email = "student@example.com", name = "Some Student", password = "x", role = "student",
        )
        self.student = Student.objects.create(
            user = self.user, parents_phone_number = "1234567",
            date_of_birth = date(2000, 1, 1), gender = "M",
            department = self.department, section = self.section,
        )

    def test_student_reads_identity_from_user(self):
        student = Student.objects.select_related("user").get(id = self.student.id)
        self.assertEqual(student.effective_first_name, "Some")
        self.assertEqual(student.effective_last_name, "Student")
        self.assertEqual(student.effective_email, "student@example.com")

    def test_mapper_output_uses_effective_identity(self):
        dto = StudentMapper.to_list_dto(
            Student.objects.select_related("user", "department", "section").get(id = self.student.id)
        )
        self.assertEqual(dto["name"], "Some Student")
        self.assertEqual(dto["student_email"], "student@example.com")
        self.assertEqual(
            set(dto.keys()),
            {"id", "name", "student_email", "department_name", "section_name"},
        )

    def test_student_name_sorting_uses_user_name(self):
        other_user = User.objects.create_user(
            email = "another@example.com", name = "Another Student", password = "x", role = "student",
        )
        other_student = Student.objects.create(
            user = other_user, parents_phone_number = "1234567",
            date_of_birth = date(2000, 1, 1), gender = "F",
            department = self.department, section = self.section,
        )
        repo = StudentRepository()
        ids_in_order = list(
            repo.get_queryset_for_list().order_by("user__name").values_list("id", flat = True)
        )
        self.assertEqual(ids_in_order, [other_student.id, self.student.id])

    def test_search_matches_user_name_and_email(self):
        repo = StudentRepository()
        results = repo.get_queryset_for_list(search = "Some Student")
        self.assertIn(self.student.id, results.values_list("id", flat = True))

        results = repo.get_queryset_for_list(search = "student@example.com")
        self.assertIn(self.student.id, results.values_list("id", flat = True))
