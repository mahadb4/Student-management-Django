from django.db import models
from pgvector.django import VectorField


class RemarkEmbedding(models.Model):
    """
    Semantic embedding for a Remark. Retrieval always filters via
    remarks.authorization.get_remarks_queryset_for_user before similarity ordering.
    """
    remark = models.OneToOneField(
        "remarks.Remark", on_delete=models.CASCADE, related_name="embedding",
    )
    embedding = VectorField(dimensions=768)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"RemarkEmbedding(remark_id={self.remark_id})"
