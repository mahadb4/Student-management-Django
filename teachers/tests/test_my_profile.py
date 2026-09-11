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
        self.teacher = Teacher.objects.create(
            user = user, employee_id = "15021", phone_number = "1234567",
            department = self.department, designation = "Senior Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
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
            {"id", "name", "employee_id", "email", "department_name", "designation", "profile_picture_url"},
        )
        # No first_name/last_name on this profile-only response - name is
        # already the single joined string the Profile page renders.
        self.assertNotIn("first_name", data)
        self.assertNotIn("last_name", data)

    def test_my_profile_name_is_joined_first_and_last_name(self):
        response = self.client.get("/api/teachers/me/", **self._auth_headers(self.teacher.user))
        self.assertEqual(response.json()["name"], "Muhammad Owais")
