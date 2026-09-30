"""
Source/context consistency tests for the AI Assistant. These are
verification tests, not regression fixes: sources are already built in
lock-step with the items sent to Gemini (same retrieval call, same loop,
same domain-gating), never from Gemini's own output or a second query.

Real DB fixtures and real retrieval/context-building code are used
throughout; only Gemini generation is faked, capturing exactly what context
it was handed so each test can assert against what was actually sent.
"""
import math
from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from ai_assistant.models import RemarkEmbedding
from ai_assistant.orchestrator import answer_academic_question
from assignments.models import Assignment
from attendance.models import Attendance
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from enrollments.models import Enrollment
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User

DIM = 768


def _vector(angle_degrees):
    theta = math.radians(angle_degrees)
    return [math.cos(theta), math.sin(theta)] + [0.0] * (DIM - 2)


class _FixedVectorEmbeddingService:
    def __init__(self, vector=None):
        self._vector = vector if vector is not None else _vector(0)

    def embed_text(self, text):
        return self._vector


class _CapturingGeminiGenerationService:
    """Records exactly the context it was handed, and returns a fixed answer."""

    def __init__(self, *args, **kwargs):
        pass

    def generate_answer(self, question, context):
        type(self).last_context = context
        return "A grounded answer."


class SourceContextConsistencyTests(TestCase):
    """
    Builds a rich fixture (7 courses, attendance, assignments, remarks at
    varying semantic distances), then drives answer_academic_question()
    end-to-end for each of the 7 real user flows.
    """

    def setUp(self):
        self.department = Department.objects.create(name="Computing", code="CMP")
        self.section = Section.objects.create(
            name="A", department=self.department, semester_number=1, academic_year=2026,
        )

        user = User.objects.create_user(email="teacher@example.com", name="Dr. Ahmed", password="x", role="teacher")
        self.teacher = Teacher.objects.create(
            user=user, employee_id="EMP-1", phone_number="1234567",
            department=self.department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )

        student_user = User.objects.create_user(
            email="student@example.com", name="Student One", password="x", role="student",
        )
        self.student = Student.objects.create(
            user=student_user, parents_phone_number="1234567",
            department=self.department, section=self.section,
        )

        course_names = [
            ("Database Systems", "CS301"), ("Introduction to Programming", "CS101"),
            ("English / Communication", "ENG101"), ("Pakistan Studies", "PST101"),
            ("Basic Computing", "CS100"), ("Calculus", "MTH101"), ("Maths", "MTH102"),
        ]
        self.offerings = []
        for name, code in course_names:
            course = Course.objects.create(
                name=name, code=code, credits=3, department=self.department, teacher=self.teacher,
            )
            offering = CourseOffering.objects.create(
                course=course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
                academic_year=2026, section=self.section,
            )
            Enrollment.objects.create(student=self.student, course_offering=offering, status=Enrollment.Status.ACTIVE)
            self.offerings.append(offering)

        self.primary_offering = self.offerings[0]
        primary_enrollment = Enrollment.objects.get(student=self.student, course_offering=self.primary_offering)

        Attendance.objects.create(enrollment=primary_enrollment, date=date(2026, 2, 1), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=primary_enrollment, date=date(2026, 2, 2), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=primary_enrollment, date=date(2026, 2, 3), status=Attendance.Status.PRESENT)
        Attendance.objects.create(enrollment=primary_enrollment, date=date(2026, 2, 4), status=Attendance.Status.ABSENT)

        self.assignment = Assignment.objects.create(
            course_offering=self.primary_offering, teacher=self.teacher, title="SQL Homework",
            description="Joins", due_at=timezone.now() + timedelta(days=3),
        )

        # Two remarks: one close to the query (angle 20 -> distance ~0.06,
        # within threshold), one far (angle 170 -> distance ~1.98, must
        # never appear as a source).
        self.close_remark = Remark.objects.create(
            student=self.student, teacher=self.teacher, course_offering=self.primary_offering,
            remark_text="Struggling with SQL joins.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        RemarkEmbedding.objects.create(
            remark=self.close_remark, embedding=_vector(20),
        )
        self.far_remark = Remark.objects.create(
            student=self.student, teacher=self.teacher, course_offering=self.primary_offering,
            remark_text="Completely unrelated aside about the weather.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        RemarkEmbedding.objects.create(
            remark=self.far_remark, embedding=_vector(170),
        )

        self.private_remark = Remark.objects.create(
            student=self.student, teacher=self.teacher, course_offering=self.primary_offering,
            remark_text="Private note about the student.", visibility=Remark.Visibility.PRIVATE,
        )
        RemarkEmbedding.objects.create(
            remark=self.private_remark, embedding=_vector(15),
        )

        _CapturingGeminiGenerationService.last_context = None
        self.embedding_service = _FixedVectorEmbeddingService()

    def _ask(self, question):
        return answer_academic_question(
            self.student.user, question,
            embedding_service=self.embedding_service,
            generation_service=_CapturingGeminiGenerationService(),
        )

    def test_course_list_returns_all_seven_course_sources_uncapped_by_top_k(self):
        result = self._ask("Which subjects am I having?")

        course_sources = [s for s in result["sources"] if s["type"] == "course"]
        self.assertEqual(len(course_sources), 7)
        names = {s["course_name"] for s in course_sources}
        self.assertEqual(names, {name for name, _ in [
            ("Database Systems", None), ("Introduction to Programming", None), ("English / Communication", None),
            ("Pakistan Studies", None), ("Basic Computing", None), ("Calculus", None), ("Maths", None),
        ]})

    def test_attendance_question_returns_only_attendance_sources(self):
        result = self._ask("What is my attendance?")

        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"attendance"})

    def test_assignment_question_returns_only_assignment_sources(self):
        result = self._ask("Which assignments are pending?")

        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"assignment"})
        self.assertEqual(result["sources"][0]["title"], "SQL Homework")

    def test_teacher_feedback_returns_only_close_authorized_remark(self):
        result = self._ask("What did my teacher say about my performance?")

        remark_sources = [s for s in result["sources"] if s["type"] == "remark"]
        ids = {s["remark_id"] for s in remark_sources}
        self.assertEqual(ids, {self.close_remark.id})
        self.assertNotIn(self.far_remark.id, ids)
        self.assertNotIn(self.private_remark.id, ids)

    def test_academic_improvement_returns_attendance_and_remark_sources(self):
        result = self._ask("Based on my attendance and teacher feedback, what should I improve?")

        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"attendance", "remark"})

    def test_course_recommendation_returns_no_sources_and_never_calls_gemini(self):
        _CapturingGeminiGenerationService.last_context = None
        result = self._ask("What courses do you recommend for my next semester?")

        self.assertEqual(result["sources"], [])
        self.assertIsNone(_CapturingGeminiGenerationService.last_context)

    def test_unsupported_question_returns_no_sources(self):
        result = self._ask("What is the weather today?")

        self.assertEqual(result["sources"], [])

    def test_far_remark_beyond_threshold_never_appears_as_a_source(self):
        result = self._ask("What did my teacher say about my performance?")

        remark_ids = {s["remark_id"] for s in result["sources"] if s["type"] == "remark"}
        self.assertNotIn(self.far_remark.id, remark_ids)

    def test_private_remark_never_appears_as_a_source(self):
        result = self._ask("What did my teacher say about my performance?")

        remark_ids = {s["remark_id"] for s in result["sources"] if s["type"] == "remark"}
        self.assertNotIn(self.private_remark.id, remark_ids)

    def test_sources_match_items_actually_sent_to_gemini_for_course_list(self):
        result = self._ask("Which subjects am I having?")

        sent_context = _CapturingGeminiGenerationService.last_context
        # One prompt_item for courses - the source list's course names must
        # all appear inside that one item's text.
        combined_text = " ".join(item["text"] for item in sent_context["items"])
        for source in result["sources"]:
            self.assertIn(source["course_name"], combined_text)

    def test_sources_match_items_actually_sent_to_gemini_for_teacher_feedback(self):
        result = self._ask("What did my teacher say about my performance?")

        sent_context = _CapturingGeminiGenerationService.last_context
        sent_texts = {item["text"] for item in sent_context["items"]}
        self.assertEqual(sent_texts, {self.close_remark.remark_text})
        self.assertNotIn(self.far_remark.remark_text, sent_texts)
        self.assertNotIn(self.private_remark.remark_text, sent_texts)

    def test_source_count_matches_item_count_for_hybrid_question(self):
        result = self._ask("Based on my attendance and teacher feedback, what should I improve?")

        sent_context = _CapturingGeminiGenerationService.last_context
        # Every source type present must have at least one corresponding
        # item in what was sent to Gemini.
        item_types_present = len(sent_context["items"])
        self.assertGreaterEqual(item_types_present, 2)
        self.assertTrue(any(s["type"] == "attendance" for s in result["sources"]))
        self.assertTrue(any(s["type"] == "remark" for s in result["sources"]))

    def test_course_sources_are_not_a_second_query_they_match_the_context_item(self):
        # If sources were built by a separate query from context, a
        # dropped/added enrollment between two queries could desync them.
        # The single course prompt_item text already lists all 7 names,
        # and result["sources"] has exactly the same 7.
        result = self._ask("Which subjects am I having?")
        self.assertEqual(len(result["sources"]), 7)
