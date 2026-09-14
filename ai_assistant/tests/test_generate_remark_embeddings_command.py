"""
Phase 4 tests: the generate_remark_embeddings backfill command.

GeminiEmbeddingService is patched at its import site inside the command
module, so no real Gemini API calls happen and no real GEMINI_API_KEY is
required.
"""
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_embedding_service import EMBEDDING_DIMENSIONS, EmbeddingGenerationError
from course_offerings.models import CourseOffering
from courses.models import Course
from departments.models import Department
from remarks.models import Remark
from sections.models import Section
from students.models import Student
from teachers.models import Teacher
from users.models import User


class _FakeEmbeddingService:
    def __init__(self, fail_for_remark_ids=None):
        self._fail_for_remark_ids = fail_for_remark_ids or set()

    def embed_text(self, text):
        return [0.25] * EMBEDDING_DIMENSIONS


class GenerateRemarkEmbeddingsCommandTests(TestCase):

    def setUp(self):
        department = Department.objects.create(name="Computing", code="CMP")
        section = Section.objects.create(
            name="A", department=department, semester_number=1, academic_year=2026,
        )
        teacher_user = User.objects.create_user(email="t@example.com", name="Teacher", password="x", role="teacher")
        teacher = Teacher.objects.create(
            user=teacher_user, employee_id="EMP-A", phone_number="1234567",
            department=department, designation="Lecturer", qualification="MSc",
            date_of_joining=date(2020, 1, 1), salary=1,
        )
        student_user = User.objects.create_user(email="s@example.com", name="Student", password="x", role="student")
        student = Student.objects.create(
            user=student_user, parents_phone_number="1234567", department=department, section=section,
        )
        course = Course.objects.create(
            name="Databases", code="CS101", credits=3, department=department, teacher=teacher,
        )
        offering = CourseOffering.objects.create(
            course=course, teacher=teacher, semester=CourseOffering.Semester.FALL,
            academic_year=2026, section=section,
        )
        self.remark_a = Remark.objects.create(
            student=student, teacher=teacher, course_offering=offering,
            remark_text="Struggling with joins.", visibility=Remark.Visibility.PRIVATE,
        )
        self.remark_b = Remark.objects.create(
            student=student, teacher=teacher, course_offering=offering,
            remark_text="Improved significantly.", visibility=Remark.Visibility.STUDENT_VISIBLE,
        )

    def _run_command(self, **options):
        out = StringIO()
        call_command("generate_remark_embeddings", stdout=out, **options)
        return out.getvalue()

    @patch("ai_assistant.management.commands.generate_remark_embeddings.GeminiEmbeddingService")
    def test_backfill_creates_missing_embeddings(self, mock_service_cls):
        mock_service_cls.return_value = _FakeEmbeddingService()

        self._run_command()

        self.assertEqual(RemarkEmbedding.objects.count(), 2)
        self.assertTrue(RemarkEmbedding.objects.filter(remark=self.remark_a).exists())
        self.assertTrue(RemarkEmbedding.objects.filter(remark=self.remark_b).exists())

    @patch("ai_assistant.management.commands.generate_remark_embeddings.GeminiEmbeddingService")
    def test_backfill_does_not_create_duplicates_on_rerun(self, mock_service_cls):
        mock_service_cls.return_value = _FakeEmbeddingService()

        self._run_command()
        self._run_command()

        self.assertEqual(RemarkEmbedding.objects.count(), 2)

    @patch("ai_assistant.management.commands.generate_remark_embeddings.GeminiEmbeddingService")
    def test_backfill_skips_already_up_to_date_remarks_on_rerun(self, mock_service_cls):
        mock_service_cls.return_value = _FakeEmbeddingService()

        self._run_command()
        output = self._run_command()

        self.assertIn("Already up to date: 2", output)
        self.assertIn("Embedded 0 remark(s)", output)

    @patch("ai_assistant.management.commands.generate_remark_embeddings.GeminiEmbeddingService")
    def test_dry_run_does_not_write_to_database(self, mock_service_cls):
        mock_service_cls.return_value = _FakeEmbeddingService()

        self._run_command(dry_run=True)

        self.assertEqual(RemarkEmbedding.objects.count(), 0)

    @patch("ai_assistant.management.commands.generate_remark_embeddings.GeminiEmbeddingService")
    def test_api_failure_for_one_remark_does_not_block_others_or_create_invalid_rows(self, mock_service_cls):
        class _PartiallyFailingService:
            def embed_text(self, text):
                if text == "Struggling with joins.":
                    raise EmbeddingGenerationError("simulated failure")
                return [0.25] * EMBEDDING_DIMENSIONS

        mock_service_cls.return_value = _PartiallyFailingService()

        output = self._run_command()

        self.assertFalse(RemarkEmbedding.objects.filter(remark=self.remark_a).exists())
        self.assertTrue(RemarkEmbedding.objects.filter(remark=self.remark_b).exists())
        self.assertIn("Failed: 1", output)

    @patch("ai_assistant.management.commands.generate_remark_embeddings.GeminiEmbeddingService")
    def test_command_output_never_contains_api_key_text(self, mock_service_cls):
        from django.conf import settings

        mock_service_cls.return_value = _FakeEmbeddingService()
        output = self._run_command()

        self.assertNotIn(settings.GEMINI_API_KEY, output)
