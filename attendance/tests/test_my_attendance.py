from datetime import date
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from attendance.models import Attendance
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User
from users.repositories.user_repository import UserRepository


class MyTeacherAttendanceApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        def make_teacher(email, name, employee_id):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "teacher")
            UserRepository().approve(user)
            return Teacher.objects.create(
                user = user, employee_id = employee_id, phone_number = "1234567",
                department = self.department, designation = "Lecturer", qualification = "MSc",
                date_of_joining = date(2020, 1, 1), salary = 1,
            )

        def make_student(email, name):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
            UserRepository().approve(user)
            return Student.objects.create(
                user = user, parents_phone_number = "1234567",
                department = self.department, section = self.section,
            )

        self.teacher_a = make_teacher("a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("b@example.com", "Teacher B", "EMP-B")

        self.course_a = Course.objects.create(
            name = "Maths", code = "MTH101", credits = 3, department = self.department, teacher = self.teacher_a,
        )
        self.offering_a = CourseOffering.objects.create(
            course = self.course_a, teacher = self.teacher_a, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.course_b = Course.objects.create(
            name = "English", code = "ENG101", credits = 3, department = self.department, teacher = self.teacher_b,
        )
        self.offering_b = CourseOffering.objects.create(
            course = self.course_b, teacher = self.teacher_b, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.student = make_student("student@example.com", "Student One")
        self.enrollment_a = Enrollment.objects.create(student = self.student, course_offering = self.offering_a)
        self.enrollment_b = Enrollment.objects.create(student = self.student, course_offering = self.offering_b)

        self.attendance_a = Attendance.objects.create(
            enrollment = self.enrollment_a, date = date(2026, 9, 1), status = Attendance.Status.PRESENT,
        )
        self.attendance_b = Attendance.objects.create(
            enrollment = self.enrollment_b, date = date(2026, 9, 1), status = Attendance.Status.ABSENT,
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_without_filter_teacher_sees_only_their_own_offerings_attendance(self):
        # apply_data_scope already restricts to the teacher's own classes,
        # even before any course_offering_id filter is applied.
        response = self.client.get("/api/teachers/me/attendance/", **self._auth_headers(self.teacher_a.user))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.attendance_a.id})

    def test_course_offering_filter_scopes_to_that_class_only(self):
        response = self.client.get(
            f"/api/teachers/me/attendance/?course_offering_id={self.offering_a.id}",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.attendance_a.id})

    def test_course_offering_filter_for_another_teachers_offering_returns_empty(self):
        # teacher_a passing teacher_b's offering id must not leak teacher_b's
        # attendance - apply_data_scope's own restriction to teacher_a's
        # offerings means this combination simply matches nothing.
        response = self.client.get(
            f"/api/teachers/me/attendance/?course_offering_id={self.offering_b.id}",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_response_row_keys_unchanged(self):
        response = self.client.get(
            f"/api/teachers/me/attendance/?course_offering_id={self.offering_a.id}",
            **self._auth_headers(self.teacher_a.user),
        )
        row = response.json()["results"][0]
        self.assertEqual(set(row.keys()), {"id", "date", "status", "remarks", "enrollment_id", "student_name"})
