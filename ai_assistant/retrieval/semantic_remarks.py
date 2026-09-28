"""
Permission-aware semantic retrieval over Remarks.

Security model (non-negotiable): authorization and vector similarity are
combined in a single database query. The authorized Remark ID set is applied
as the queryset's filter BEFORE the CosineDistance ordering runs, so an
unauthorized RemarkEmbedding is never even considered by the similarity ranking.
"""
from pgvector.django import CosineDistance

from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_embedding_service import GeminiEmbeddingService
from remarks.authorization import get_remarks_queryset_for_user

# One remark = one embedding (not a chunk of a larger document), so returning
# many risks pulling in tangentially-related feedback instead of the best match.
TOP_K = 2

# Operational starting point (not scientifically derived), set just above the
# distance this project's own test fixtures use for "authorized but not a close
# match", so it doesn't discard a real passing case while still dropping noise.
SIMILARITY_DISTANCE_THRESHOLD = 0.6


def get_semantically_relevant_remarks(
    user, query_text, *, student_id=None, course_offering_id=None, top_k=TOP_K, embedding_service=None,
):
    """
    Returns up to `top_k` authorized Remarks most semantically similar to
    `query_text` and within SIMILARITY_DISTANCE_THRESHOLD, most similar first.
    Remarks with no RemarkEmbedding row are silently excluded; this function
    never generates an embedding on the fly.

    `course_offering_id`, if given, narrows the already-authorized remark ID
    set to just that offering, applied after get_remarks_queryset_for_user.
    """
    if not isinstance(query_text, str) or not query_text.strip():
        raise ValueError("query_text must be a non-empty string.")
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    embedding_service = embedding_service or GeminiEmbeddingService()
    query_vector = embedding_service.embed_text(query_text)

    authorized_remark_ids = get_remarks_queryset_for_user(user, student_id=student_id)
    if course_offering_id:
        authorized_remark_ids = authorized_remark_ids.filter(course_offering_id=course_offering_id)
    authorized_remark_ids = authorized_remark_ids.values("id")

    qs = (
        RemarkEmbedding.objects
        .filter(remark_id__in=authorized_remark_ids)
        .select_related("remark__teacher__user", "remark__course_offering__course")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lte=SIMILARITY_DISTANCE_THRESHOLD)
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
