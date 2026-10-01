from datetime import date
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from sections.models import Section
from teachers.models import Teacher
from users.models import User
from users.repositories.user_repository import UserRepository


class MyCourseOfferingsApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "D", department = self.department, semester_number = 1, academic_year = 2026,
        )

        user = User.objects.create_user(email = "t@example.com", name = "Teacher One", password = "x", role = "teacher")
        UserRepository().approve(user)
        self.teacher = Teacher.objects.create(
            user = user, employee_id = "EMP-1", phone_number = "1234567",
            department = self.department, designation = "Lecturer", qualification = "MSc",
            date_of_joining = date(2020, 1, 1), salary = 1,
        )

        self.course = Course.objects.create(
            name = "Maths", code = "MTH101", credits = 3, department = self.department, teacher = self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_default_response_shape_is_unchanged(self):
        response = self.client.get("/api/teachers/me/courses/", **self._auth_headers(self.teacher.user))
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertEqual(
            set(row.keys()),
            {"id", "course_name", "course_code", "semester", "academic_year", "section_name", "is_active", "enrolled_students_count"},
        )

    def test_attendance_view_returns_a_narrower_projection(self):
        # ?view=attendance is opt-in for the Attendance register only - the
        # default (above) is unchanged for every other caller (My Classes).
        response = self.client.get(
            "/api/teachers/me/courses/?view=attendance", **self._auth_headers(self.teacher.user),
        )
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertEqual(set(row.keys()), {"id", "course_name", "section_name"})
        self.assertEqual(row["course_name"], "Maths")
        self.assertEqual(row["section_name"], "D")
