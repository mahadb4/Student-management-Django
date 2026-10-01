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


class AdminAttendanceApiTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name = "Computing", code = "CMP")
        self.other_department = Department.objects.create(name = "Business", code = "BUS")
        self.section = Section.objects.create(
            name = "A", department = self.department, semester_number = 1, academic_year = 2026,
        )

        def make_teacher(email, name, employee_id, department):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "teacher")
            UserRepository().approve(user)
            return Teacher.objects.create(
                user = user, employee_id = employee_id, phone_number = "1234567",
                department = department, designation = "Lecturer", qualification = "MSc",
                date_of_joining = date(2020, 1, 1), salary = 1,
            )

        def make_student(email, name):
            user = User.objects.create_user(email = email, name = name, password = "x", role = "student")
            UserRepository().approve(user)
            return Student.objects.create(
                user = user, parents_phone_number = "1234567",
                department = self.department, section = self.section,
            )

        self.teacher_a = make_teacher("a@example.com", "Teacher A", "EMP-A", self.department)
        self.teacher_b = make_teacher("b@example.com", "Teacher B", "EMP-B", self.other_department)

        self.course_a = Course.objects.create(
            name = "Maths", code = "MTH101", credits = 3, department = self.department, teacher = self.teacher_a,
        )
        self.offering_a = CourseOffering.objects.create(
            course = self.course_a, teacher = self.teacher_a, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.course_b = Course.objects.create(
            name = "English", code = "ENG101", credits = 3, department = self.other_department, teacher = self.teacher_b,
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

        # Real admin accounts in this system are always created as Django
        # superusers (see users/management/commands/create_admin.py), which
        # already bypass has_perm entirely and is_superuser is already treated
        # as unrestricted by apply_data_scope - this is the realistic shape of
        # an admin caller, not an artificial role="admin"-without-superuser one.
        self.admin_user = User.objects.create_superuser(email = "admin@example.com", name = "Admin", password = "x")

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # 1. admin can list attendance
    def test_admin_can_list_all_attendance(self):
        response = self.client.get("/api/attendance/", **self._auth_headers(self.admin_user))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.attendance_a.id, self.attendance_b.id})

    # 2. admin can filter by course_offering/date
    def test_admin_can_filter_by_course_offering_and_date(self):
        response = self.client.get(
            f"/api/attendance/?course_offering_id={self.offering_a.id}&date=2026-09-01",
            **self._auth_headers(self.admin_user),
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.attendance_a.id})

    def test_admin_filter_by_department_and_teacher(self):
        response = self.client.get(
            f"/api/attendance/?department_id={self.department.id}&teacher_id={self.teacher_a.id}",
            **self._auth_headers(self.admin_user),
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.attendance_a.id})

    # Enrollment filtering by course_offering works (used by the Add Record modal)
    def test_enrollment_list_filters_by_course_offering(self):
        response = self.client.get(
            f"/api/enrollments/?course_offering_id={self.offering_a.id}",
            **self._auth_headers(self.admin_user),
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["student_name"] for row in response.json()["results"]}
        self.assertEqual(ids, {"Student One"})
        self.assertEqual(response.json()["total_count"], 1)

    def test_course_offering_reference_filters_by_teacher(self):
        response = self.client.get(
            f"/api/course_offerings/reference/?teacher_id={self.teacher_a.id}",
            **self._auth_headers(self.admin_user),
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["course_code"] for row in response.json()["results"]}
        self.assertEqual(ids, {"MTH101"})
