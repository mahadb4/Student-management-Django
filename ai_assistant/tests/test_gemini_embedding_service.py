"""
Phase 4 tests: GeminiEmbeddingService.

No real Gemini API calls are made - a fake client is injected, so these
tests never touch the network and never require a real GEMINI_API_KEY.
"""
from django.test import TestCase

from ai_assistant.services.gemini_embedding_service import (
    EMBEDDING_DIMENSIONS,
    EmbeddingGenerationError,
    GeminiEmbeddingService,
)


class _FakeEmbeddingObj:
    def __init__(self, values):
        self.values = values


class _FakeEmbedResult:
    def __init__(self, values):
        self.embeddings = [_FakeEmbeddingObj(values)]


class _FakeModels:
    def __init__(self, values=None, exception=None):
        self._values = values
        self._exception = exception
        self.last_call_kwargs = None

    def embed_content(self, **kwargs):
        self.last_call_kwargs = kwargs
        if self._exception:
            raise self._exception
        return _FakeEmbedResult(self._values)


class _FakeClient:
    def __init__(self, values=None, exception=None):
        self.models = _FakeModels(values=values, exception=exception)


class GeminiEmbeddingServiceTests(TestCase):

    def test_embed_text_returns_correct_dimension_vector(self):
        fake_client = _FakeClient(values=[0.1] * EMBEDDING_DIMENSIONS)
        service = GeminiEmbeddingService(client=fake_client)

        result = service.embed_text("Struggling with joins.")

        self.assertEqual(len(result), EMBEDDING_DIMENSIONS)
        self.assertEqual(result, [0.1] * EMBEDDING_DIMENSIONS)

    def test_only_the_given_text_is_sent_to_gemini(self):
        fake_client = _FakeClient(values=[0.1] * EMBEDDING_DIMENSIONS)
        service = GeminiEmbeddingService(client=fake_client)

        service.embed_text("Improved significantly.")

        self.assertEqual(fake_client.models.last_call_kwargs["contents"], "Improved significantly.")

    def test_wrong_dimension_response_is_rejected(self):
        fake_client = _FakeClient(values=[0.1] * 5)  # wrong size
        service = GeminiEmbeddingService(client=fake_client)

        with self.assertRaises(EmbeddingGenerationError):
            service.embed_text("Struggling with joins.")

    def test_api_failure_raises_embedding_generation_error(self):
        fake_client = _FakeClient(exception=RuntimeError("network down"))
        service = GeminiEmbeddingService(client=fake_client)

        with self.assertRaises(EmbeddingGenerationError):
            service.embed_text("Struggling with joins.")

    def test_api_failure_does_not_leak_exception_details_in_message(self):
        fake_client = _FakeClient(exception=RuntimeError("some internal detail"))
        service = GeminiEmbeddingService(client=fake_client)

        try:
            service.embed_text("Struggling with joins.")
            self.fail("expected EmbeddingGenerationError")
        except EmbeddingGenerationError as e:
            self.assertNotIn("some internal detail", str(e))

    def test_malformed_response_raises_embedding_generation_error(self):
        class _BrokenModels:
            def embed_content(self, **kwargs):
                class _Empty:
                    embeddings = []
                return _Empty()

        class _BrokenClient:
            def __init__(self):
                self.models = _BrokenModels()

        service = GeminiEmbeddingService(client=_BrokenClient())

        with self.assertRaises(EmbeddingGenerationError):
            service.embed_text("Struggling with joins.")
