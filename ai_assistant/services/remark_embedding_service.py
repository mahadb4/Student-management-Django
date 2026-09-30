from ai_assistant.models import RemarkEmbedding
from ai_assistant.services.gemini_embedding_service import GeminiEmbeddingService


def embed_remark(remark, embedding_service=None):
    """
    Generates (or regenerates) the embedding for a single Remark and
    persists it as that Remark's RemarkEmbedding row (updated in place,
    never duplicated). Only remark.remark_text is sent to Gemini.
    """
    embedding_service = embedding_service or GeminiEmbeddingService()
    text = remark.remark_text

    values = embedding_service.embed_text(text)

    obj, _created = RemarkEmbedding.objects.update_or_create(
        remark=remark,
        defaults={"embedding": values},
    )
    return obj


def remark_embedding_is_stale(remark):
    """
    True if the Remark has no embedding yet, or the embedding predates the
    Remark's last update (remark_text may have changed since it was embedded).
    """
    embedding = getattr(remark, "embedding", None)
    if embedding is None:
        return True
    return embedding.updated_at < remark.updated_at
