"""
Deterministic, authorization-scoped course-name resolution. Resolves a question
to one of the authenticated student's own authorized, active course offerings,
using get_active_enrollments_for_user as the search space so a resolved course
can never be one the student isn't already allowed to see.
"""
import re

from ai_assistant.context.course_context import get_active_enrollments_for_user

# Used only to decide whether to surface a "no matching course" message vs
# falling through to keyword routing; does not itself decide which course was meant.
_TRAILING_COURSE_PHRASE = re.compile(r"\b(?:in|for)\s+([A-Za-z0-9][A-Za-z0-9 ]*?)\s*[?.!]*$")


def _normalize(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def _contains_whole_phrase(normalized_question, normalized_phrase):
    if not normalized_phrase:
        return False
    return re.search(r"\b" + re.escape(normalized_phrase) + r"\b", normalized_question) is not None


def _extract_candidate_phrase(question):
    match = _TRAILING_COURSE_PHRASE.search(question.strip())
    if not match:
        return None
    phrase = match.group(1).strip()
    return phrase or None


def _resolve_from_matches(matches):
    distinct_offerings = {e.course_offering_id: e for e in matches}
    if len(distinct_offerings) == 1:
        enrollment = next(iter(distinct_offerings.values()))
        return {
            "status": "matched",
            "course_offering_id": enrollment.course_offering_id,
            "course_name": enrollment.course_offering.course.name,
        }
    return {
        "status": "ambiguous",
        "candidates": sorted({e.course_offering.course.name for e in distinct_offerings.values()}),
    }


def resolve_mentioned_course(user, question):
    """
    Returns one of:
        {"status": "matched", "course_offering_id": int, "course_name": str}
        {"status": "ambiguous", "candidates": [str, ...]}
        {"status": "none_but_mentioned", "phrase": str}
        {"status": "none"}
    """
    enrollments = list(get_active_enrollments_for_user(user))

    if not enrollments:
        phrase = _extract_candidate_phrase(question)
        return {"status": "none_but_mentioned", "phrase": phrase} if phrase else {"status": "none"}

    normalized_question = _normalize(question)

    code_matches = [
        e for e in enrollments
        if _contains_whole_phrase(normalized_question, _normalize(e.course_offering.course.code))
    ]
    if code_matches:
        return _resolve_from_matches(code_matches)

    name_matches = [
        e for e in enrollments
        if _contains_whole_phrase(normalized_question, _normalize(e.course_offering.course.name))
    ]
    if name_matches:
        return _resolve_from_matches(name_matches)

    phrase = _extract_candidate_phrase(question)
    return {"status": "none_but_mentioned", "phrase": phrase} if phrase else {"status": "none"}
