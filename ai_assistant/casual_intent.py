"""
Deterministic casual-conversation layer, checked before the academic domain
router and course resolution. A message is classified as casual only when it
fully matches a fixed pattern after stripping punctuation, so an academic
question never gets swallowed by a partial match.
"""
import re

from common.utils import split_display_name

_PUNCTUATION_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")

_GREETING_PHRASES = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
_GOODBYE_PHRASES = {"bye", "goodbye", "good bye", "see you", "see you later"}

# A leading "hi"/"hey"/"hello" (e.g. "hey how are u") is classified as wellbeing,
# not a separate greeting, so the response addresses the well-being question.
_WELLBEING_RE = re.compile(r"^(?:(?:hi|hey|hello)\s+)?how\s+are\s+(?:you|u|ya)$")

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
    normalized, is purely a casual message, or None otherwise.
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
    full_name = getattr(user, "name", "") or ""
    first_name, _ = split_display_name(full_name)
    return first_name


def build_casual_response(intent, user):
    """
    Returns the fixed, friendly reply for `intent` (one of this module's
    GREETING/WELLBEING/THANKS/GOODBYE constants).
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
