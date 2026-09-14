"""
Phase 10B tests: build_attendance_context.

Authorization is entirely delegated to common.permissions.apply_data_scope
(unchanged, already covered by ai_assistant/tests/test_scope.py) - these
tests focus on the new aggregation math and on re-confirming the scoping
boundary holds through this new entry point too.
"""
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ai_assistant.context.attendance_context import build_attendance_context
from attendance.models import Attendance
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class AttendanceContextTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        teacher_user = User.objects.create_user(email="t@example.com", name="Teacher A", password="x", role="teacher")
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id="EMP-A", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )

        other_teacher_user = User.objects.create_user(
            email="t2@example.com", name="Teacher B", password="x", role="teacher",
        )
        self.other_teacher = Teacher.objects.create(
            user=other_teacher_user, employee_id="EMP-B", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )

        student_user = User.objects.create_user(email="s@example.com", name="Student", password="x", role="student")
        self.student = Student.objects.create(
            user=student_user, parents_phone_number="1234567", department=self.department, section=self.section,
        )

        other_student_user = User.objects.create_user(
            email="s2@example.com", name="Other Student", password="x", role="student",
        )
        self.other_student = Student.objects.create(
            user=other_student_user, parents_phone_number="1234567", department=self.department, section=self.section,
        )

        self.course_maths = Course.objects.create(
            name="Maths", code="MTH101", credits=3, department=self.department, teacher=self.teacher,
        )
        self.course_cs = Course.objects.create(
            name="Basic Computing", code="CS101", credits=3, department=self.department, teacher=self.teacher,
        )
        self.other_course = Course.objects.create(
            name="Networks", code="CS102", credits=3, department=self.department, teacher=self.other_teacher,
        )

        self.offering_maths = CourseOffering.objects.create(
            course=self.course_maths, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )
        self.offering_cs = CourseOffering.objects.create(
            course=self.course_cs, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )
        self.other_offering = CourseOffering.objects.create(
            course=self.other_course, teacher=self.other_teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.enrollment_maths = Enrollment.objects.create(student=self.student, course_offering=self.offering_maths)
        self.enrollment_cs = Enrollment.objects.create(student=self.student, course_offering=self.offering_cs)
        self.other_student_enrollment = Enrollment.objects.create(
            student=self.other_student, course_offering=self.other_offering,
        )

        # Student: Maths - 2 present, 1 late; Basic Computing - 1 present, 1 absent.
        Attendance.objects.create(enrollment=self.enrollment_maths, date=date(2026, 2, 1), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=self.enrollment_maths, date=date(2026, 2, 2), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=self.enrollment_maths, date=date(2026, 2, 3), status=Attendance.Status.LATE)
        Attendance.objects.create(enrollment=self.enrollment_cs, date=date(2026, 2, 1), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=self.enrollment_cs, date=date(2026, 2, 2), status=Attendance.Status.ABSENT)

        # Other student's attendance - must never appear in `student`'s context.
        Attendance.objects.create(
            enrollment=self.other_student_enrollment, date=date(2026, 2, 1), status=Attendance.Status.ABSENT,
        )

    def test_overall_totals_and_percentage(self):
        context = build_attendance_context(self.student.user)
        text = context["prompt_item"]["text"]
        self.assertIn("5 total classes, 3 present, 1 late, 1 absent", text)
        self.assertIn("60% attendance", text)  # 3/5 = 60%

    def test_per_course_breakdown_in_sources(self):
        context = build_attendance_context(self.student.user)
        by_course = {s["course_name"]: s for s in context["sources"]}
        self.assertEqual(set(by_course.keys()), {"Maths", "Basic Computing"})
        self.assertIn("67%", by_course["Maths"]["detail"])  # 2/3 present, rounds to 67%
        self.assertIn("50%", by_course["Basic Computing"]["detail"])  # 1/2 present

    def test_sources_are_attendance_typed(self):
        context = build_attendance_context(self.student.user)
        for source in context["sources"]:
            self.assertEqual(source["type"], "attendance")

    def test_another_students_attendance_never_appears(self):
        context = build_attendance_context(self.student.user)
        self.assertNotIn("Networks", context["prompt_item"]["text"])
        course_names = {s["course_name"] for s in context["sources"]}
        self.assertNotIn("Networks", course_names)

    def test_teacher_sees_only_their_own_offerings_attendance(self):
        context = build_attendance_context(self.teacher.user)
        # Teacher A teaches Maths + Basic Computing (5 records total), not
        # the other teacher's Networks offering (1 record) - must be excluded.
        self.assertIn("5 total classes", context["prompt_item"]["text"])
        course_names = {s["course_name"] for s in context["sources"]}
        self.assertNotIn("Networks", course_names)

    def test_prompt_item_has_no_real_created_at(self):
        # Option A compatibility wrapper: this is a computed summary, not a
        # dated record - created_at must stay empty so it never looks like
        # a real timestamped source to the model.
        context = build_attendance_context(self.student.user)
        self.assertEqual(context["prompt_item"]["created_at"], "")

    def test_no_attendance_records_produces_safe_text_and_no_sources(self):
        empty_user = User.objects.create_user(email="lonely@example.com", name="Lonely", password="x", role="student")
        Student.objects.create(
            user=empty_user, parents_phone_number="1234567", department=self.department, section=self.section,
        )
        context = build_attendance_context(empty_user)
        self.assertIn("doesn't have any attendance records yet", context["prompt_item"]["text"])
        self.assertEqual(context["sources"], [])

    def test_anonymous_user_gets_no_attendance_data(self):
        context = build_attendance_context(AnonymousUser())
        self.assertIn("doesn't have any attendance records yet", context["prompt_item"]["text"])
        self.assertEqual(context["sources"], [])
