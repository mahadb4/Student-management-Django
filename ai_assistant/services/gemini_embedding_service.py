from django.conf import settings
from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768


class EmbeddingGenerationError(Exception):
    """
    Raised when Gemini fails to return a usable embedding - either the API
    call itself failed, or it returned a vector of the wrong dimensionality.
    Never includes the API key or raw remark text in its message.
    """
    pass


class GeminiEmbeddingService:
    """
    Thin wrapper around the google-genai SDK for generating text embeddings.
    Provider-specific on purpose - this is not a generic embedding
    abstraction layer, matching the project's existing service style (see
    common/services/s3_service.py).
    """

    def __init__(self, client=None):
        self.client = client or genai.Client(api_key=settings.GEMINI_API_KEY)

    def embed_text(self, text):
        """
        Returns a list of EMBEDDING_DIMENSIONS floats for the given text.
        Raises EmbeddingGenerationError if the call fails or the returned
        vector has an unexpected number of dimensions.
        """
        try:
            result = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
            )
        except Exception as e:
            raise EmbeddingGenerationError(f"Gemini embedding request failed: {type(e).__name__}") from e

        try:
            [embedding_obj] = result.embeddings
            values = list(embedding_obj.values)
        except (ValueError, AttributeError, TypeError) as e:
            raise EmbeddingGenerationError("Gemini returned an unexpected response shape.") from e

        if len(values) != EMBEDDING_DIMENSIONS:
            raise EmbeddingGenerationError(
                f"Gemini returned a {len(values)}-dimensional vector, expected {EMBEDDING_DIMENSIONS}."
            )

        return values
