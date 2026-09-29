"""
Student Academic Assistant orchestrator. Routes a question through router.route()
and resolve_mentioned_course(), then calls each per-domain context builder (each
independently authorized), and combines their results into a GeminiGenerationService
answer. Performs no authorization or database queries of its own.
"""
from ai_assistant.casual_intent import build_casual_response, classify_casual_intent
from ai_assistant.context.assignment_context import build_assignment_context
from ai_assistant.context.attendance_context import build_attendance_context
from ai_assistant.context.course_context import build_course_context
from ai_assistant.context.remark_context import build_remark_context
from ai_assistant.course_resolution import resolve_mentioned_course
from ai_assistant.intent_classifier import Intent, RetrievalStrategy, classify_intent
from ai_assistant.retrieval.semantic_remarks import get_semantically_relevant_remarks
from ai_assistant.router import route
from ai_assistant.services.gemini_generation_service import GeminiGenerationService

NO_RELEVANT_DOMAIN_MESSAGE = (
    "I'm mainly here to help with your academic information, like your courses, attendance, assignments, "
    "and teacher feedback. I don't have anything on that topic, but feel free to ask me something about "
    "your studies."
)

NOT_ENOUGH_INFORMATION_MESSAGE = "There is not enough information available to answer this question."

# Recognized intents the system has no data source for at all, distinct from
# Intent.UNSUPPORTED (no domain matched, handled via NO_RELEVANT_DOMAIN_MESSAGE).
_UNSUPPORTED_INTENT_MESSAGES = {
    Intent.COURSE_RECOMMENDATION: (
        "I can show you the courses you're currently enrolled in, but I don't have your future semester "
        "plan, prerequisite structure, or an advisor-approved course roadmap, so I can't reliably recommend "
        "your next courses from the data available here. Your academic advisor can guide that decision "
        "using your full degree plan."
    ),
}
_DEFAULT_UNSUPPORTED_CAPABILITY_MESSAGE = (
    "I'm mainly here to help with your academic information, like your courses, attendance, assignments, "
    "and teacher feedback. I don't have anything on that topic, but feel free to ask me something about "
    "your studies."
)

# Domain-specific FUTURE_PREDICTION replies, so a question about future feedback
# talks about feedback rather than reciting all four domains every time. Falls
# back to a general reply when the question doesn't clearly point at one domain.
_FUTURE_PREDICTION_MESSAGES = {
    frozenset({"remarks"}): (
        "I can help you understand the feedback you've received from your teachers so far, but I can't know "
        "what feedback you'll receive in the future. I can show you your recent feedback and help you see "
        "what you may need to work on."
    ),
    frozenset({"attendance"}): (
        "I can show you your attendance record so far, but I can't predict what your attendance will look "
        "like going forward. I can walk you through what you've got on record right now if that helps."
    ),
    frozenset({"assignments"}): (
        "I can show you the assignments you currently have, but I don't know what assignments a teacher "
        "will give you later on. I can show you what's due right now if that's useful."
    ),
    frozenset({"courses"}): (
        "I can tell you about the courses you're currently taking, but I can't predict a future grade or "
        "outcome in them. I can walk you through how things stand right now."
    ),
}
_DEFAULT_FUTURE_PREDICTION_MESSAGE = (
    "I can help you understand your current courses, attendance, assignments, and teacher feedback, but I "
    "can't predict what's coming next, like a future grade or upcoming feedback. I can show you what's on "
    "record right now if that helps."
)


def _unsupported_capability_message(intent):
    return _UNSUPPORTED_INTENT_MESSAGES.get(intent, _DEFAULT_UNSUPPORTED_CAPABILITY_MESSAGE)


def _future_prediction_message(domains):
    return _FUTURE_PREDICTION_MESSAGES.get(domains, _DEFAULT_FUTURE_PREDICTION_MESSAGE)

# When any of these phrases appear, all four domains are activated regardless
# of which specific domain keywords also matched.
_OVERALL_KEYWORDS = ("overall", "summary", "how am i doing", "academic progress")


def _is_overall_question(question: str) -> bool:
    normalized = question.lower()
    return any(keyword in normalized for keyword in _OVERALL_KEYWORDS)


def _course_ambiguous_message(candidates):
    return f"I found more than one course matching that name: {', '.join(candidates)}. Which one do you mean?"


def _course_not_found_message(phrase):
    return (
        f"You don't appear to be currently enrolled in a course matching \"{phrase}\". "
        "Ask me about one of your current courses, or say \"what courses am I taking\" to see the list."
    )


def answer_academic_question(user, question, *, embedding_service=None, generation_service=None):
    # Only a full match short-circuits here; see ai_assistant.casual_intent.
    casual_intent = classify_casual_intent(question)
    if casual_intent is not None:
        return {"answer": build_casual_response(casual_intent, user), "sources": []}

    domains = route(question)
    overall = _is_overall_question(question)

    # Recognized-but-structurally-unsupported intents are caught before course
    # resolution/retrieval run, since no data source exists for them.
    intent_result = classify_intent(question, is_overall=overall)
    if intent_result.intent is Intent.FUTURE_PREDICTION:
        return {"answer": _future_prediction_message(intent_result.domains), "sources": []}
    if intent_result.retrieval_strategy is RetrievalStrategy.UNSUPPORTED and intent_result.intent != Intent.UNSUPPORTED:
        return {"answer": _unsupported_capability_message(intent_result.intent), "sources": []}

    course_match = resolve_mentioned_course(user, question)

    # An ambiguous course match is never safe to guess through.
    if course_match["status"] == "ambiguous":
        return {"answer": _course_ambiguous_message(course_match["candidates"]), "sources": []}

    # Only surface "no such course" when no other domain keyword already routed,
    # since naming a specific (unrecognized) course is a more specific signal
    # than the generic overall trigger and must win.
    if course_match["status"] == "none_but_mentioned" and not any(domains.values()):
        return {"answer": _course_not_found_message(course_match["phrase"]), "sources": []}

    if overall:
        domains = {key: True for key in domains}
    elif course_match["status"] == "matched" and not any(domains.values()):
        # Resolving a specific course with no domain keyword is itself the
        # signal that a broad, course-scoped answer is wanted.
        domains = {key: True for key in domains}

    if not any(domains.values()):
        return {"answer": NO_RELEVANT_DOMAIN_MESSAGE, "sources": []}

    course_offering_id = course_match["course_offering_id"] if course_match["status"] == "matched" else None

    items = []
    sources = []

    if domains["remarks"]:
        retrieval_results = get_semantically_relevant_remarks(
            user, question, course_offering_id=course_offering_id, embedding_service=embedding_service,
        )
        remark_context = build_remark_context(retrieval_results)
        items.extend(remark_context["items"])
        sources.extend({"type": "remark", **source} for source in remark_context["sources"])

    if domains["attendance"]:
        attendance_context = build_attendance_context(user, course_offering_id=course_offering_id)
        items.append(attendance_context["prompt_item"])
        sources.extend(attendance_context["sources"])

    if domains["assignments"]:
        assignment_context = build_assignment_context(user, course_offering_id=course_offering_id)
        items.append(assignment_context["prompt_item"])
        sources.extend(assignment_context["sources"])

    if domains["courses"]:
        course_context = build_course_context(user, course_offering_id=course_offering_id)
        items.append(course_context["prompt_item"])
        sources.extend(course_context["sources"])

    if not items:
        return {"answer": NOT_ENOUGH_INFORMATION_MESSAGE, "sources": []}

    generation_service = generation_service or GeminiGenerationService()
    combined_context = {"items": items, "sources": sources, "truncated": False}
    answer = generation_service.generate_answer(question, combined_context)

    return {"answer": answer, "sources": sources}
