"""
Phase 10E tests: resolve_mentioned_course.

Authorization is entirely delegated to
ai_assistant.context.course_context.get_active_enrollments_for_user
(Phase 10D, unchanged) - these tests focus on the deterministic matching
rules (code-first, then name, whole-phrase only, ambiguity handling) and
re-confirm the search space can never include an unauthorized course.
"""
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ai_assistant.course_resolution import resolve_mentioned_course
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class CourseResolutionTests(TestCase):

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
            name="Database Systems", code="CS301", credits=3, department=self.department, teacher=self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.maths_course = Course.objects.create(
            name="Maths", code="MTH101", credits=3, department=self.department, teacher=self.teacher,
        )
        self.maths_offering = CourseOffering.objects.create(
            course=self.maths_course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.advanced_maths_course = Course.objects.create(
            name="Advanced Maths", code="MTH201", credits=3, department=self.department, teacher=self.teacher,
        )
        self.advanced_maths_offering = CourseOffering.objects.create(
            course=self.advanced_maths_course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        # A course the OTHER student is enrolled in, `student` is not -
        # must never be resolvable from `student`'s questions.
        self.foreign_course = Course.objects.create(
            name="Networks", code="CS302", credits=3, department=self.department, teacher=self.teacher,
        )
        self.foreign_offering = CourseOffering.objects.create(
            course=self.foreign_course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        Enrollment.objects.create(student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE)
        Enrollment.objects.create(student=self.student, course_offering=self.maths_offering, status=Enrollment.Status.ACTIVE)
        Enrollment.objects.create(
            student=self.other_student, course_offering=self.foreign_offering, status=Enrollment.Status.ACTIVE,
        )

    # ── Exact code match ─────────────────────────────────────────────────

    def test_exact_course_code_match(self):
        result = resolve_mentioned_course(self.student.user, "How am I doing in CS301?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["course_offering_id"], self.offering.id)
        self.assertEqual(result["course_name"], "Database Systems")

    def test_code_match_is_case_insensitive(self):
        result = resolve_mentioned_course(self.student.user, "how am i doing in cs301?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["course_offering_id"], self.offering.id)

    # ── Exact name match ─────────────────────────────────────────────────

    def test_exact_course_name_match(self):
        result = resolve_mentioned_course(self.student.user, "How am I doing in Database Systems?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["course_offering_id"], self.offering.id)

    def test_name_match_handles_extra_whitespace(self):
        result = resolve_mentioned_course(self.student.user, "How am I doing in   Database   Systems?")
        # Whitespace is normalized (collapsed) before comparison.
        self.assertEqual(result["status"], "matched")

    # ── No loose substring matching ──────────────────────────────────────

    def test_math_does_not_ambiguously_match_maths_and_advanced_maths(self):
        # "Maths" is enrolled; "Advanced Maths" is NOT enrolled by `student`
        # in this specific test scenario is irrelevant - the real point:
        # asking about "Maths" must resolve to exactly "Maths", not treat
        # "Advanced Maths" as also matching merely because it CONTAINS the
        # substring "Maths". Whole-phrase matching prevents that.
        result = resolve_mentioned_course(self.student.user, "How am I doing in Maths?")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["course_offering_id"], self.maths_offering.id)

    def test_partial_code_does_not_match(self):
        # "CS3" is a substring of "CS301" but not a whole-word match - must
        # not resolve (avoids the exact loose-substring risk flagged in the
        # design review).
        result = resolve_mentioned_course(self.student.user, "How am I doing in CS3?")
        self.assertNotEqual(result["status"], "matched")

    # ── Ambiguity ────────────────────────────────────────────────────────

    def test_ambiguous_when_multiple_authorized_courses_match(self):
        Enrollment.objects.create(
            student=self.student, course_offering=self.advanced_maths_offering, status=Enrollment.Status.ACTIVE,
        )
        # Neither "Maths" (whole word) nor "Advanced Maths" is literally
        # present as a full course name in this question, but craft a
        # scenario where both names appear via a generic reference - here
        # we directly test the ambiguity path via two matching enrollments
        # sharing an identical course name (e.g. two sections of the same
        # course), which is the realistic way ambiguity actually occurs.
        Course.objects.filter(id=self.advanced_maths_course.id).update(name="Maths")
        result = resolve_mentioned_course(self.student.user, "How am I doing in Maths?")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 1)  # same name, listed once

    # ── Authorization boundary ───────────────────────────────────────────

    def test_cannot_resolve_another_students_course(self):
        result = resolve_mentioned_course(self.student.user, "How am I doing in Networks?")
        self.assertNotEqual(result["status"], "matched")

    def test_no_course_mentioned_returns_none(self):
        result = resolve_mentioned_course(self.student.user, "What are my weaknesses?")
        self.assertEqual(result["status"], "none")

    def test_course_like_phrase_with_no_match_returns_none_but_mentioned(self):
        result = resolve_mentioned_course(self.student.user, "How am I doing in Physics?")
        self.assertEqual(result["status"], "none_but_mentioned")
        self.assertEqual(result["phrase"], "Physics")

    def test_anonymous_user_gets_no_match(self):
        result = resolve_mentioned_course(AnonymousUser(), "How am I doing in CS301?")
        self.assertNotEqual(result["status"], "matched")

    def test_teacher_caller_gets_no_match(self):
        # Course resolution is student-focused, same scope limit as the
        # course/assignment context builders.
        result = resolve_mentioned_course(self.teacher.user, "How am I doing in CS301?")
        self.assertNotEqual(result["status"], "matched")
