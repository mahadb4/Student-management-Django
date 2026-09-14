"""
Phase 10B/10C tests: the deterministic question router.

Pure function, no DB, no network - SimpleTestCase proves that structurally.
"""
from django.test import SimpleTestCase

from ai_assistant.router import route


class RouterTests(SimpleTestCase):

    def test_attendance_question_routes_to_attendance_only(self):
        self.assertEqual(
            route("How is my attendance?"), {"remarks": False, "attendance": True, "assignments": False, "courses": False},
        )

    def test_missed_classes_question_routes_to_attendance_only(self):
        self.assertEqual(
            route("How many classes have I missed?"), {"remarks": False, "attendance": True, "assignments": False, "courses": False},
        )

    def test_remarks_question_routes_to_remarks_only(self):
        self.assertEqual(
            route("What are my weaknesses according to my teachers?"),
            {"remarks": True, "attendance": False, "assignments": False, "courses": False},
        )

    def test_improvement_question_routes_to_remarks_only(self):
        self.assertEqual(
            route("What should I improve?"), {"remarks": True, "attendance": False, "assignments": False, "courses": False},
        )

    def test_combined_question_routes_to_both_remarks_and_attendance(self):
        self.assertEqual(
            route("How is my attendance and what should I improve?"),
            {"remarks": True, "attendance": True, "assignments": False, "courses": False},
        )

    def test_unmatched_question_routes_to_none(self):
        self.assertEqual(
            route("What is the meaning of life?"), {"remarks": False, "attendance": False, "assignments": False, "courses": False},
        )

    def test_matching_is_case_insensitive(self):
        self.assertEqual(
            route("HOW IS MY ATTENDANCE?"), {"remarks": False, "attendance": True, "assignments": False, "courses": False},
        )

    def test_class_alone_does_not_trigger_attendance(self):
        # "class" is deliberately NOT an attendance keyword - a teacher
        # asking about "my class" (their students in general) must not be
        # misrouted away from remarks just because "class" appears.
        self.assertEqual(
            route("What feedback have I given my class?"),
            {"remarks": True, "attendance": False, "assignments": False, "courses": False},
        )

    # ── Phase 10C: assignments ──────────────────────────────────────────

    def test_assignment_question_routes_to_assignments_only(self):
        self.assertEqual(
            route("What assignments do I have?"), {"remarks": False, "attendance": False, "assignments": True, "courses": False},
        )

    def test_pending_assignments_question_routes_to_assignments_only(self):
        self.assertEqual(
            route("Do I have any pending assignments?"),
            {"remarks": False, "attendance": False, "assignments": True, "courses": False},
        )

    def test_due_soon_question_routes_to_assignments_only(self):
        self.assertEqual(
            route("What is due soon?"), {"remarks": False, "attendance": False, "assignments": True, "courses": False},
        )

    def test_homework_question_routes_to_assignments_only(self):
        self.assertEqual(
            route("Has my teacher posted any homework?"),
            {"remarks": False, "attendance": False, "assignments": True, "courses": False},
        )

    def test_attendance_and_assignments_combined(self):
        self.assertEqual(
            route("How is my attendance and what assignments do I have?"),
            {"remarks": False, "attendance": True, "assignments": True, "courses": False},
        )

    def test_all_three_domains_combined(self):
        self.assertEqual(
            route("How is my attendance, what assignments do I have, and what should I improve?"),
            {"remarks": True, "attendance": True, "assignments": True, "courses": False},
        )

    def test_assignment_keyword_does_not_trigger_remarks_or_attendance(self):
        self.assertEqual(
            route("What assignments do I have?"), {"remarks": False, "attendance": False, "assignments": True, "courses": False},
        )

    # ── Phase 10D: courses ───────────────────────────────────────────────

    def test_who_teaches_me_routes_to_courses_only(self):
        self.assertEqual(
            route("Who teaches me?"), {"remarks": False, "attendance": False, "assignments": False, "courses": True},
        )

    def test_what_courses_question_routes_to_courses_only(self):
        self.assertEqual(
            route("What courses am I taking?"),
            {"remarks": False, "attendance": False, "assignments": False, "courses": True},
        )

    def test_who_teaches_named_course_routes_to_courses_only(self):
        self.assertEqual(
            route("Who teaches Database Systems?"),
            {"remarks": False, "attendance": False, "assignments": False, "courses": True},
        )

    def test_enrolled_question_routes_to_courses_only(self):
        self.assertEqual(
            route("Which courses am I enrolled in?"),
            {"remarks": False, "attendance": False, "assignments": False, "courses": True},
        )

    def test_teacher_feedback_question_does_not_trigger_courses(self):
        # The critical false-positive-avoidance case: bare "teacher" must
        # NOT be a course keyword, or this remarks-only question would be
        # wrongly routed toward courses too.
        self.assertEqual(
            route("What did my teacher say about my performance?"),
            {"remarks": True, "attendance": False, "assignments": False, "courses": False},
        )

    def test_courses_and_remarks_combined(self):
        self.assertEqual(
            route("Who teaches me and what are my weaknesses?"),
            {"remarks": True, "attendance": False, "assignments": False, "courses": True},
        )

    def test_courses_and_attendance_combined(self):
        self.assertEqual(
            route("What courses am I taking and how is my attendance?"),
            {"remarks": False, "attendance": True, "assignments": False, "courses": True},
        )
