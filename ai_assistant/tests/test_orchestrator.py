"""
Phase 10B tests: the orchestrator's domain-selection behavior.

These tests mock every downstream dependency (retrieval, both context
builders, generation) so they can run as SimpleTestCase - no database
involved. That's deliberate: the point of this file is proving the
ORCHESTRATION logic itself (which functions get called, with what,
combined how) is correct, independent of what any one domain's real
authorization does (that's covered separately: Phase 1/5 for remarks,
test_attendance_context.py for attendance).
"""
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase

from ai_assistant.orchestrator import (
    NO_RELEVANT_DOMAIN_MESSAGE,
    NOT_ENOUGH_INFORMATION_MESSAGE,
    answer_academic_question,
)


class OrchestratorTests(SimpleTestCase):

    def setUp(self):
        self.user = AnonymousUser()  # identity is irrelevant here - every call is mocked

    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_attendance_only_question_never_calls_remarks_retrieval(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
    ):
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "attendance", "course_name": "Maths", "detail": "90%"}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Your attendance is 90%."

        result = answer_academic_question(self.user, "How is my attendance?")

        mock_retrieve.assert_not_called()
        mock_build_remark_ctx.assert_not_called()
        mock_build_attendance_ctx.assert_called_once_with(self.user, course_offering_id=None)
        self.assertEqual(result["answer"], "Your attendance is 90%.")
        self.assertEqual(result["sources"], [{"type": "attendance", "course_name": "Maths", "detail": "90%"}])

    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_remarks_only_question_never_calls_attendance_context(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
    ):
        mock_retrieve.return_value = [{"remark_id": 1, "text": "Struggling.", "teacher_name": "T", "course_name": "C", "visibility": "STUDENT_VISIBLE", "created_at": "2026-01-01", "distance": 0.1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Focus on SQL."

        result = answer_academic_question(self.user, "What are my weaknesses?")

        mock_build_attendance_ctx.assert_not_called()
        mock_retrieve.assert_called_once()
        self.assertEqual(result["answer"], "Focus on SQL.")
        self.assertEqual(result["sources"], [{"type": "remark", "remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}])

    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_combined_question_calls_both_domains_and_combines_sources(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
    ):
        mock_retrieve.return_value = [{"remark_id": 1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "attendance", "course_name": "Maths", "detail": "90%"}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Combined answer."

        result = answer_academic_question(self.user, "How is my attendance and what should I improve?")

        mock_retrieve.assert_called_once()
        mock_build_attendance_ctx.assert_called_once()
        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"remark", "attendance"})

        # The combined context handed to Gemini must contain both items.
        sent_context = mock_gen_cls.return_value.generate_answer.call_args[0][1]
        self.assertEqual(len(sent_context["items"]), 2)

    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_unmatched_question_calls_nothing_and_no_gemini(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
    ):
        result = answer_academic_question(self.user, "What is the meaning of life?")

        mock_retrieve.assert_not_called()
        mock_build_remark_ctx.assert_not_called()
        mock_build_attendance_ctx.assert_not_called()
        mock_gen_cls.assert_not_called()
        self.assertEqual(result, {"answer": NO_RELEVANT_DOMAIN_MESSAGE, "sources": []})

    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_remarks_domain_with_zero_results_returns_not_enough_info_without_calling_gemini(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
    ):
        mock_retrieve.return_value = []
        mock_build_remark_ctx.return_value = {"items": [], "sources": [], "truncated": False}

        result = answer_academic_question(self.user, "What are my weaknesses?")

        mock_gen_cls.assert_not_called()
        self.assertEqual(result, {"answer": NOT_ENOUGH_INFORMATION_MESSAGE, "sources": []})

    # ── Phase 10C: assignments ──────────────────────────────────────────

    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_assignment_only_question_never_calls_remarks_or_attendance(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx, mock_build_assignment_ctx,
    ):
        mock_build_assignment_ctx.return_value = {
            "prompt_item": {"teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "assignment", "title": "SQL Homework", "course_name": "Databases", "due_at": "2026-09-20T00:00:00Z", "status": "pending", "attachment_available": False}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "You have 1 pending assignment."

        result = answer_academic_question(self.user, "What assignments do I have?")

        mock_retrieve.assert_not_called()
        mock_build_remark_ctx.assert_not_called()
        mock_build_attendance_ctx.assert_not_called()
        mock_build_assignment_ctx.assert_called_once_with(self.user, course_offering_id=None)
        self.assertEqual(result["answer"], "You have 1 pending assignment.")
        self.assertEqual(
            result["sources"],
            [{"type": "assignment", "title": "SQL Homework", "course_name": "Databases", "due_at": "2026-09-20T00:00:00Z", "status": "pending", "attachment_available": False}],
        )

    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_attendance_only_question_never_calls_assignment_context(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx, mock_build_assignment_ctx,
    ):
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "..."

        answer_academic_question(self.user, "How is my attendance?")

        mock_build_assignment_ctx.assert_not_called()

    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_all_three_domains_combine_when_routed(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx, mock_build_assignment_ctx,
    ):
        mock_retrieve.return_value = [{"remark_id": 1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "attendance", "course_name": "Maths", "detail": "90%"}],
        }
        mock_build_assignment_ctx.return_value = {
            "prompt_item": {"teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "assignment", "title": "SQL Homework", "course_name": "Databases", "due_at": "2026-09-20T00:00:00Z", "status": "pending", "attachment_available": False}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Full summary."

        result = answer_academic_question(
            self.user, "How is my attendance, what assignments do I have, and what should I improve?",
        )

        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"remark", "attendance", "assignment"})
        sent_context = mock_gen_cls.return_value.generate_answer.call_args[0][1]
        self.assertEqual(len(sent_context["items"]), 3)

    # ── Phase 10D: courses ───────────────────────────────────────────────

    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_course_only_question_calls_no_other_domain(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx,
    ):
        mock_build_course_ctx.return_value = {
            "prompt_item": {"teacher_name": "Courses Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "course", "course_name": "Database Systems", "course_code": "CS301", "teacher_name": "Muhammad Owais", "section_name": "A"}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "You are taking Database Systems."

        result = answer_academic_question(self.user, "Who teaches me?")

        mock_retrieve.assert_not_called()
        mock_build_remark_ctx.assert_not_called()
        mock_build_attendance_ctx.assert_not_called()
        mock_build_assignment_ctx.assert_not_called()
        mock_build_course_ctx.assert_called_once_with(self.user, course_offering_id=None)
        self.assertEqual(result["answer"], "You are taking Database Systems.")
        self.assertEqual(
            result["sources"],
            [{"type": "course", "course_name": "Database Systems", "course_code": "CS301", "teacher_name": "Muhammad Owais", "section_name": "A"}],
        )

    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_teacher_feedback_question_never_calls_course_context(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx,
    ):
        mock_retrieve.return_value = [{"remark_id": 1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Focus on SQL."

        # Critical false-positive-avoidance case (bare "teacher" is not a
        # course keyword) verified at the orchestration level too.
        answer_academic_question(self.user, "What did my teacher say about my performance?")

        mock_build_course_ctx.assert_not_called()

    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_all_four_domains_combine_when_routed(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx,
    ):
        mock_retrieve.return_value = [{"remark_id": 1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "attendance", "course_name": "Maths", "detail": "90%"}],
        }
        mock_build_assignment_ctx.return_value = {
            "prompt_item": {"teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "assignment", "title": "SQL Homework", "course_name": "Databases", "due_at": "2026-09-20T00:00:00Z", "status": "pending", "attachment_available": False}],
        }
        mock_build_course_ctx.return_value = {
            "prompt_item": {"teacher_name": "Courses Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "course", "course_name": "Databases", "course_code": "CS101", "teacher_name": "T", "section_name": "A"}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Full summary."

        result = answer_academic_question(
            self.user,
            "Who teaches me, how is my attendance, what assignments do I have, and what should I improve?",
        )

        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"remark", "attendance", "assignment", "course"})
        sent_context = mock_gen_cls.return_value.generate_answer.call_args[0][1]
        self.assertEqual(len(sent_context["items"]), 4)

    # ── Phase 10E: overall trigger ───────────────────────────────────────

    def _mock_all_four(self, mock_retrieve, mock_build_remark_ctx, mock_build_attendance_ctx,
                        mock_build_assignment_ctx, mock_build_course_ctx, mock_gen_cls):
        mock_retrieve.return_value = [{"remark_id": 1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "attendance", "course_name": "Maths", "detail": "90%"}],
        }
        mock_build_assignment_ctx.return_value = {
            "prompt_item": {"teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "assignment", "title": "SQL Homework", "course_name": "Databases", "due_at": "2026-09-20T00:00:00Z", "status": "pending", "attachment_available": False}],
        }
        mock_build_course_ctx.return_value = {
            "prompt_item": {"teacher_name": "Courses Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "course", "course_name": "Databases", "course_code": "CS101", "teacher_name": "T", "section_name": "A"}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Overall summary."

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_overall_question_activates_all_four_domains(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {"status": "none"}
        self._mock_all_four(
            mock_retrieve, mock_build_remark_ctx, mock_build_attendance_ctx,
            mock_build_assignment_ctx, mock_build_course_ctx, mock_gen_cls,
        )

        result = answer_academic_question(self.user, "Give me an overall academic summary.")

        mock_retrieve.assert_called_once()
        mock_build_attendance_ctx.assert_called_once()
        mock_build_assignment_ctx.assert_called_once()
        mock_build_course_ctx.assert_called_once()
        types = {s["type"] for s in result["sources"]}
        self.assertEqual(types, {"remark", "attendance", "assignment", "course"})

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_how_am_i_doing_overall_also_triggers_all_four(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {"status": "none"}
        self._mock_all_four(
            mock_retrieve, mock_build_remark_ctx, mock_build_attendance_ctx,
            mock_build_assignment_ctx, mock_build_course_ctx, mock_gen_cls,
        )

        answer_academic_question(self.user, "How am I doing overall?")

        mock_build_course_ctx.assert_called_once()

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_single_domain_question_unaffected_by_overall_logic(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {"status": "none"}
        mock_build_attendance_ctx.return_value = {
            "prompt_item": {"teacher_name": "Attendance Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "attendance", "course_name": "Maths", "detail": "90%"}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "90%."

        answer_academic_question(self.user, "How is my attendance?")

        mock_build_course_ctx.assert_not_called()
        mock_build_assignment_ctx.assert_not_called()
        mock_retrieve.assert_not_called()

    # ── Phase 10E: course-specific narrowing ────────────────────────────

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_resolved_course_with_no_domain_keyword_activates_all_four_scoped(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {
            "status": "matched", "course_offering_id": 42, "course_name": "Database Systems",
        }
        self._mock_all_four(
            mock_retrieve, mock_build_remark_ctx, mock_build_attendance_ctx,
            mock_build_assignment_ctx, mock_build_course_ctx, mock_gen_cls,
        )

        answer_academic_question(self.user, "How am I doing in Database Systems?")

        mock_retrieve.assert_called_once()
        _, retrieve_kwargs = mock_retrieve.call_args
        self.assertEqual(retrieve_kwargs["course_offering_id"], 42)
        mock_build_attendance_ctx.assert_called_once_with(self.user, course_offering_id=42)
        mock_build_assignment_ctx.assert_called_once_with(self.user, course_offering_id=42)
        mock_build_course_ctx.assert_called_once_with(self.user, course_offering_id=42)

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_resolved_course_with_existing_domain_keyword_only_scopes_that_domain(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {
            "status": "matched", "course_offering_id": 42, "course_name": "Maths",
        }
        mock_build_assignment_ctx.return_value = {
            "prompt_item": {"teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "", "text": "..."},
            "sources": [{"type": "assignment", "title": "HW", "course_name": "Maths", "due_at": "2026-09-20T00:00:00Z", "status": "pending", "attachment_available": False}],
        }
        mock_gen_cls.return_value.generate_answer.return_value = "1 pending."

        answer_academic_question(self.user, "What assignments do I have for Maths?")

        # assignments keyword already routed - stays assignments-only, but
        # still narrowed by the resolved course.
        mock_build_attendance_ctx.assert_not_called()
        mock_build_course_ctx.assert_not_called()
        mock_retrieve.assert_not_called()
        mock_build_assignment_ctx.assert_called_once_with(self.user, course_offering_id=42)

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_ambiguous_course_short_circuits_with_no_retrieval_and_no_gemini(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {"status": "ambiguous", "candidates": ["Maths", "Advanced Maths"]}

        result = answer_academic_question(self.user, "How am I doing in Maths?")

        mock_retrieve.assert_not_called()
        mock_build_attendance_ctx.assert_not_called()
        mock_build_assignment_ctx.assert_not_called()
        mock_build_course_ctx.assert_not_called()
        mock_gen_cls.assert_not_called()
        self.assertEqual(result["sources"], [])
        self.assertIn("Maths", result["answer"])
        self.assertIn("Advanced Maths", result["answer"])

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_unmatched_course_mention_with_no_other_signal_returns_not_found_message(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        mock_resolve_course.return_value = {"status": "none_but_mentioned", "phrase": "Physics"}

        result = answer_academic_question(self.user, "How am I doing in Physics?")

        mock_retrieve.assert_not_called()
        mock_build_attendance_ctx.assert_not_called()
        mock_build_assignment_ctx.assert_not_called()
        mock_build_course_ctx.assert_not_called()
        mock_gen_cls.assert_not_called()
        self.assertEqual(result["sources"], [])
        self.assertIn("Physics", result["answer"])

    @patch("ai_assistant.orchestrator.resolve_mentioned_course")
    @patch("ai_assistant.orchestrator.build_course_context")
    @patch("ai_assistant.orchestrator.build_assignment_context")
    @patch("ai_assistant.orchestrator.build_attendance_context")
    @patch("ai_assistant.orchestrator.GeminiGenerationService")
    @patch("ai_assistant.orchestrator.build_remark_context")
    @patch("ai_assistant.orchestrator.get_semantically_relevant_remarks")
    def test_unmatched_course_mention_alongside_a_routed_domain_does_not_hijack_the_answer(
        self, mock_retrieve, mock_build_remark_ctx, mock_gen_cls, mock_build_attendance_ctx,
        mock_build_assignment_ctx, mock_build_course_ctx, mock_resolve_course,
    ):
        # A harmless mis-extracted trailing phrase (e.g. "...in general?")
        # must not hijack a question that already routed a real domain.
        mock_resolve_course.return_value = {"status": "none_but_mentioned", "phrase": "general"}
        mock_retrieve.return_value = [{"remark_id": 1}]
        mock_build_remark_ctx.return_value = {
            "items": [{"teacher_name": "T", "course_name": "C", "created_at": "2026-01-01", "text": "Struggling."}],
            "sources": [{"remark_id": 1, "teacher_name": "T", "course_name": "C", "created_at": "2026-01-01"}],
            "truncated": False,
        }
        mock_gen_cls.return_value.generate_answer.return_value = "Focus on SQL."

        result = answer_academic_question(self.user, "What are my weaknesses in general?")

        mock_gen_cls.return_value.generate_answer.assert_called_once()
        self.assertEqual(result["answer"], "Focus on SQL.")
