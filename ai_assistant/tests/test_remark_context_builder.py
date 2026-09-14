"""
Phase 6 tests: deterministic context construction from Phase 5 retrieval
results.

This entire test file uses django.test.SimpleTestCase, not TestCase - that
is itself part of the proof for requirement #12 ("context builder performs
no authorization/database retrieval of its own"): SimpleTestCase forbids
any database access and raises an error if a test tries to use the ORM.
If build_remark_context ever queried the database, every test below would
fail immediately with "Database access not allowed", regardless of what it
asserts about the returned value.
"""
from django.test import SimpleTestCase

from ai_assistant.context.remark_context import build_remark_context

# Mirrors the exact shape returned by
# ai_assistant.retrieval.semantic_remarks.get_semantically_relevant_remarks
RESULT_A = {
    "remark_id": 1,
    "text": "Struggling with joins.",
    "teacher_name": "Teacher A",
    "course_name": "Databases",
    "visibility": "PRIVATE",
    "created_at": "2026-02-01T00:00:00+00:00",
    "distance": 0.12,
}
RESULT_B = {
    "remark_id": 2,
    "text": "Improved significantly.",
    "teacher_name": "Teacher A",
    "course_name": "Databases",
    "visibility": "STUDENT_VISIBLE",
    "created_at": "2026-03-01T00:00:00+00:00",
    "distance": 0.45,
}
RESULT_C = {
    "remark_id": 3,
    "text": "Excellent grasp of routing.",
    "teacher_name": "Teacher B",
    "course_name": "Networks",
    "visibility": "STUDENT_VISIBLE",
    "created_at": "2026-04-01T00:00:00+00:00",
    "distance": 0.80,
}


class RemarkContextBuilderTests(SimpleTestCase):

    # ── Field preservation ───────────────────────────────────────────────

    def test_converts_results_into_expected_item_format(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(context["items"], [{
            "teacher_name": "Teacher A",
            "course_name": "Databases",
            "created_at": "2026-02-01T00:00:00+00:00",
            "text": "Struggling with joins.",
        }])

    def test_teacher_name_preserved(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(context["items"][0]["teacher_name"], "Teacher A")

    def test_course_name_preserved(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(context["items"][0]["course_name"], "Databases")

    def test_remark_text_preserved(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(context["items"][0]["text"], "Struggling with joins.")

    def test_date_preserved(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(context["items"][0]["created_at"], "2026-02-01T00:00:00+00:00")

    # ── Ordering ─────────────────────────────────────────────────────────

    def test_ordering_from_retrieval_is_preserved_not_resorted(self):
        # C has the largest "distance" (least similar) but is passed first;
        # the builder must not re-rank - that's Phase 5's job, already done.
        context = build_remark_context([RESULT_C, RESULT_A, RESULT_B])
        self.assertEqual(
            [item["text"] for item in context["items"]],
            [RESULT_C["text"], RESULT_A["text"], RESULT_B["text"]],
        )

    # ── Empty input ──────────────────────────────────────────────────────

    def test_empty_retrieval_produces_empty_safe_context(self):
        context = build_remark_context([])
        self.assertEqual(context, {"items": [], "sources": [], "truncated": False})

    # ── Source references ───────────────────────────────────────────────

    def test_sources_preserve_correct_remark_ids(self):
        context = build_remark_context([RESULT_A, RESULT_B])
        self.assertEqual([s["remark_id"] for s in context["sources"]], [1, 2])

    def test_sources_contain_only_reference_fields(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(
            set(context["sources"][0].keys()), {"remark_id", "teacher_name", "course_name", "created_at"},
        )

    def test_sources_and_items_are_parallel_and_same_length(self):
        context = build_remark_context([RESULT_A, RESULT_B, RESULT_C])
        self.assertEqual(len(context["items"]), len(context["sources"]))

    # ── Sensitive/unnecessary fields are excluded ───────────────────────

    def test_embedding_and_distance_never_appear_in_items(self):
        context = build_remark_context([RESULT_A])
        for item in context["items"]:
            self.assertNotIn("distance", item)
            self.assertNotIn("embedding", item)

    def test_embedding_and_distance_never_appear_in_sources(self):
        context = build_remark_context([RESULT_A])
        for source in context["sources"]:
            self.assertNotIn("distance", source)
            self.assertNotIn("embedding", source)

    def test_internal_ids_and_visibility_not_included_in_items(self):
        # items are what the LLM sees - remark_id, visibility, and any
        # student/teacher/course internal IDs must not appear there.
        context = build_remark_context([RESULT_A])
        item = context["items"][0]
        self.assertNotIn("remark_id", item)
        self.assertNotIn("visibility", item)
        self.assertNotIn("student_id", item)
        self.assertNotIn("teacher_id", item)
        self.assertNotIn("course_id", item)

    def test_items_contain_exactly_the_expected_keys(self):
        context = build_remark_context([RESULT_A])
        self.assertEqual(set(context["items"][0].keys()), {"teacher_name", "course_name", "created_at", "text"})

    # ── Size limiting ────────────────────────────────────────────────────

    def test_max_items_limits_result_count(self):
        context = build_remark_context([RESULT_A, RESULT_B, RESULT_C], max_items=2)
        self.assertEqual(len(context["items"]), 2)
        self.assertTrue(context["truncated"])

    def test_not_truncated_when_all_results_fit(self):
        context = build_remark_context([RESULT_A, RESULT_B], max_items=10, max_total_characters=100000)
        self.assertFalse(context["truncated"])

    def test_character_budget_stops_before_exceeding_it(self):
        long_result = dict(RESULT_A, text="x" * 100)
        budget = len("x" * 100) + len("Teacher A") + len("Databases") + len("2026-02-01T00:00:00+00:00") + 10
        context = build_remark_context([long_result, RESULT_B], max_items=10, max_total_characters=budget)
        self.assertEqual(len(context["items"]), 1)
        self.assertTrue(context["truncated"])

    def test_character_budget_never_truncates_a_single_remarks_text(self):
        # Even a remark that alone exceeds the budget is included whole,
        # never cut mid-string - truncating feedback text could change its
        # meaning, so the builder drops whole items, never partial text.
        huge_result = dict(RESULT_A, text="y" * 50000)
        context = build_remark_context([huge_result], max_items=10, max_total_characters=10)
        self.assertEqual(len(context["items"]), 1)
        self.assertEqual(context["items"][0]["text"], "y" * 50000)

    # ── No authorization / no DB access (see module docstring: enforced ─
    # structurally by SimpleTestCase for every test in this file) ────────

    def test_builder_works_on_plain_dicts_with_no_database_involved(self):
        context = build_remark_context([RESULT_A, RESULT_B, RESULT_C])
        self.assertEqual(len(context["items"]), 3)
