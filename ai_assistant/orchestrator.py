"""
Phase 10B/10C/10D/10E: the Student Academic Assistant orchestrator.

    question
       |
       v
    router.route()               -- which domains are relevant? (NOT authorization)
    resolve_mentioned_course()   -- did the question name one of the student's
                                     OWN authorized courses? (NOT authorization -
                                     search space is already-authorized courses only)
       |
       v
    per-domain context builders  -- each independently authorized, each
    optionally narrowed to one course_offering_id AFTER its own authorization
    check, never instead of it:
       remarks:     remarks.authorization.get_remarks_queryset_for_user (Phase 5)
       attendance:  common.permissions.apply_data_scope (Phase 10B)
       assignments: assignments.authorization.get_assignments_queryset_for_user (Phase 10C)
       courses:     common.permissions.apply_data_scope (Phase 10D)
       |
       v
    combined context -> GeminiGenerationService (Phase 7, unchanged)
       |
       v
    {"answer": str, "sources": [...]}

This module performs no authorization of its own and no database queries
of its own - it only calls other functions that already do, and combines
their results. If no domain is relevant to the question, none is queried
and Gemini is never called - a fallback/clarification message is returned
directly.
"""
from ai_assistant.context.assignment_context import build_assignment_context
from ai_assistant.context.attendance_context import build_attendance_context
from ai_assistant.context.course_context import build_course_context
from ai_assistant.context.remark_context import build_remark_context
from ai_assistant.course_resolution import resolve_mentioned_course
from ai_assistant.retrieval.semantic_remarks import get_semantically_relevant_remarks
from ai_assistant.router import route
from ai_assistant.services.gemini_generation_service import GeminiGenerationService

NO_RELEVANT_DOMAIN_MESSAGE = (
    "I can help with your courses, attendance, assignments, or feedback from your teachers. "
    "What would you like to know?"
)
NOT_ENOUGH_INFORMATION_MESSAGE = "There is not enough information available to answer this question."

# Additive layer on top of the existing keyword router (Phase 10B/C/D),
# not a rewrite of it - when any of these phrases appear, all four domains
# are activated regardless of which specific domain keywords also matched.
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
    domains = route(question)
    overall = _is_overall_question(question)
    course_match = resolve_mentioned_course(user, question)

    # An ambiguous course match is never safe to guess through - stop here,
    # no retrieval, no Gemini call, regardless of what else was routed.
    if course_match["status"] == "ambiguous":
        return {"answer": _course_ambiguous_message(course_match["candidates"]), "sources": []}

    # Only surface the explicit "no such course" message when no OTHER
    # domain keyword already routed (a harmless mis-extracted trailing
    # phrase, e.g. "...in general?", must not hijack an already-answerable
    # question into a dead end). Deliberately NOT conditioned on `overall`:
    # a phrase like "How am I doing in Physics?" also happens to contain
    # the overall-trigger substring "how am i doing", but naming a specific
    # (unrecognized) course is a MORE specific signal than the generic
    # overall trigger and must win - otherwise a failed course lookup would
    # silently fall through to a full, unscoped four-domain answer instead
    # of telling the student the course wasn't found.
    if course_match["status"] == "none_but_mentioned" and not any(domains.values()):
        return {"answer": _course_not_found_message(course_match["phrase"]), "sources": []}

    if overall:
        domains = {key: True for key in domains}
    elif course_match["status"] == "matched" and not any(domains.values()):
        # "How am I doing in Database Systems?" carries no domain keyword
        # of its own - resolving a specific course is itself the signal
        # that a broad, course-scoped answer (all four domains, narrowed)
        # is wanted, mirroring the "overall" trigger but for one course.
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
