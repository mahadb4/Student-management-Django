"""
Phase 4 tests: the embed_remark persistence operation.

A fake embedding service is injected everywhere - no real Gemini API calls,
no real GEMINI_API_KEY required.
"""
from datetime import date

from django.test import TestCase

from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_embedding_service import EMBEDDING_DIMENSIONS, EmbeddingGenerationError
from ai_assistant.services.remark_embedding_service import embed_remark, remark_embedding_is_stale
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class _FakeEmbeddingService:
    def __init__(self, values=None, exception=None):
        # 0.25 is exactly representable in float32, so it survives the
        # pgvector DB round-trip without precision drift affecting equality
        # assertions below.
        self._values = values or [0.25] * EMBEDDING_DIMENSIONS
        self._exception = exception
        self.calls = []

    def embed_text(self, text):
        self.calls.append(text)
        if self._exception:
            raise self._exception
        return self._values


class RemarkEmbeddingServiceTests(TestCase):

    def setUp(self):
        department = Department.objects.create(name="Computing", code="CMP")
        section = Section.objects.create(
            name="A", department=department, semester_number=1, academic_year=2026,
        )
        teacher_user = User.objects.create_user(email="t@example.com", name="Teacher", password="x", role="teacher")
        self.teacher = Teacher.objects.create(
            user=teacher_user, employee_id="EMP-A", phone_number="1234567",
            department=department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )
        student_user = User.objects.create_user(email="s@example.com", name="Student", password="x", role="student")
        self.student = Student.objects.create(
            user=student_user, parents_phone_number="1234567", department=department, section=section,
        )
        course = Course.objects.create(
            name="Databases", code="CS101", credits=3, department=department, teacher=self.teacher,
        )
        self.offering = CourseOffering.objects.create(
            course=course, teacher=self.teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=section,
        )
        self.remark = Remark.objects.create(
            student=self.student, teacher=self.teacher, course_offering=self.offering,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )

    # ── create / update, no duplication ─────────────────────────────────

    def test_embed_remark_creates_embedding(self):
        service = _FakeEmbeddingService()
        embed_remark(self.remark, embedding_service=service)

        self.assertEqual(RemarkEmbedding.objects.filter(remark=self.remark).count(), 1)
        obj = RemarkEmbedding.objects.get(remark=self.remark)
        self.assertEqual(len(obj.embedding), EMBEDDING_DIMENSIONS)

    def test_embed_remark_updates_existing_embedding_not_duplicate(self):
        service = _FakeEmbeddingService(values=[0.5] * EMBEDDING_DIMENSIONS)
        embed_remark(self.remark, embedding_service=service)

        service2 = _FakeEmbeddingService(values=[0.125] * EMBEDDING_DIMENSIONS)
        embed_remark(self.remark, embedding_service=service2)

        self.assertEqual(RemarkEmbedding.objects.filter(remark=self.remark).count(), 1)
        obj = RemarkEmbedding.objects.get(remark=self.remark)
        self.assertEqual(list(obj.embedding), [0.125] * EMBEDDING_DIMENSIONS)

    def test_embedded_text_matches_text_actually_embedded(self):
        service = _FakeEmbeddingService()
        embed_remark(self.remark, embedding_service=service)

        obj = RemarkEmbedding.objects.get(remark=self.remark)
        self.assertEqual(obj.embedded_text, "Struggling with joins.")
        self.assertEqual(service.calls, ["Struggling with joins."])

    def test_only_remark_text_is_sent_to_the_embedding_service(self):
        # Guards against accidentally constructing a string containing
        # teacher/student/course names - only remark.remark_text may be sent.
        service = _FakeEmbeddingService()
        embed_remark(self.remark, embedding_service=service)

        self.assertEqual(service.calls, [self.remark.remark_text])
        for leaked in ("Teacher", "Student", "Databases", "CS101"):
            self.assertNotIn(leaked, service.calls[0])

    # ── failure handling: no invalid rows ───────────────────────────────

    def test_embedding_failure_does_not_create_a_row(self):
        service = _FakeEmbeddingService(exception=EmbeddingGenerationError("boom"))

        with self.assertRaises(EmbeddingGenerationError):
            embed_remark(self.remark, embedding_service=service)

        self.assertEqual(RemarkEmbedding.objects.filter(remark=self.remark).count(), 0)

    def test_embedding_failure_does_not_corrupt_existing_row(self):
        service = _FakeEmbeddingService(values=[0.5] * EMBEDDING_DIMENSIONS)
        embed_remark(self.remark, embedding_service=service)

        failing_service = _FakeEmbeddingService(exception=EmbeddingGenerationError("boom"))
        with self.assertRaises(EmbeddingGenerationError):
            embed_remark(self.remark, embedding_service=failing_service)

        obj = RemarkEmbedding.objects.get(remark=self.remark)
        self.assertEqual(list(obj.embedding), [0.5] * EMBEDDING_DIMENSIONS)

    # ── Remark model itself is unchanged ────────────────────────────────

    def test_remark_model_has_no_new_concrete_fields(self):
        concrete_field_names = {f.name for f in Remark._meta.fields}
        self.assertEqual(
            concrete_field_names,
            {"id", "student", "teacher", "course_offering", "remark_text", "visibility", "created_at", "updated_at"},
        )

    # ── staleness detection ──────────────────────────────────────────────

    def test_remark_with_no_embedding_is_stale(self):
        self.assertTrue(remark_embedding_is_stale(self.remark))

    def test_remark_with_matching_embedded_text_is_not_stale(self):
        embed_remark(self.remark, embedding_service=_FakeEmbeddingService())
        self.remark.refresh_from_db()
        self.assertFalse(remark_embedding_is_stale(self.remark))

    def test_remark_with_changed_text_is_stale(self):
        embed_remark(self.remark, embedding_service=_FakeEmbeddingService())
        self.remark.remark_text = "Now doing much better with joins."
        self.remark.save(update_fields=["remark_text"])
        self.remark.refresh_from_db()
        self.assertTrue(remark_embedding_is_stale(self.remark))

    # ── cascade delete ───────────────────────────────────────────────────

    def test_deleting_remark_deletes_its_embedding(self):
        embed_remark(self.remark, embedding_service=_FakeEmbeddingService())
        self.assertEqual(RemarkEmbedding.objects.count(), 1)

        self.remark.delete()

        self.assertEqual(RemarkEmbedding.objects.count(), 0)
