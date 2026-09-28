"""
Deterministic context construction from already-authorized semantic retrieval
results (get_semantically_relevant_remarks output). Performs no authorization
or database access of its own - it is a pure transformation.
"""

# No tokenization framework is used elsewhere in this project, so a character
# count is used as a deterministic, dependency-free proxy for prompt size.
DEFAULT_MAX_ITEMS = 10
DEFAULT_MAX_TOTAL_CHARACTERS = 6000


def build_remark_context(retrieval_results, *, max_items=DEFAULT_MAX_ITEMS,
                          max_total_characters=DEFAULT_MAX_TOTAL_CHARACTERS):
    """
    Converts retrieval results into:

        {
            "items": [ {teacher_name, course_name, created_at, text}, ... ],
            "sources": [ {remark_id, teacher_name, course_name, created_at}, ... ],
            "truncated": bool,
        }

    `items` never contains remark_id or other internal IDs. `sources` is kept
    separate so an API can return source IDs without ever trusting an LLM to
    invent them - carried through unchanged from the retrieval results.

    Ordering is preserved exactly as given; this function never re-sorts.
    Individual remark text is never truncated mid-string - an item is included
    whole or not at all, except the first item is always included even if it
    alone exceeds the character budget, so a single long remark can't produce
    an empty context.
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
