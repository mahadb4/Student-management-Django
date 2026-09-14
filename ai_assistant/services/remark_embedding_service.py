from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_embedding_service import GeminiEmbeddingService


def embed_remark(remark, embedding_service=None):
    """
    Generates (or regenerates) the embedding for a single Remark and
    persists it as that Remark's RemarkEmbedding row.

    - If the Remark has no embedding yet, one is created.
    - If it already has one, it is updated in place (same OneToOne row),
      never duplicated.
    - embedded_text is always set to the exact text that was sent to
      Gemini, so staleness (embedded_text != remark.remark_text) can be
      detected later without re-calling the API.

    Only remark.remark_text is sent to Gemini - no teacher name, student
    name, course name, IDs, or other metadata.

    This function contains no authorization logic. It is an ingestion
    operation, not a retrieval path - callers are responsible for deciding
    which remarks are eligible to be embedded (see the backfill command).
    """
    embedding_service = embedding_service or GeminiEmbeddingService()
    text = remark.remark_text

    values = embedding_service.embed_text(text)

    obj, _created = RemarkEmbedding.objects.update_or_create(
        remark=remark,
        defaults={"embedding": values, "embedded_text": text},
    )
    return obj


def remark_embedding_is_stale(remark):
    """
    True if the Remark has no embedding yet, or its stored embedded_text no
    longer matches the Remark's current remark_text.
    """
    embedding = getattr(remark, "embedding", None)
    if embedding is None:
        return True
    return embedding.embedded_text != remark.remark_text
