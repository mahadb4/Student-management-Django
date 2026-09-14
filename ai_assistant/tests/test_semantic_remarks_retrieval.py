"""
Phase 5 tests: permission-aware semantic retrieval over Remarks.

No real Gemini API calls - a fake embedding service is injected everywhere,
returning hand-crafted 768-dim vectors so distances/ordering are exactly
predictable. RemarkEmbedding rows are created directly (bypassing
embed_remark) with the same hand-crafted vectors, so this file tests
retrieval/authorization behavior, not the embedding-generation pipeline
(already covered in test_remark_embedding_service.py).
"""
import math
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from ai_assistant.models import RemarkEmbedding
from ai_assistant.retrieval.semantic_remarks import get_semantically_relevant_remarks
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
    """
    A 768-dim vector living in the plane spanned by the first two axes:
    [cos(theta), sin(theta), 0, 0, ..., 0]. Cosine distance from the
    angle-0 vector ([1, 0, 0, ...]) is exactly 1 - cos(theta_radians),
    so angle directly controls, and predicts, pgvector's CosineDistance.
    """
    theta = math.radians(angle_degrees)
    return [math.cos(theta), math.sin(theta)] + [0.0] * (DIM - 2)


class _FixedVectorEmbeddingService:
    """Always returns the same pre-set query vector, regardless of text."""

    def __init__(self, vector):
        self._vector = vector

    def embed_text(self, text):
        return self._vector


class SemanticRemarksRetrievalTests(TestCase):

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

        # Remarks about student_57, in teacher_a's offering.
        self.private_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )
        self.visible_remark = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="Improved significantly.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        # Remark about student_80, in teacher_b's offering - unrelated to teacher_a/student_57.
        self.other_teacher_remark = Remark.objects.create(
            student=self.student_80, teacher=self.teacher_b, course_offering=self.offering_b,
            remark_text="Excellent grasp of routing.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )

        # Query vector = angle 0. Give each remark its own embedding at a
        # controlled angle, so distance-from-query is exactly predictable.
        RemarkEmbedding.objects.create(
            remark=self.private_remark, embedding=_vector(60), embedded_text=self.private_remark.remark_text,
        )
        RemarkEmbedding.objects.create(
            remark=self.visible_remark, embedding=_vector(30), embedded_text=self.visible_remark.remark_text,
        )
        RemarkEmbedding.objects.create(
            remark=self.other_teacher_remark, embedding=_vector(10),
            embedded_text=self.other_teacher_remark.remark_text,
        )

        self.query_service = _FixedVectorEmbeddingService(_vector(0))

    # ── Student authorization ───────────────────────────────────────────

    def test_student_retrieves_only_own_authorized_remarks(self):
        results = get_semantically_relevant_remarks(
            self.student_57.user, "how am I doing", embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertEqual(ids, {self.visible_remark.id})

    def test_student_cannot_retrieve_private_remarks(self):
        results = get_semantically_relevant_remarks(
            self.student_57.user, "how am I doing", embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertNotIn(self.private_remark.id, ids)

    def test_student_cannot_retrieve_another_students_remarks(self):
        # get_remarks_queryset_for_user's student branch ignores student_id
        # entirely - a student is always scoped to their OWN remarks,
        # regardless of what student_id is passed. So student_80 passing
        # student_57's id does not leak student_57's data; it just returns
        # student_80's own (unrelated) authorized remark.
        results = get_semantically_relevant_remarks(
            self.student_80.user, "feedback", student_id=self.student_57.id, embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertNotIn(self.visible_remark.id, ids)  # student_57's remark must never leak
        self.assertNotIn(self.private_remark.id, ids)
        self.assertEqual(ids, {self.other_teacher_remark.id})  # student_80's own remark, unaffected

    # ── Teacher authorization ────────────────────────────────────────────

    def test_teacher_retrieves_remarks_from_own_offerings(self):
        results = get_semantically_relevant_remarks(
            self.teacher_a.user, "class performance", embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id})

    def test_teacher_cannot_retrieve_another_teachers_remarks(self):
        results = get_semantically_relevant_remarks(
            self.teacher_b.user, "class performance", embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertNotIn(self.private_remark.id, ids)
        self.assertNotIn(self.visible_remark.id, ids)
        self.assertEqual(ids, {self.other_teacher_remark.id})

    def test_cross_teacher_student_id_probe_returns_no_unauthorized_data(self):
        # teacher_a has no relationship to student_80 at all.
        results = get_semantically_relevant_remarks(
            self.teacher_a.user, "feedback", student_id=self.student_80.id, embedding_service=self.query_service,
        )
        self.assertEqual(results, [])

    # ── Anonymous / superuser ────────────────────────────────────────────

    def test_anonymous_user_gets_no_results(self):
        results = get_semantically_relevant_remarks(
            AnonymousUser(), "how am I doing", embedding_service=self.query_service,
        )
        self.assertEqual(results, [])

    def test_superuser_sees_all_embedded_remarks(self):
        superuser = User.objects.create_superuser(email="root@example.com", name="Root", password="x")
        results = get_semantically_relevant_remarks(
            superuser, "everything", embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertEqual(ids, {self.private_remark.id, self.visible_remark.id, self.other_teacher_remark.id})

    # ── THE critical security test ──────────────────────────────────────

    def test_unauthorized_but_more_similar_remark_is_never_returned(self):
        # other_teacher_remark's embedding (angle 10) is far more similar
        # to the query (angle 0) than visible_remark's embedding (angle 30)
        # is. If authorization were applied AFTER a broad similarity
        # search, other_teacher_remark would rank first. It must never
        # appear at all for student_57, regardless of similarity.
        results = get_semantically_relevant_remarks(
            self.student_57.user, "routing feedback", embedding_service=self.query_service,
        )
        ids = [r["remark_id"] for r in results]

        self.assertNotIn(self.other_teacher_remark.id, ids)
        self.assertEqual(ids, [self.visible_remark.id])

    # ── Ordering ─────────────────────────────────────────────────────────

    def test_results_ordered_by_distance_most_similar_first(self):
        results = get_semantically_relevant_remarks(
            self.teacher_a.user, "performance", embedding_service=self.query_service,
        )
        # visible_remark (angle 30) is closer to the query (angle 0) than
        # private_remark (angle 60).
        self.assertEqual([r["remark_id"] for r in results], [self.visible_remark.id, self.private_remark.id])
        self.assertLess(results[0]["distance"], results[1]["distance"])

    def test_top_k_limits_result_count(self):
        results = get_semantically_relevant_remarks(
            self.teacher_a.user, "performance", top_k=1, embedding_service=self.query_service,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["remark_id"], self.visible_remark.id)

    # ── Missing embeddings ───────────────────────────────────────────────

    def test_remarks_without_embeddings_are_excluded(self):
        unembedded = Remark.objects.create(
            student=self.student_57, teacher=self.teacher_a, course_offering=self.offering_a,
            remark_text="No embedding generated yet.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )
        results = get_semantically_relevant_remarks(
            self.teacher_a.user, "performance", embedding_service=self.query_service,
        )
        ids = {r["remark_id"] for r in results}
        self.assertNotIn(unembedded.id, ids)

    # ── Result shape ─────────────────────────────────────────────────────

    def test_result_shape_has_expected_keys(self):
        results = get_semantically_relevant_remarks(
            self.teacher_a.user, "performance", embedding_service=self.query_service,
        )
        for r in results:
            self.assertEqual(
                set(r.keys()),
                {"remark_id", "text", "teacher_name", "course_name", "visibility", "created_at", "distance"},
            )

    # ── Input validation ─────────────────────────────────────────────────

    def test_empty_query_text_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_semantically_relevant_remarks(self.teacher_a.user, "   ", embedding_service=self.query_service)

    def test_invalid_top_k_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_semantically_relevant_remarks(
                self.teacher_a.user, "performance", top_k=0, embedding_service=self.query_service,
            )
