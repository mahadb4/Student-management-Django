import json
from datetime import date
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from departments.models import Department
from sections.models import Section
from students.models import Student
from users.models import User
from users.repositories.user_repository import UserRepository


# End-to-end proof of the academic-review gate: a student whose onboarding
# is submitted but whose Department/Section an admin hasn't confirmed yet
# must be refused normal student-portal data by the SERVER (not just kept
# off the dashboard by the frontend route guard) - see
# common/permissions.py's authenticate_request, the shared chokepoint behind
# every "me" endpoint exercised here.
class AcademicReviewGateTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computer Science", code = "CS")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        self.student_user = User.objects.create_user(
            email = "pending@example.com", name = "Pending Student", password = "x", role = "student",
        )
        UserRepository().approve(self.student_user)
        self.student_user.date_of_birth = date(2002, 1, 1)
        self.student_user.gender = "M"
        self.student_user.save()

        # Created the same way onboarding does: no department/section,
        # placement_confirmed defaults False.
        self.student = Student.objects.create(
            user = self.student_user, parents_phone_number = "03001234567",
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_pending_student_is_refused_dashboard_summary(self):
        response = self.client.get("/api/students/me/summary/", **self._auth_headers(self.student_user))
        self.assertEqual(response.status_code, 403)

    def test_pending_student_is_refused_own_profile(self):
        response = self.client.get("/api/students/me/", **self._auth_headers(self.student_user))
        self.assertEqual(response.status_code, 403)

    def test_pending_student_can_still_reach_users_me(self):
        # /users/me/ authenticates independently of authenticate_request()
        # (see me_api) - the review page needs this to poll for the admin's
        # decision without logging out.
        response = self.client.get("/api/users/me/", **self._auth_headers(self.student_user))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["user"]["academic_review_pending"])

    def test_confirmed_student_can_reach_dashboard_summary(self):
        admin_user = User.objects.create_user(
            email = "admin@example.com", name = "Admin", password = "x", role = "admin",
        )
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()

        response = self.client.patch(
            f"/api/students/{self.student.id}/",
            data = json.dumps({
                "department": self.department.id, "section": self.section.id, "placement_confirmed": True,
            }),
            content_type = "application/json",
            **self._auth_headers(admin_user),
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/students/me/summary/", **self._auth_headers(self.student_user))
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/users/me/", **self._auth_headers(self.student_user))
        self.assertFalse(response.json()["user"]["academic_review_pending"])
