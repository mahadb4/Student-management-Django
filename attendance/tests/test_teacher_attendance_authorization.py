# Verifies the fix in attendance/migrations/0003_grant_teacher_group_permissions.py:
# a teacher now has the Django permission to reach the attendance write views
# at all, but the existing ownership check (enrollment.course_offering.teacher_id
# == teacher.id, in attendance_service.py - untouched by that migration) still
# separately decides whether a given write is actually allowed. Final
# authorization is the AND of both. Admin's own authorization/behavior is
# asserted unchanged here too (see admin_can_* tests) - nothing in
# common/permissions.py or the admin write path was touched by this fix.
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


class TeacherAttendanceAuthorizationTests(TestCase):

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

        # make_teacher() -> approve() puts the user in the TEACHER group,
        # which the new migration grants attendance permissions to.
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

        self.attendance_b = Attendance.objects.create(
            enrollment = self.enrollment_b, date = date(2026, 9, 1), status = Attendance.Status.PRESENT,
        )

        # Real admin accounts in this system are always Django superusers
        # (see users/management/commands/create_admin.py) - is_superuser
        # bypasses has_perm entirely, unaffected by this migration.
        self.admin_user = User.objects.create_superuser(email = "admin@example.com", name = "Admin", password = "x")

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # 1. Teacher can create attendance for their own offering.
    def test_teacher_can_create_attendance_for_own_offering(self):
        response = self.client.post(
            "/api/attendance/",
            data = {"enrollment_id": self.enrollment_a.id, "date": "2026-09-05", "status": "PRESENT", "remarks": ""},
            content_type = "application/json",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Attendance.objects.filter(enrollment_id = self.enrollment_a.id, date = "2026-09-05").exists())

    # 2. Teacher can update attendance for their own offering.
    def test_teacher_can_update_attendance_for_own_offering(self):
        attendance_a = Attendance.objects.create(
            enrollment = self.enrollment_a, date = date(2026, 9, 1), status = Attendance.Status.PRESENT,
        )
        response = self.client.put(
            f"/api/attendance/{attendance_a.id}/",
            data = {"enrollment_id": self.enrollment_a.id, "date": "2026-09-01", "status": "LATE", "remarks": ""},
            content_type = "application/json",
            **self._auth_headers(self.teacher_a.user),
        )
        self.assertEqual(response.status_code, 200)
        attendance_a.refresh_from_db()
        self.assertEqual(attendance_a.status, "LATE")

    # 3. Teacher cannot create attendance for another teacher's offering.
    def test_teacher_cannot_create_attendance_for_another_teachers_offering(self):
        response = self.client.post(
            "/api/attendance/",
            data = {"enrollment_id": self.enrollment_b.id, "date": "2026-09-06", "status": "PRESENT", "remarks": ""},
            content_type = "application/json",
            **self._auth_headers(self.teacher_a.user),
        )
        # Permission check passes (has_perm succeeds now) - rejected by the
        # unchanged ownership check in attendance_service.create() instead.
        self.assertEqual(response.status_code, 400)
        self.assertIn("not assigned", response.json()["error"].lower())
        self.assertFalse(Attendance.objects.filter(enrollment_id = self.enrollment_b.id, date = "2026-09-06").exists())

    # 4. Teacher cannot update another teacher's attendance.
    def test_teacher_cannot_update_another_teachers_attendance(self):
        response = self.client.put(
            f"/api/attendance/{self.attendance_b.id}/",
            data = {"enrollment_id": self.enrollment_b.id, "date": "2026-09-01", "status": "LATE", "remarks": ""},
            content_type = "application/json",
            **self._auth_headers(self.teacher_a.user),
        )
        # apply_data_scope hides teacher_b's attendance from teacher_a before
        # the detail lookup even resolves - forbidden at the scope check.
        self.assertEqual(response.status_code, 403)
        self.attendance_b.refresh_from_db()
        self.assertEqual(self.attendance_b.status, "PRESENT")

    # 5. Student cannot write attendance.
    def test_student_cannot_create_attendance(self):
        response = self.client.post(
            "/api/attendance/",
            data = {"enrollment_id": self.enrollment_a.id, "date": "2026-09-07", "status": "PRESENT", "remarks": ""},
            content_type = "application/json",
            **self._auth_headers(self.student.user),
        )
        self.assertEqual(response.status_code, 403)

    # 6. Admin's existing behavior remains unchanged (superuser bypass,
    # untouched by this migration - ADMIN group was deliberately not granted
    # anything here).
    def test_admin_can_list_attendance_unaffected(self):
        response = self.client.get("/api/attendance/", **self._auth_headers(self.admin_user))
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.attendance_b.id, ids)

    def test_admin_write_behavior_unchanged_still_requires_teacher_profile(self):
        # Admin has no Teacher profile in this test and none was added for
        # admin write access - this must still behave exactly as before this
        # migration (400 ATTENDANCE_TEACHER_NOT_FOUND), confirming admin
        # write authorization was not touched.
        response = self.client.post(
            "/api/attendance/",
            data = {"enrollment_id": self.enrollment_a.id, "date": "2026-09-08", "status": "PRESENT", "remarks": ""},
            content_type = "application/json",
            **self._auth_headers(self.admin_user),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Teacher profile not found for the current user.")
