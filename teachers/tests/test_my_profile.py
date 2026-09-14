import json
from datetime import date
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from departments.models import Department
from teachers.models import Teacher
from users.models import User
from users.repositories.user_repository import UserRepository


class MyTeacherProfileApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computer Science", code = "CS")

        user = User.objects.create_user(
            email = "owais@example.com", name = "Muhammad Owais", password = "x", role = "teacher",
        )
        UserRepository().approve(user)
        user.date_of_birth = date(1985, 3, 10)
        user.gender = "M"
        user.address = "Gulshan"
        user.save()
        self.teacher = Teacher.objects.create(
            user = user, employee_id = "15021", phone_number = "1234567",
            department = self.department, designation = "Senior Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

        other_user = User.objects.create_user(
            email = "other-teacher@example.com", name = "Other Teacher", password = "x", role = "teacher",
        )
        UserRepository().approve(other_user)
        other_user.date_of_birth = date(1990, 5, 5)
        other_user.gender = "F"
        other_user.save()
        self.other_teacher = Teacher.objects.create(
            user = other_user, employee_id = "15022", phone_number = "7654321",
            department = self.department, designation = "Lecturer", qualification = "BSc",
            date_of_joining = date(2021, 1, 1), salary = 1,
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_my_profile_returns_exact_expected_keys(self):
        response = self.client.get("/api/teachers/me/", **self._auth_headers(self.teacher.user))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(
            set(data.keys()),
            {
                "id", "name", "employee_id", "email", "phone_number", "date_of_birth", "gender",
                "address", "qualification", "department_name", "designation", "profile_picture_url",
            },
        )
        # No first_name/last_name on this profile-only response - name is
        # already the single joined string the Profile page renders.
        self.assertNotIn("first_name", data)
        self.assertNotIn("last_name", data)

    def test_my_profile_name_is_joined_first_and_last_name(self):
        response = self.client.get("/api/teachers/me/", **self._auth_headers(self.teacher.user))
        self.assertEqual(response.json()["name"], "Muhammad Owais")

    def test_teacher_can_edit_allowed_personal_fields(self):
        response = self.client.patch(
            "/api/teachers/me/",
            data = json.dumps({"phone_number": "03119998887", "address": "DHA Phase 6"}),
            content_type = "application/json",
            **self._auth_headers(self.teacher.user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Teacher updated successfully."})

        self.teacher.refresh_from_db()
        self.teacher.user.refresh_from_db()
        self.assertEqual(self.teacher.phone_number, "03119998887")
        self.assertEqual(self.teacher.user.address, "DHA Phase 6")

    def test_teacher_cannot_edit_admin_controlled_fields(self):
        other_department = Department.objects.create(name = "Mathematics", code = "MATH")

        response = self.client.patch(
            "/api/teachers/me/",
            data = json.dumps({
                "department": other_department.id,
                "designation": "Head of Department",
                "salary": 999999,
                "employee_id": "99999",
                "is_active": False,
            }),
            content_type = "application/json",
            **self._auth_headers(self.teacher.user),
        )
        self.assertEqual(response.status_code, 200)

        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.department_id, self.department.id)
        self.assertEqual(self.teacher.designation, "Senior Lecturer")
        self.assertEqual(self.teacher.salary, 1)
        self.assertEqual(self.teacher.employee_id, "15021")
        self.assertTrue(self.teacher.is_active)

    def test_teacher_cannot_modify_another_teachers_profile(self):
        response = self.client.patch(
            "/api/teachers/me/",
            data = json.dumps({"phone_number": "00000000000"}),
            content_type = "application/json",
            **self._auth_headers(self.teacher.user),
        )
        self.assertEqual(response.status_code, 200)

        self.other_teacher.refresh_from_db()
        self.assertEqual(self.other_teacher.phone_number, "7654321")

    def test_invalid_personal_information_is_rejected(self):
        response = self.client.patch(
            "/api/teachers/me/",
            data = json.dumps({"phone_number": "not-a-phone"}),
            content_type = "application/json",
            **self._auth_headers(self.teacher.user),
        )
        self.assertEqual(response.status_code, 400)

        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.phone_number, "1234567")
