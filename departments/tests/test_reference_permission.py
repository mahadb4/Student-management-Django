from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from departments.models import Department
from sections.models import Section
from users.models import User
from users.repositories.user_repository import UserRepository


# Regression test for the onboarding Department/Section dropdown appearing
# permanently empty ("greyed out") to students: nothing in the codebase ever
# granted the STUDENT group view permission on Department/Section, so every
# GET to /departments/reference/ or /sections/reference/ from a real student
# session 403'd silently (the frontend only logged the error). Matches the
# same root cause already fixed once for remarks
# (remarks/migrations/0002_grant_group_permissions.py) and once for
# attendance (attendance/migrations/0003_grant_teacher_group_permissions.py).
class StudentCanReadDepartmentAndSectionReferenceTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name="Computer Science", code="CS")
        Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        self.user = User.objects.create_user(
            email="onboarding@example.com", name="Onboarding Student", password="x", role="student",
        )
        UserRepository().approve(self.user)
        self.client = Client()

    def _auth_headers(self):
        token = str(RefreshToken.for_user(self.user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_student_can_list_department_reference(self):
        response = self.client.get("/api/departments/reference/", **self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_student_can_list_section_reference_filtered_by_department(self):
        response = self.client.get(
            f"/api/sections/reference/?department_id={self.department.id}", **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
