"""
Phase 10B/10C/10D: deterministic question routing.

This is NOT an authorization layer. It only decides which context-builder
functions the orchestrator should call - each of those still independently
enforces its own existing authorization (get_remarks_queryset_for_user /
apply_data_scope / get_assignments_queryset_for_user). A routing mistake
can, at worst, pick the wrong authorized domain or none at all - it can
never widen what a domain returns, because the domains themselves don't
trust the router for that.

Deterministic keyword matching, not an LLM call - per Phase 10's explicit
instruction to prefer predictable behavior for obvious questions and avoid
spending an extra Gemini call just to classify intent.
"""

_ATTENDANCE_KEYWORDS = (
    "attendance", "present", "absent", "absence", "late", "missed", "miss",
)

_REMARKS_KEYWORDS = (
    "weakness", "weaknesses", "strength", "strengths", "improve", "improvement",
    "feedback", "performance", "teacher said", "teachers say", "teachers said",
    "remark", "remarks",
)

_ASSIGNMENT_KEYWORDS = (
    "assignment", "assignments", "homework", "due", "submit", "submission", "submitted",
)

# Deliberately NOT "teacher" alone - that word appears constantly in
# remarks-flavored questions ("what did my teacher say"), and including it
# here would misroute those away from remarks. "who teaches"/"teaches me"
# are specific enough to mean "which course/instructor", not "what did my
# teacher say about me".
_COURSE_KEYWORDS = (
    "course", "courses", "enrolled", "enrollment", "subject", "instructor",
    "teaches me", "who teaches", "section",
)


def route(question: str) -> dict:
    """
    Returns {"remarks": bool, "attendance": bool, "assignments": bool,
    "courses": bool}. Any combination can be True - a question matching no
    keyword in any list routes to none of them, which the orchestrator
    treats as "ask a clarifying question, retrieve nothing, call no LLM."
    """
    normalized = question.lower()
    return {
        "remarks": any(keyword in normalized for keyword in _REMARKS_KEYWORDS),
        "attendance": any(keyword in normalized for keyword in _ATTENDANCE_KEYWORDS),
        "assignments": any(keyword in normalized for keyword in _ASSIGNMENT_KEYWORDS),
        "courses": any(keyword in normalized for keyword in _COURSE_KEYWORDS),
    }
