import json
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


class AttendanceBulkApiTests(TestCase):

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

        # make_teacher() -> UserRepository().approve() puts the user in the
        # TEACHER group, which now has add/change/view/delete_attendance via
        # attendance/migrations/0003_grant_teacher_group_permissions.py - no
        # per-test permission workaround needed any more.
        self.teacher_a = make_teacher("a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("b@example.com", "Teacher B", "EMP-B")

        self.course = Course.objects.create(
            name = "Maths", code = "MTH101", credits = 3, department = self.department, teacher = self.teacher_a,
        )
        self.offering = CourseOffering.objects.create(
            course = self.course, teacher = self.teacher_a, semester = CourseOffering.Semester.FALL,
            academic_year = 2026, section = self.section,
        )

        self.student_1 = make_student("s1@example.com", "Student One")
        self.student_2 = make_student("s2@example.com", "Student Two")
        self.enrollment_1 = Enrollment.objects.create(student = self.student_1, course_offering = self.offering)
        self.enrollment_2 = Enrollment.objects.create(student = self.student_2, course_offering = self.offering)

        # A DROPPED enrollment must never be required/accepted by the bulk save.
        self.student_3 = make_student("s3@example.com", "Student Three")
        self.enrollment_3_dropped = Enrollment.objects.create(
            student = self.student_3, course_offering = self.offering, status = Enrollment.Status.DROPPED,
        )

        self.client = Client()

    def _auth_headers(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _post(self, payload, user):
        return self.client.post(
            "/api/attendance/bulk/",
            data = json.dumps(payload),
            content_type = "application/json",
            **self._auth_headers(user),
        )

    def test_bulk_create_for_complete_active_roster_succeeds(self):
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "PRESENT"},
                {"enrollment_id": self.enrollment_2.id, "status": "ABSENT"},
            ],
        }, self.teacher_a.user)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(len(body["created"]), 2)
        self.assertEqual(Attendance.objects.filter(date = "2026-09-13").count(), 2)

    def test_bulk_create_is_one_request_for_the_whole_class(self):
        # One HTTP call handles every student - no per-student POST loop.
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "PRESENT"},
                {"enrollment_id": self.enrollment_2.id, "status": "PRESENT"},
            ],
        }, self.teacher_a.user)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()["created"]), 2)

    def test_incomplete_roster_is_rejected_and_writes_nothing(self):
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "PRESENT"},
                # enrollment_2 missing - incomplete.
            ],
        }, self.teacher_a.user)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attendance.objects.filter(date = "2026-09-13").count(), 0)

    def test_dropped_enrollment_in_payload_is_rejected(self):
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "PRESENT"},
                {"enrollment_id": self.enrollment_2.id, "status": "PRESENT"},
                {"enrollment_id": self.enrollment_3_dropped.id, "status": "PRESENT"},
            ],
        }, self.teacher_a.user)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attendance.objects.filter(date = "2026-09-13").count(), 0)

    def test_duplicate_date_is_rejected_and_does_not_touch_existing_rows(self):
        Attendance.objects.create(enrollment = self.enrollment_1, date = date(2026, 9, 13), status = "PRESENT")

        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "LATE"},
                {"enrollment_id": self.enrollment_2.id, "status": "PRESENT"},
            ],
        }, self.teacher_a.user)

        self.assertEqual(response.status_code, 400)
        # The pre-existing row for enrollment_1 is untouched, and no row was
        # created for enrollment_2 either - the whole batch rolled back.
        self.assertEqual(Attendance.objects.filter(date = date(2026, 9, 13)).count(), 1)
        self.assertEqual(Attendance.objects.get(date = date(2026, 9, 13)).status, "PRESENT")

    def test_teacher_cannot_bulk_save_another_teachers_offering(self):
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "PRESENT"},
                {"enrollment_id": self.enrollment_2.id, "status": "PRESENT"},
            ],
        }, self.teacher_b.user)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attendance.objects.filter(date = "2026-09-13").count(), 0)

    def test_student_cannot_bulk_save(self):
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [{"enrollment_id": self.enrollment_1.id, "status": "PRESENT"}],
        }, self.student_1.user)

        self.assertEqual(response.status_code, 403)

    def test_invalid_status_in_one_record_rejects_whole_batch(self):
        response = self._post({
            "course_offering_id": self.offering.id,
            "date": "2026-09-13",
            "records": [
                {"enrollment_id": self.enrollment_1.id, "status": "PRESENT"},
                {"enrollment_id": self.enrollment_2.id, "status": "NOT_A_STATUS"},
            ],
        }, self.teacher_a.user)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attendance.objects.filter(date = "2026-09-13").count(), 0)
