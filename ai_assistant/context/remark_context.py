"""
Phase 6 of the RAG effort: deterministic context construction from ALREADY-
AUTHORIZED semantic retrieval results (Phase 5's
get_semantically_relevant_remarks output).

This module performs NO authorization and NO database access of its own.
It does not accept a user or student_id, does not query Remark or
RemarkEmbedding, and does not call remarks.authorization. It is a pure
transformation: authorized retrieval results in, LLM-ready context out.
Whatever Phase 5 already excluded for security reasons never reaches this
function in the first place - there is nothing here to re-check.

No randomness, no LLM calls, no summarization, no extra queries - the same
input always produces the same output.
"""

# No existing tokenization framework is used anywhere else in this project
# (confirmed: no tiktoken/similar in requirements.txt), so a simple
# character count is used as a deterministic, dependency-free proxy for
# "how much text a future LLM request would carry." These are starting
# defaults, not tuned against a specific LLM's context window.
DEFAULT_MAX_ITEMS = 10
DEFAULT_MAX_TOTAL_CHARACTERS = 6000


def build_remark_context(retrieval_results, *, max_items=DEFAULT_MAX_ITEMS,
                          max_total_characters=DEFAULT_MAX_TOTAL_CHARACTERS):
    """
    Converts Phase 5 retrieval results into:

        {
            "items": [ {teacher_name, course_name, created_at, text}, ... ],
            "sources": [ {remark_id, teacher_name, course_name, created_at}, ... ],
            "truncated": bool,
        }

    `items` is what a future LLM prompt would be built from - it never
    contains remark_id, student/teacher/course internal IDs, visibility,
    embeddings, or distance scores. `sources` is kept separate specifically
    so a future API can return {"sources": [...]} to the frontend without
    the backend ever trusting an LLM to invent those IDs - they are carried
    through unchanged from Phase 5's retrieval results, never regenerated.

    Ordering is preserved exactly as given (Phase 5's similarity ranking) -
    this function never re-sorts.

    Size limiting: at most `max_items` results are included, and inclusion
    stops early if adding the next full item would exceed
    `max_total_characters`. Individual remark text is NEVER truncated
    mid-string - an item is included whole or not at all, so feedback text
    is never cut in a way that changes its meaning. The one exception is
    the first item: it is always included even if it alone exceeds the
    character budget, so a single long remark can't produce an empty
    context.

    `truncated` is True whenever fewer results were included than were
    passed in, so a future caller can tell the context is partial.
    """
    items = []
    sources = []
    total_characters = 0

    for result in retrieval_results:
        if len(items) >= max_items:
            break

        text = result["text"]
        teacher_name = result["teacher_name"]
        course_name = result["course_name"]
        created_at = result["created_at"]

        item_characters = len(text) + len(teacher_name) + len(course_name) + len(created_at)

        if items and total_characters + item_characters > max_total_characters:
            break

        items.append({
            "teacher_name": teacher_name,
            "course_name": course_name,
            "created_at": created_at,
            "text": text,
        })
        sources.append({
            "remark_id": result["remark_id"],
            "teacher_name": teacher_name,
            "course_name": course_name,
            "created_at": created_at,
        })
        total_characters += item_characters

    return {
        "items": items,
        "sources": sources,
        "truncated": len(items) < len(retrieval_results),
    }
