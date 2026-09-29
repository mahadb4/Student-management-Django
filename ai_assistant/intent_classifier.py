"""
Intent classification layer between the keyword router (ai_assistant.router.route)
and the orchestrator's per-domain retrieval. Distinguishes DOMAIN (e.g. "mentions
courses") from INTENT (e.g. "wants a list" vs "wants a recommendation"), since both
can match the same domain keyword but only one has data behind it.
"""
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet

from ai_assistant.router import route


class Intent(str, Enum):
    COURSE_LIST = "course_list"
    ATTENDANCE = "attendance"
    ASSIGNMENT_STATUS = "assignment_status"
    TEACHER_FEEDBACK = "teacher_feedback"
    ACADEMIC_IMPROVEMENT = "academic_improvement"
    COURSE_RECOMMENDATION = "course_recommendation"
    GENERAL_ACADEMIC_QUESTION = "general_academic_question"
    FUTURE_PREDICTION = "future_prediction"
    UNSUPPORTED = "unsupported"


class RetrievalStrategy(str, Enum):
    STRUCTURED = "structured"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    domains: FrozenSet[str]
    retrieval_strategy: RetrievalStrategy


# This project has no course catalog/prerequisite/advising-roadmap data, so a
# recommendation question is structurally unsupported regardless of other domain matches.
_COURSE_RECOMMENDATION_TRIGGERS = (
    "recommend", "recommendation", "should i take", "should i enroll",
    "next semester", "future course", "suggest a course", "suggest courses",
    "course plan", "plan my courses", "roadmap",
    "which course should i take next", "what course should i take next",
)

# Questions asking the assistant to predict something that doesn't exist yet in
# the retrieved data (a future grade, future feedback, future attendance, etc.).
# Checked before domain retrieval so words like "feedback" or "attendance" don't
# trigger real retrieval just because they co-occur with a future/prediction ask.
_FUTURE_PREDICTION_TRIGGERS = (
    "will i", "will my", "will there", "will be", "will it",
    "would i", "would my",
    "predict", "prediction", "going forward", "in the future",
)

_SEMANTIC_DOMAINS = frozenset({"remarks"})

_SINGLE_DOMAIN_INTENT = {
    "courses": Intent.COURSE_LIST,
    "attendance": Intent.ATTENDANCE,
    "assignments": Intent.ASSIGNMENT_STATUS,
    "remarks": Intent.TEACHER_FEEDBACK,
}


def _strategy_for_domains(domains: FrozenSet[str]) -> RetrievalStrategy:
    if not domains:
        return RetrievalStrategy.UNSUPPORTED
    if domains <= _SEMANTIC_DOMAINS:
        return RetrievalStrategy.SEMANTIC
    if domains.isdisjoint(_SEMANTIC_DOMAINS):
        return RetrievalStrategy.STRUCTURED
    return RetrievalStrategy.HYBRID


def classify_intent(question: str, *, is_overall: bool = False) -> IntentResult:
    """
    `is_overall` is passed in from orchestrator._is_overall_question so the
    "overall" keyword set stays defined in exactly one place.
    """
    normalized = question.lower()
    domain_flags = route(question)
    matched_domains = frozenset(d for d, matched in domain_flags.items() if matched)

    # Future/prediction detection happens before domain retrieval is trusted:
    # a question like "what will my future feedback be" must not become a
    # teacher_feedback semantic lookup just because "feedback" appears. route()
    # above is plain keyword matching, not retrieval, so it's safe to consult
    # here purely to tailor the unsupported message to the mentioned domain(s).
    if any(t in normalized for t in _FUTURE_PREDICTION_TRIGGERS):
        return IntentResult(Intent.FUTURE_PREDICTION, matched_domains, RetrievalStrategy.UNSUPPORTED)

    if "courses" in matched_domains and any(t in normalized for t in _COURSE_RECOMMENDATION_TRIGGERS):
        return IntentResult(Intent.COURSE_RECOMMENDATION, frozenset(), RetrievalStrategy.UNSUPPORTED)

    if is_overall:
        return IntentResult(
            Intent.GENERAL_ACADEMIC_QUESTION, frozenset(domain_flags.keys()), RetrievalStrategy.HYBRID,
        )

    if not matched_domains:
        return IntentResult(Intent.UNSUPPORTED, frozenset(), RetrievalStrategy.UNSUPPORTED)

    if len(matched_domains) == 1:
        (only_domain,) = matched_domains
        intent = _SINGLE_DOMAIN_INTENT[only_domain]
    elif matched_domains == frozenset({"remarks", "attendance"}):
        intent = Intent.ACADEMIC_IMPROVEMENT
    else:
        intent = Intent.GENERAL_ACADEMIC_QUESTION

    return IntentResult(intent, matched_domains, _strategy_for_domains(matched_domains))
