from django.db import models
from pgvector.django import VectorField


class RemarkEmbedding(models.Model):
    """
    One row per Remark. Holds the semantic embedding used for authorized
    similarity search over teacher remarks (Phase 3+). This model adds no
    authorization logic of its own - retrieval always starts from
    remarks.authorization.get_remarks_queryset_for_user and filters this
    table by the resulting authorized remark IDs before any similarity
    ordering is applied.
    """
    remark = models.OneToOneField(
        "remarks.Remark", on_delete=models.CASCADE, related_name="embedding",
    )
    embedding = VectorField(dimensions=768)
    embedded_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"RemarkEmbedding(remark_id={self.remark_id})"
