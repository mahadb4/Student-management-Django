"""
Deterministic casual-conversation layer, checked BEFORE the academic
domain router (ai_assistant.router.route) and BEFORE course resolution -
see the top of orchestrator.answer_academic_question. This is a pure UX
improvement: "hello"/"thanks"/"bye"-style messages get a fixed, friendly
reply without ever reaching Gemini or any of the authorized domain
context builders.

Deliberately NOT an LLM classification step (no extra Gemini call just to
detect small talk, matching this project's existing keyword-router
philosophy) - a normalized-text match against a small, fixed set of
patterns. A message is classified as casual only when, after stripping
punctuation, it matches one of these patterns IN FULL - "hi, how is my
attendance?" normalizes to "hi how is my attendance", which does not
fully match any casual pattern, so it correctly falls through to the
existing academic router untouched. This module has no knowledge of
attendance/assignments/courses/remarks keywords and never needs any -
the "must not swallow an academic question" guarantee comes entirely from
requiring a FULL match, not from cross-checking router keywords.
"""
import re

from common.utils import split_display_name

_PUNCTUATION_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")

_GREETING_PHRASES = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
_GOODBYE_PHRASES = {"bye", "goodbye", "good bye", "see you", "see you later"}

# Optional leading "hi"/"hey"/"hello" (e.g. "hey how are u") is part of the
# SAME casual message, not a separate greeting - classified once, as
# "wellbeing", so the response addresses the well-being question rather
# than only acknowledging the greeting.
_WELLBEING_RE = re.compile(r"^(?:(?:hi|hey|hello)\s+)?how\s+are\s+(?:you|u|ya)$")

# "thanks" / "thank you" / "thanks a lot" / "thank you so much" and close
# variants.
_THANKS_RE = re.compile(r"^thanks?(?:\s+you)?(?:\s+(?:a\s+lot|so\s+much|very\s+much))?$")

GREETING = "greeting"
WELLBEING = "wellbeing"
THANKS = "thanks"
GOODBYE = "goodbye"


def _normalize(text):
    lowered = (text or "").strip().lower()
    no_punctuation = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", no_punctuation).strip()


def classify_casual_intent(question):
    """
    Returns one of GREETING/WELLBEING/THANKS/GOODBYE if `question`, once
    normalized, is PURELY a casual message - or None if it isn't (which
    includes empty input and any question carrying additional/academic
    content alongside a greeting-like word).
    """
    normalized = _normalize(question)
    if not normalized:
        return None

    if _WELLBEING_RE.fullmatch(normalized):
        return WELLBEING
    if _THANKS_RE.fullmatch(normalized):
        return THANKS
    if normalized in _GOODBYE_PHRASES:
        return GOODBYE
    if normalized in _GREETING_PHRASES:
        return GREETING
    return None


def _student_first_name(user):
    # `user.name` is the same field every other view in this project reads
    # for display (see users/api/user_api.py, remark_api.py, etc.) - not a
    # new lookup, and safe for a user object that happens to lack it
    # (e.g. AnonymousUser in tests) since getattr just yields "".
    full_name = getattr(user, "name", "") or ""
    first_name, _ = split_display_name(full_name)
    return first_name


def build_casual_response(intent, user):
    """
    Returns the fixed, friendly reply for `intent` (one of this module's
    GREETING/WELLBEING/THANKS/GOODBYE constants). Uses the authenticated
    user's first name where the existing response text calls for one -
    never hardcoded, and gracefully omitted if the name is unavailable.
    """
    first_name = _student_first_name(user)

    if intent == GREETING:
        name_part = f" {first_name}" if first_name else ""
        return f"Hi{name_part}! \U0001F44B How can I help you with your courses, attendance, assignments, or teacher feedback?"

    if intent == WELLBEING:
        return "I'm doing well! \U0001F44B What would you like to know about your academic progress?"

    if intent == THANKS:
        return "You're welcome! Let me know if you need anything else."

    if intent == GOODBYE:
        name_part = f", {first_name}" if first_name else ""
        return f"See you later{name_part}! \U0001F44B"

    raise ValueError(f"Unknown casual intent: {intent!r}")
