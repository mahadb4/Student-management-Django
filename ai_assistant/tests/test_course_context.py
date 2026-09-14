"""
Phase 10D tests: build_course_context.

Authorization is entirely delegated to common.permissions.apply_data_scope
("enrollment") - the same function Attendance (10B) already reuses. These
tests focus on: the ACTIVE-only scope decision, using CourseOffering.teacher
(not Course.teacher), and re-confirming cross-student isolation through
this new entry point.
"""
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ai_assistant.context.course_context import build_course_context
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class CourseContextTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        # Course.teacher deliberately differs from CourseOffering.teacher -
        # proves the context uses the offering's teacher, not the course's.
        stale_teacher_user = User.objects.create_user(
            email="stale@example.com", name="Stale Course Teacher", password="x", role="teacher",
        )
        self.stale_course_teacher = Teacher.objects.create(
            user=stale_teacher_user, employee_id="EMP-STALE", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )
        real_teacher_user = User.objects.create_user(
            email="real@example.com", name="Real Offering Teacher", password="x", role="teacher",
        )
        self.offering_teacher = Teacher.objects.create(
            user=real_teacher_user, employee_id="EMP-REAL", phone_number="1234567",
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

        self.course = Course.objects.create(
            name="Database Systems", code="CS301", credits=3, department=self.department,
            teacher=self.stale_course_teacher,  # deliberately the "wrong" teacher
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, teacher=self.offering_teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.dropped_course = Course.objects.create(
            name="Networks", code="CS302", credits=3, department=self.department, teacher=self.offering_teacher,
        )
        self.dropped_offering = CourseOffering.objects.create(
            course=self.dropped_course, teacher=self.offering_teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.completed_course = Course.objects.create(
            name="Intro to Programming", code="CS100", credits=3, department=self.department,
            teacher=self.offering_teacher,
        )
        self.completed_offering = CourseOffering.objects.create(
            course=self.completed_course, teacher=self.offering_teacher, semester=CourseOffering.Semester.SPRING,
            academic_year=2025, section=self.section,
        )

    def test_active_enrollment_appears(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)

        context = build_course_context(self.student.user)

        self.assertEqual(len(context["sources"]), 1)
        self.assertEqual(context["sources"][0]["course_name"], "Database Systems")

    def test_dropped_enrollment_excluded(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)
        Enrollment.objects.create(
            student=self.student, course_offering=self.dropped_offering, status=Enrollment.Status.DROPPED,
        )

        context = build_course_context(self.student.user)

        course_names = {s["course_name"] for s in context["sources"]}
        self.assertNotIn("Networks", course_names)

    def test_completed_enrollment_excluded(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)
        Enrollment.objects.create(
            student=self.student, course_offering=self.completed_offering, status=Enrollment.Status.COMPLETED,
        )

        context = build_course_context(self.student.user)

        course_names = {s["course_name"] for s in context["sources"]}
        self.assertNotIn("Intro to Programming", course_names)

    def test_uses_course_offering_teacher_not_course_teacher(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)

        context = build_course_context(self.student.user)

        self.assertEqual(context["sources"][0]["teacher_name"], "Real Offering Teacher")
        self.assertNotIn("Stale Course Teacher", str(context))

    def test_another_students_enrollment_never_appears(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)
        Enrollment.objects.create(
            student=self.other_student, course_offering=self.dropped_offering, status=Enrollment.Status.ACTIVE,
        )

        context = build_course_context(self.student.user)

        course_names = {s["course_name"] for s in context["sources"]}
        self.assertEqual(course_names, {"Database Systems"})

    def test_sources_are_course_typed_with_no_internal_ids(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)

        context = build_course_context(self.student.user)

        source = context["sources"][0]
        self.assertEqual(source["type"], "course")
        self.assertEqual(set(source.keys()), {"type", "course_name", "course_code", "teacher_name", "section_name"})

    def test_section_name_included(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)

        context = build_course_context(self.student.user)

        self.assertEqual(context["sources"][0]["section_name"], "A")

    def test_no_active_enrollments_produces_safe_text_and_no_sources(self):
        context = build_course_context(self.student.user)
        self.assertIn("not currently enrolled", context["prompt_item"]["text"])
        self.assertEqual(context["sources"], [])

    def test_teacher_caller_gets_no_teacher_side_analytics(self):
        context = build_course_context(self.offering_teacher.user)
        self.assertEqual(context["sources"], [])
        self.assertIn("No course information is available", context["prompt_item"]["text"])

    def test_anonymous_user_gets_no_course_data(self):
        context = build_course_context(AnonymousUser())
        self.assertEqual(context["sources"], [])

    def test_prompt_item_has_no_real_created_at(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)
        context = build_course_context(self.student.user)
        self.assertEqual(context["prompt_item"]["created_at"], "")
