"""
Tests for ai_assistant.intent_classifier.classify_intent - a pure
function, no DB, no network.

Covers the domain-vs-intent distinction this layer exists for: a router
domain match alone is not enough to determine intent (e.g. "courses"
matches both course_list and course_recommendation questions).
"""
from django.test import SimpleTestCase

from ai_assistant.intent_classifier import Intent, RetrievalStrategy, classify_intent


class IntentClassifierTests(SimpleTestCase):

    def test_which_subjects_am_i_having_is_course_list(self):
        result = classify_intent("Which subjects am I having?")
        self.assertEqual(result.intent, Intent.COURSE_LIST)
        self.assertEqual(result.domains, frozenset({"courses"}))
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.STRUCTURED)

    def test_what_courses_am_i_currently_enrolled_in_is_course_list(self):
        result = classify_intent("What courses am I currently enrolled in?")
        self.assertEqual(result.intent, Intent.COURSE_LIST)
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.STRUCTURED)

    def test_what_did_my_teacher_say_about_performance_is_teacher_feedback(self):
        result = classify_intent("What did my teacher say about my performance?")
        self.assertEqual(result.intent, Intent.TEACHER_FEEDBACK)
        self.assertEqual(result.domains, frozenset({"remarks"}))
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.SEMANTIC)

    def test_what_should_i_improve_according_to_teachers_is_teacher_feedback(self):
        result = classify_intent("What should I improve according to my teachers?")
        self.assertEqual(result.intent, Intent.TEACHER_FEEDBACK)
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.SEMANTIC)

    def test_what_is_my_attendance_is_attendance(self):
        result = classify_intent("What is my attendance?")
        self.assertEqual(result.intent, Intent.ATTENDANCE)
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.STRUCTURED)

    def test_which_assignments_are_pending_is_assignment_status(self):
        result = classify_intent("Which assignments are pending?")
        self.assertEqual(result.intent, Intent.ASSIGNMENT_STATUS)
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.STRUCTURED)

    def test_attendance_plus_feedback_is_academic_improvement_hybrid(self):
        result = classify_intent("What should I improve based on my attendance and teacher feedback?")
        self.assertEqual(result.intent, Intent.ACADEMIC_IMPROVEMENT)
        self.assertEqual(result.domains, frozenset({"attendance", "remarks"}))
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.HYBRID)

    def test_future_course_recommendation_is_unsupported_not_course_list(self):
        # The core distinction this module exists for: same "courses"
        # keyword as course_list, but a different intent and no retrieval.
        result = classify_intent("What courses will you recommend me in future?")
        self.assertEqual(result.intent, Intent.COURSE_RECOMMENDATION)
        self.assertEqual(result.domains, frozenset())
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.UNSUPPORTED)

    def test_weather_question_is_unsupported(self):
        result = classify_intent("Tell me the weather tomorrow.")
        self.assertEqual(result.intent, Intent.UNSUPPORTED)
        self.assertEqual(result.domains, frozenset())
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.UNSUPPORTED)

    def test_no_relevant_remarks_case_is_still_classified_as_teacher_feedback(self):
        # Classification doesn't know retrieval will come back empty -
        # that's the retriever's job (threshold), not the classifier's.
        result = classify_intent("What feedback did my teacher give about quantum computing?")
        self.assertEqual(result.intent, Intent.TEACHER_FEEDBACK)
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.SEMANTIC)

    def test_course_list_and_course_recommendation_share_a_domain_but_differ_in_intent(self):
        list_result = classify_intent("What courses am I taking?")
        rec_result = classify_intent("What courses should I take next semester?")
        self.assertNotEqual(list_result.intent, rec_result.intent)
        self.assertEqual(rec_result.retrieval_strategy, RetrievalStrategy.UNSUPPORTED)
        self.assertEqual(list_result.retrieval_strategy, RetrievalStrategy.STRUCTURED)

    def test_recommendation_trigger_without_course_domain_does_not_force_recommendation_intent(self):
        result = classify_intent("What is my attendance?")
        self.assertNotEqual(result.intent, Intent.COURSE_RECOMMENDATION)

    def test_overall_flag_forces_general_academic_question_hybrid(self):
        result = classify_intent("How am I doing overall?", is_overall=True)
        self.assertEqual(result.intent, Intent.GENERAL_ACADEMIC_QUESTION)
        self.assertEqual(result.domains, frozenset({"remarks", "attendance", "assignments", "courses"}))
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.HYBRID)

    def test_three_domains_without_overall_flag_is_general_academic_question(self):
        result = classify_intent("How is my attendance, what assignments do I have, and what should I improve?")
        self.assertEqual(result.intent, Intent.GENERAL_ACADEMIC_QUESTION)
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.HYBRID)

    def test_unmatched_question_is_unsupported_with_no_domains(self):
        result = classify_intent("What is the meaning of life?")
        self.assertEqual(result.intent, Intent.UNSUPPORTED)
        self.assertEqual(result.domains, frozenset())
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.UNSUPPORTED)

    def test_single_sql_domain_is_structured(self):
        self.assertEqual(classify_intent("Who teaches me?").retrieval_strategy, RetrievalStrategy.STRUCTURED)

    def test_single_semantic_domain_is_semantic(self):
        self.assertEqual(
            classify_intent("What are my weaknesses?").retrieval_strategy, RetrievalStrategy.SEMANTIC,
        )

    def test_remarks_plus_courses_is_hybrid(self):
        result = classify_intent("Who teaches me and what are my weaknesses?")
        self.assertEqual(result.retrieval_strategy, RetrievalStrategy.HYBRID)
