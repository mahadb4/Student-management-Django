from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from departments.models import Department
from sections.models import Section
from users.models import User
from users.repositories.user_repository import UserRepository


# Covers the Onboarding/Admin Section dropdown's core requirement: selecting
# a department must only ever surface that department's own sections, never
# another department's - this is what makes the dropdown "Department ->
# Section" dependent instead of showing every section in the database
# (the original "A, A, A, A..." duplicate-names bug).
class SectionReferenceDepartmentFilteringTests(TestCase):

    def setUp(self):
        self.cs = Department.objects.create(name="Computer Science", code="CS")
        self.ee = Department.objects.create(name="Electrical Engineering", code="EE")

        self.cs_section_a = Section.objects.create(
            name="A", department=self.cs, semester_number=1, academic_year=2026,
        )
        self.cs_section_b = Section.objects.create(
            name="B", department=self.cs, semester_number=1, academic_year=2026,
        )
        self.ee_section_a = Section.objects.create(
            name="A", department=self.ee, semester_number=1, academic_year=2026,
        )

        self.user = User.objects.create_user(
            email="onboarding@example.com", name="Onboarding Student", password="x", role="student",
        )
        UserRepository().approve(self.user)
        self.client = Client()

    def _auth_headers(self):
        token = str(RefreshToken.for_user(self.user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_section_reference_filtered_by_department_returns_only_that_departments_sections(self):
        response = self.client.get(
            f"/api/sections/reference/?department_id={self.cs.id}", **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.cs_section_a.id, self.cs_section_b.id})
        self.assertNotIn(self.ee_section_a.id, ids)

    def test_section_reference_for_different_department_returns_different_sections(self):
        response = self.client.get(
            f"/api/sections/reference/?department_id={self.ee.id}", **self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.ee_section_a.id})
