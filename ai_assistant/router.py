"""
Deterministic question routing. Not an authorization layer - it only decides
which context-builder functions the orchestrator should call; each of those
still independently enforces its own authorization.

Matching requires a word boundary immediately before each keyword (not plain
substring), since plain `keyword in question` previously misrouted
"calculate"/"translate" and "permission" into the attendance domain.
"""
import re

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

# Deliberately not "teacher" alone - that word appears constantly in
# remarks-flavored questions and would misroute those away from remarks.
_COURSE_KEYWORDS = (
    "course", "courses", "enrolled", "enrollment", "subject", "instructor",
    "teaches me", "who teaches", "section",
)


def _matches(normalized: str, keyword: str) -> bool:
    return re.search(r"\b" + re.escape(keyword), normalized) is not None


def route(question: str) -> dict:
    """
    Returns {"remarks": bool, "attendance": bool, "assignments": bool,
    "courses": bool}. Any combination can be True.
    """
    normalized = question.lower()
    return {
        "remarks": any(_matches(normalized, k) for k in _REMARKS_KEYWORDS),
        "attendance": any(_matches(normalized, k) for k in _ATTENDANCE_KEYWORDS),
        "assignments": any(_matches(normalized, k) for k in _ASSIGNMENT_KEYWORDS),
        "courses": any(_matches(normalized, k) for k in _COURSE_KEYWORDS),
    }
