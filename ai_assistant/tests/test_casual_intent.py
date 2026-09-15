"""
Tests for ai_assistant.casual_intent - the deterministic casual-message
layer checked before the academic router. No Gemini/LLM involved: these
are pure string-matching tests.
"""
from django.test import SimpleTestCase

from ai_assistant.casual_intent import (
    GOODBYE,
    GREETING,
    THANKS,
    WELLBEING,
    build_casual_response,
    classify_casual_intent,
)


class _FakeUser:
    def __init__(self, name=""):
        self.name = name


class ClassifyCasualIntentTests(SimpleTestCase):

    # ── Greetings ────────────────────────────────────────────────────
    def test_hello(self):
        self.assertEqual(classify_casual_intent("hello"), GREETING)

    def test_hi(self):
        self.assertEqual(classify_casual_intent("hi"), GREETING)

    def test_hey(self):
        self.assertEqual(classify_casual_intent("hey"), GREETING)

    def test_good_morning(self):
        self.assertEqual(classify_casual_intent("good morning"), GREETING)

    def test_good_afternoon(self):
        self.assertEqual(classify_casual_intent("good afternoon"), GREETING)

    def test_good_evening(self):
        self.assertEqual(classify_casual_intent("good evening"), GREETING)

    def test_greeting_is_case_insensitive_and_tolerates_punctuation(self):
        self.assertEqual(classify_casual_intent("Hi!"), GREETING)
        self.assertEqual(classify_casual_intent("  HELLO  "), GREETING)

    # ── Well-being ───────────────────────────────────────────────────
    def test_how_are_you(self):
        self.assertEqual(classify_casual_intent("how are you"), WELLBEING)
        self.assertEqual(classify_casual_intent("how are you?"), WELLBEING)

    def test_how_are_u(self):
        self.assertEqual(classify_casual_intent("how are u"), WELLBEING)

    def test_hey_how_are_you(self):
        self.assertEqual(classify_casual_intent("hey how are you?"), WELLBEING)

    def test_hey_how_are_u(self):
        self.assertEqual(classify_casual_intent("hey how are u"), WELLBEING)

    # ── Thanks ───────────────────────────────────────────────────────
    def test_thanks(self):
        self.assertEqual(classify_casual_intent("thanks"), THANKS)

    def test_thank_you(self):
        self.assertEqual(classify_casual_intent("thank you"), THANKS)

    def test_thanks_a_lot(self):
        self.assertEqual(classify_casual_intent("thanks a lot"), THANKS)

    def test_thank_you_so_much(self):
        self.assertEqual(classify_casual_intent("thank you so much"), THANKS)

    # ── Goodbye ──────────────────────────────────────────────────────
    def test_bye(self):
        self.assertEqual(classify_casual_intent("bye"), GOODBYE)

    def test_goodbye(self):
        self.assertEqual(classify_casual_intent("goodbye"), GOODBYE)

    def test_see_you(self):
        self.assertEqual(classify_casual_intent("see you"), GOODBYE)

    def test_see_you_later(self):
        self.assertEqual(classify_casual_intent("see you later"), GOODBYE)

    # ── Not casual: empty / unrelated ───────────────────────────────
    def test_empty_string_is_not_casual(self):
        self.assertIsNone(classify_casual_intent(""))
        self.assertIsNone(classify_casual_intent("   "))

    def test_unrelated_academic_question_is_not_casual(self):
        self.assertIsNone(classify_casual_intent("What is my GPA?"))

    # ── Ambiguous cases: casual word + academic content must NOT classify as casual ──
    def test_hi_plus_attendance_question_is_not_casual(self):
        self.assertIsNone(classify_casual_intent("hi, how is my attendance?"))

    def test_hey_plus_assignments_question_is_not_casual(self):
        self.assertIsNone(classify_casual_intent("hey, what assignments do I have?"))

    def test_hello_plus_courses_question_is_not_casual(self):
        self.assertIsNone(classify_casual_intent("hello, who teaches me?"))


class BuildCasualResponseTests(SimpleTestCase):

    def test_greeting_includes_first_name(self):
        response = build_casual_response(GREETING, _FakeUser(name="Mahad Baloch"))
        self.assertEqual(
            response,
            "Hi Mahad! \U0001F44B How can I help you with your courses, attendance, assignments, or teacher feedback?",
        )

    def test_greeting_without_name_still_works(self):
        response = build_casual_response(GREETING, _FakeUser(name=""))
        self.assertEqual(
            response,
            "Hi! \U0001F44B How can I help you with your courses, attendance, assignments, or teacher feedback?",
        )

    def test_wellbeing_response_is_fixed(self):
        response = build_casual_response(WELLBEING, _FakeUser(name="Mahad Baloch"))
        self.assertEqual(
            response,
            "I'm doing well! \U0001F44B What would you like to know about your academic progress?",
        )

    def test_thanks_response_is_fixed(self):
        response = build_casual_response(THANKS, _FakeUser(name="Mahad Baloch"))
        self.assertEqual(response, "You're welcome! Let me know if you need anything else.")

    def test_goodbye_includes_first_name(self):
        response = build_casual_response(GOODBYE, _FakeUser(name="Mahad Baloch"))
        self.assertEqual(response, "See you later, Mahad! \U0001F44B")

    def test_goodbye_without_name_still_works(self):
        response = build_casual_response(GOODBYE, _FakeUser(name=""))
        self.assertEqual(response, "See you later! \U0001F44B")

    def test_only_first_name_is_used_not_full_name(self):
        response = build_casual_response(GREETING, _FakeUser(name="Mahad Baloch Extra"))
        self.assertIn("Hi Mahad!", response)
        self.assertNotIn("Baloch", response)

    def test_user_without_name_attribute_does_not_crash(self):
        class _NoNameUser:
            pass

        response = build_casual_response(GREETING, _NoNameUser())
        self.assertTrue(response.startswith("Hi!"))
