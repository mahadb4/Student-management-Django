"""
Phase 10C tests: build_assignment_context.

Authorization is entirely delegated to
assignments.authorization.get_assignments_queryset_for_user (unchanged) -
these tests focus on the new status-derivation logic (submitted/overdue/
pending) and re-confirm the scoping boundary holds through this new entry
point too, including DROPPED-enrollment exclusion and cross-student
submission isolation.
"""
from datetime import date, timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from ai_assistant.context.assignment_context import build_assignment_context
from assignments.models import Assignment, Submission
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class AssignmentContextTests(TestCase):

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
            name="Databases", code="CS101", credits=3, department=self.department, teacher=self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.dropped_course = Course.objects.create(
            name="Networks", code="CS102", credits=3, department=self.department, teacher=self.teacher,
        )
        self.dropped_offering = CourseOffering.objects.create(
            course=self.dropped_course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=self.section,
        )

        self.enrollment = Enrollment.objects.create(
            student=self.student, course_offering=self.offering, status=Enrollment.Status.ACTIVE,
        )
        # Both students enrolled in the same offering, for cross-student isolation checks.
        self.other_enrollment = Enrollment.objects.create(
            student=self.other_student, course_offering=self.offering, status=Enrollment.Status.ACTIVE,
        )
        Enrollment.objects.create(
            student=self.student, course_offering=self.dropped_offering, status=Enrollment.Status.DROPPED,
        )

        now = timezone.now()
        self.overdue_assignment = Assignment.objects.create(
            course_offering=self.offering, teacher=self.teacher,
            title="Past Homework", description="", due_at=now - timedelta(days=2),
        )
        self.pending_assignment = Assignment.objects.create(
            course_offering=self.offering, teacher=self.teacher,
            title="Upcoming Homework", description="", due_at=now + timedelta(days=5),
        )
        self.submitted_assignment = Assignment.objects.create(
            course_offering=self.offering, teacher=self.teacher,
            title="Completed Homework", description="", due_at=now + timedelta(days=1),
            attachment_key="assignments/3/attachment.pdf",
        )
        Submission.objects.create(assignment=self.submitted_assignment, student=self.student, file_key="submissions/x.pdf")

        # A DROPPED-course assignment - must never appear for `student`.
        self.dropped_course_assignment = Assignment.objects.create(
            course_offering=self.dropped_offering, teacher=self.teacher,
            title="Networks Homework", description="", due_at=now + timedelta(days=3),
        )

        # Another student's own submission on a shared assignment - must
        # never affect `student`'s own status for that same assignment.
        Submission.objects.create(assignment=self.pending_assignment, student=self.other_student, file_key="submissions/y.pdf")

    def test_overdue_pending_submitted_statuses_derived_correctly(self):
        context = build_assignment_context(self.student.user)
        by_title = {s["title"]: s for s in context["sources"]}
        self.assertEqual(by_title["Past Homework"]["status"], "overdue")
        self.assertEqual(by_title["Upcoming Homework"]["status"], "pending")
        self.assertEqual(by_title["Completed Homework"]["status"], "submitted")

    def test_counts_summarized_in_prompt_text(self):
        context = build_assignment_context(self.student.user)
        text = context["prompt_item"]["text"]
        self.assertIn("3 total assignments", text)
        self.assertIn("1 overdue", text)
        self.assertIn("1 pending", text)
        self.assertIn("1 submitted", text)

    def test_summary_text_explicitly_disclaims_grading(self):
        # The point isn't that the word "grade" never appears - it's that
        # the text never CLAIMS a grade/review happened. The correct way to
        # prevent that implication is an explicit disclaimer, which is what
        # this asserts (rather than banning the word "grade" outright, which
        # would also flag the disclaimer sentence itself as a false positive).
        context = build_assignment_context(self.student.user)
        text = context["prompt_item"]["text"].lower()
        self.assertIn("does not mean graded", text)
        self.assertNotIn("has been graded", text)
        self.assertNotIn("your grade", text)
        self.assertNotIn("teacher reviewed", text)

    def test_dropped_enrollment_assignment_excluded(self):
        context = build_assignment_context(self.student.user)
        titles = {s["title"] for s in context["sources"]}
        self.assertNotIn("Networks Homework", titles)

    def test_another_students_submission_does_not_affect_this_students_status(self):
        # other_student submitted pending_assignment - student did not.
        # student's own status for that assignment must still be "pending".
        context = build_assignment_context(self.student.user)
        by_title = {s["title"]: s for s in context["sources"]}
        self.assertEqual(by_title["Upcoming Homework"]["status"], "pending")

    def test_another_students_assignments_never_leak(self):
        # other_student is enrolled in the same offering, so this mainly
        # confirms no duplicate/foreign rows sneak in via the join.
        context = build_assignment_context(self.student.user)
        self.assertEqual(len(context["sources"]), 3)

    def test_attachment_presence_only_no_content(self):
        context = build_assignment_context(self.student.user)
        by_title = {s["title"]: s for s in context["sources"]}
        self.assertTrue(by_title["Completed Homework"]["attachment_available"])
        self.assertFalse(by_title["Past Homework"]["attachment_available"])
        # No S3 key, URL, or file content anywhere in the source or prompt text.
        dump = str(context)
        self.assertNotIn("attachment_key", dump)
        self.assertNotIn(".pdf", dump)
        self.assertNotIn("assignments/3/attachment", dump)

    def test_sources_are_assignment_typed(self):
        context = build_assignment_context(self.student.user)
        for source in context["sources"]:
            self.assertEqual(source["type"], "assignment")

    def test_no_assignments_produces_safe_text_and_no_sources(self):
        empty_user = User.objects.create_user(email="lonely@example.com", name="Lonely", password="x", role="student")
        Student.objects.create(
            user=empty_user, parents_phone_number="1234567", department=self.department, section=self.section,
        )
        context = build_assignment_context(empty_user)
        self.assertIn("doesn't currently have any assignments recorded", context["prompt_item"]["text"])
        self.assertEqual(context["sources"], [])

    def test_teacher_caller_gets_no_teacher_side_analytics(self):
        # Phase 10C is explicitly student-focused - a teacher asking gets a
        # safe "not available" response, not course-level submission counts.
        context = build_assignment_context(self.teacher.user)
        self.assertEqual(context["sources"], [])
        self.assertIn("No assignment information is available", context["prompt_item"]["text"])

    def test_anonymous_user_gets_no_assignment_data(self):
        context = build_assignment_context(AnonymousUser())
        self.assertEqual(context["sources"], [])

    def test_prompt_item_has_no_real_created_at(self):
        context = build_assignment_context(self.student.user)
        self.assertEqual(context["prompt_item"]["created_at"], "")
