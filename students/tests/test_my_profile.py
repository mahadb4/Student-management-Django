import json
from datetime import date
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from departments.models import Department
from sections.models import Section
from students.models import Student
from users.models import User
from users.repositories.user_repository import UserRepository


class MyStudentProfileApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computer Science", code = "CS")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        user = User.objects.create_user(
            email = "mahad@example.com", name = "Mahad Baloch", password = "x", role = "student",
        )
        UserRepository().approve(user)
        user.date_of_birth = date(2002, 7, 25)
        user.gender = "M"
        user.address = "Garden West"
        user.save()

        self.student = Student.objects.create(
            user = user, parents_phone_number = "03001234567",
            department = self.department, section = self.section,
        )

        other_user = User.objects.create_user(
            email = "other@example.com", name = "Other Student", password = "x", role = "student",
        )
        UserRepository().approve(other_user)
        other_user.date_of_birth = date(2003, 1, 1)
        other_user.gender = "F"
        other_user.save()
        self.other_student = Student.objects.create(
            user = other_user, parents_phone_number = "03007654321",
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_my_profile_returns_exact_expected_keys(self):
        response = self.client.get("/api/students/me/", **self._auth_headers(self.student.user))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            set(response.json().keys()),
            {
                "id", "first_name", "last_name", "student_email", "parents_phone_number",
                "date_of_birth", "gender", "address", "department_name", "section_name",
                "date_of_enrollment", "profile_picture_url",
            },
        )

    def test_student_can_edit_allowed_personal_fields(self):
        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"address": "North Nazimabad", "parents_phone_number": "03119998887"}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Student updated successfully."})

        self.student.refresh_from_db()
        self.student.user.refresh_from_db()
        self.assertEqual(self.student.user.address, "North Nazimabad")
        self.assertEqual(self.student.parents_phone_number, "03119998887")

    def test_student_cannot_edit_department(self):
        other_department = Department.objects.create(name = "Mathematics", code = "MATH")

        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"department": other_department.id}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.department_id, self.department.id)

    def test_student_cannot_edit_section(self):
        other_section = Section.objects.create(
            name = "B", department = self.department, semester_number = 2, academic_year = 2026,
        )

        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"section": other_section.id}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.section_id, self.section.id)

    def test_student_cannot_edit_status(self):
        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"is_active": False}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_student_cannot_edit_enrollment_date(self):
        original_enrollment_date = self.student.date_of_enrollment

        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"date_of_enrollment": "2000-01-01"}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 200)

        self.student.refresh_from_db()
        self.assertEqual(self.student.date_of_enrollment, original_enrollment_date)

    def test_student_cannot_modify_another_students_profile(self):
        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"address": "Hacked Address"}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 200)

        self.other_student.user.refresh_from_db()
        self.assertNotEqual(self.other_student.user.address, "Hacked Address")

    def test_invalid_personal_information_is_rejected(self):
        response = self.client.patch(
            "/api/students/me/",
            data = json.dumps({"parents_phone_number": "not-a-phone"}),
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 400)

        self.student.refresh_from_db()
        self.assertEqual(self.student.parents_phone_number, "03001234567")
