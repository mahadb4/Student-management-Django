"""
Phase 10E: deterministic, authorization-scoped course-name resolution.

Resolves a question like "How am I doing in Database Systems?" to one of
the AUTHENTICATED STUDENT'S OWN authorized, ACTIVE course offerings -
never a global course lookup. The search space is always
ai_assistant.context.course_context.get_active_enrollments_for_user's own
authorized list (Phase 10D's function, unchanged), so a resolved course
can never be one the student isn't already allowed to see.

Matching is deliberately simple and deterministic - no fuzzy matching, no
embeddings, no LLM entity extraction (explicitly out of scope for this
phase). Priority:
    1. exact normalized course CODE match (whole-word/phrase, not a
       partial-word substring - "CS3" would not match "CS301")
    2. exact normalized course NAME match, same whole-phrase rule
    3. no match

If more than one of the student's own authorized courses matches at
whichever stage succeeds, resolution is "ambiguous" - the caller must ask
the student to clarify rather than guessing.
"""
import re

from ai_assistant.context.course_context import get_active_enrollments_for_user

# Pure regex phrase extraction - used only to decide whether to surface an
# explicit "no matching course" message versus staying silent (falling
# through to ordinary keyword routing). It does NOT itself decide what
# course was meant, only whether the question looks like it named one via
# a trailing "in ..."/"for ..." phrase - not fuzzy/approximate matching.
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
