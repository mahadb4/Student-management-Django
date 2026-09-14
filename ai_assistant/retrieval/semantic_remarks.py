"""
Phase 5 of the RAG effort: permission-aware semantic retrieval over Remarks.

Security model (non-negotiable): authorization and vector similarity are
combined in a single database query. We never fetch embeddings broadly and
filter unauthorized rows afterward in Python - the authorized Remark ID set
(from remarks.authorization.get_remarks_queryset_for_user, unchanged) is
applied as the queryset's filter BEFORE the CosineDistance ordering runs,
so an unauthorized RemarkEmbedding is never even considered by the
similarity ranking, regardless of how semantically close it is to the
query.

This module adds no authorization logic of its own - same discipline as
ai_assistant/retrieval/remarks.py (Phase 2).
"""
from pgvector.django import CosineDistance

from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_embedding_service import GeminiEmbeddingService
from remarks.authorization import get_remarks_queryset_for_user


def get_semantically_relevant_remarks(
    user, query_text, *, student_id=None, course_offering_id=None, top_k=5, embedding_service=None,
):
    """
    Returns up to `top_k` authorized Remarks most semantically similar to
    `query_text`, most similar first.

    Remarks with no RemarkEmbedding row (not yet embedded) are silently
    excluded - this function never generates an embedding on the fly;
    embedding generation stays a separate, explicit step (Phase 4).

    `course_offering_id` (Phase 10E), if given, narrows the ALREADY-
    authorized remark ID set to just that offering - applied AFTER
    get_remarks_queryset_for_user, never instead of it, so a course-scoped
    search can never surface anything the unscoped search couldn't.
    """
    if not isinstance(query_text, str) or not query_text.strip():
        raise ValueError("query_text must be a non-empty string.")
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    embedding_service = embedding_service or GeminiEmbeddingService()
    query_vector = embedding_service.embed_text(query_text)

    # Single source of truth for who may see which Remarks. Untouched,
    # called exactly as-is - no re-derivation of its filtering logic here.
    authorized_remark_ids = get_remarks_queryset_for_user(user, student_id=student_id)
    if course_offering_id:
        authorized_remark_ids = authorized_remark_ids.filter(course_offering_id=course_offering_id)
    authorized_remark_ids = authorized_remark_ids.values("id")

    qs = (
        RemarkEmbedding.objects
        .filter(remark_id__in=authorized_remark_ids)
        .select_related("remark__teacher__user", "remark__course_offering__course")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:top_k]
    )

    return [
        {
            "remark_id": row.remark_id,
            "text": row.remark.remark_text,
            "teacher_name": row.remark.teacher.user.name,
            "course_name": row.remark.course_offering.course.name,
            "visibility": row.remark.visibility,
            "created_at": row.remark.created_at.isoformat(),
            "distance": float(row.distance),
        }
        for row in qs
    ]
