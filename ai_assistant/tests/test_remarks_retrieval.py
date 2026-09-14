"""
Phase 2 tests: the remarks retrieval shaping layer.

Phase 1 (test_scope.py) already proved get_remarks_queryset_for_user scopes
correctly. These tests do NOT re-verify that boundary from scratch - they
check the narrower thing Phase 2 actually adds: that shaping the authorized
queryset into a context list introduces no leak, and that the output shape/
ordering/limit contract holds.
"""
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from remarks.authorization import get_remarks_queryset_for_user
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User

from ai_assistant.retrieval.remarks import get_remark_context_for_user


class RemarkContextRetrievalTests(TestCase):

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        def make_teacher(email, name, employee_id):
            user = User.objects.create_user(email=email, name=name, password="x", role="teacher")
            return Teacher.objects.create(
                user=user, employee_id=employee_id, phone_number="1234567",
                department=self.department, designation="Lecturer", qualification="MSc",
                date_of_joining=date(2020, 1, 1), salary=1,
            )

        def make_student(email, name):
            user = User.objects.create_user(email=email, name=name, password="x", role="student")
            return Student.objects.create(
                user=user, parents_phone_number="1234567",
                department=self.department, section=self.section,
            )

        self.teacher_a = make_teacher("teacher.a@example.com", "Teacher A", "EMP-A")
        self.teacher_b = make_teacher("teacher.b@example.com", "Teacher B", "EMP-B")

        self.course_a = Course.objects.create(
            name="Databases", code="CS101", credits=3, department=self.department, teacher=self.teacher_a,
        )
        self.course_b = Course.objects.create(
            name="Networks", code="CS102", credits=3, department=self.department, teacher=self.teacher_b,
        )

        self.offering_a = CourseOffering.objects.create(
            course=self.course_a, teacher=self.teacher_a, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )
        self.offering_b = CourseOffering.objects.create(
            course=self.course_b, teacher=self.teacher_b, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.student_57 = make_student("student57@example.com", "Student 57")
        Enrollment.objects.create(student=self.student_57, course_offering=self.offering_a)

        self.student_80 = make_student("student80@example.com", "Student 80")
        Enrollment.objects.create(student=self.student_80, course_offering=self.offering_b)

        self.private_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )
        self.visible_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Improved significantly.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )

    # ── Leak check: output ids must be a subset of the authorized queryset ─

    def test_student_context_contains_only_authorized_remark_ids(self):
        context = get_remark_context_for_user(self.student_57.user)
        authorized_ids = set(get_remarks_queryset_for_user(self.student_57.user).values_list("id", flat=True))
        context_ids = {item["id"] for item in context}
        self.assertTrue(context_ids.issubset(authorized_ids))
        self.assertEqual(context_ids, {self.visible_remark.id})

    def test_student_private_remark_excluded_from_context(self):
        context = get_remark_context_for_user(self.student_57.user)
        ids = {item["id"] for item in context}
        self.assertNotIn(self.private_remark.id, ids)

    def test_student_cannot_pull_another_students_remarks_into_context(self):
        context = get_remark_context_for_user(self.student_80.user, student_id=self.student_57.id)
        self.assertEqual(context, [])

    def test_teacher_context_includes_private_and_visible(self):
        context = get_remark_context_for_user(self.teacher_a.user)
        ids = {item["id"] for item in context}
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})

    def test_teacher_b_gets_empty_context_for_teacher_a_data(self):
        context = get_remark_context_for_user(self.teacher_b.user)
        self.assertEqual(context, [])

    def test_unauthorized_student_id_probe_returns_empty_context(self):
        # Mirrors Phase 1's anti-enumeration test, through the new function:
        # teacher_a has no relationship to student_80.
        context = get_remark_context_for_user(self.teacher_a.user, student_id=self.student_80.id)
        self.assertEqual(context, [])

    # ── Shape / ordering / limit contract ───────────────────────────────

    def test_context_shape_has_expected_keys(self):
        context = get_remark_context_for_user(self.teacher_a.user)
        self.assertTrue(len(context) > 0)
        for item in context:
            self.assertEqual(
                set(item.keys()), {"id", "text", "teacher_name", "course_name", "visibility", "created_at"},
            )

    def test_context_ordered_most_recent_first(self):
        context = get_remark_context_for_user(self.teacher_a.user)
        self.assertEqual([item["id"] for item in context], [self.visible_remark.id, self.private_remark.id])

    def test_context_respects_limit(self):
        for i in range(5):
            Remark.objects.create(
                student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
                remark_text=f"Extra remark {i}", visibility=Remark.Visibility.PRIVATE,
            )
        context = get_remark_context_for_user(self.teacher_a.user, limit=3)
        self.assertEqual(len(context), 3)

    # ── Anonymous ────────────────────────────────────────────────────────

    def test_anonymous_user_gets_empty_context(self):
        context = get_remark_context_for_user(AnonymousUser())
        self.assertEqual(context, [])
