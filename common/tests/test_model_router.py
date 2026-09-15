"""
Tests for common.ai.model_router.GeminiModelRouter / build_model_chain.

No real Gemini API calls - a fake client is injected throughout, and the
transient/non-transient distinction is exercised using the real
google.genai.errors.APIError subclasses (ClientError/ServerError)
constructed directly, so these tests exercise the actual typed-exception
branch this module prefers, not just the string-matching fallback.
"""
from django.test import SimpleTestCase
from google.genai import errors as genai_errors

from common.ai.model_router import (
    AllModelsExhaustedError,
    GeminiModelRouter,
    build_model_chain,
)


def _api_error(code, status):
    return genai_errors.APIError(code, {"error": {"code": code, "status": status, "message": "boom"}})


def _client_error_429():
    return genai_errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}})


def _server_error_503():
    return genai_errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "overloaded"}})


def _client_error_400():
    return genai_errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "bad request"}})


def _client_error_401():
    return genai_errors.ClientError(401, {"error": {"code": 401, "status": "UNAUTHENTICATED", "message": "no key"}})


def _client_error_403():
    return genai_errors.ClientError(403, {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "denied"}})


class _FakeModels:
    """
    `responses` is a list of either a return value or an Exception
    instance, consumed one per call to generate_content(), in order - lets
    a single fake client simulate "model A fails, model B succeeds".
    """
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _FakeClient:
    def __init__(self, responses):
        self.models = _FakeModels(responses)


class _Response:
    def __init__(self, text):
        self.text = text


class BuildModelChainTests(SimpleTestCase):

    def test_primary_only_when_fallback_empty(self):
        self.assertEqual(build_model_chain("gemini-2.5-flash", ""), ["gemini-2.5-flash"])

    def test_primary_and_fallback_in_order(self):
        chain = build_model_chain("gemini-2.5-flash", "gemini-3.5-flash-lite,gemini-3.8-flash")
        self.assertEqual(chain, ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"])

    def test_whitespace_around_entries_is_stripped(self):
        chain = build_model_chain("gemini-2.5-flash", " gemini-3.5-flash-lite ,  gemini-3.8-flash ")
        self.assertEqual(chain, ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"])

    def test_empty_entries_between_commas_are_skipped(self):
        chain = build_model_chain("gemini-2.5-flash", "gemini-3.5-flash-lite,,gemini-3.8-flash,")
        self.assertEqual(chain, ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"])

    def test_duplicate_of_primary_in_fallback_is_deduplicated(self):
        chain = build_model_chain("gemini-2.5-flash", "gemini-2.5-flash,gemini-3.8-flash")
        self.assertEqual(chain, ["gemini-2.5-flash", "gemini-3.8-flash"])

    def test_duplicate_fallback_entries_are_deduplicated(self):
        chain = build_model_chain("gemini-2.5-flash", "gemini-3.8-flash,gemini-3.8-flash")
        self.assertEqual(chain, ["gemini-2.5-flash", "gemini-3.8-flash"])

    def test_none_fallback_csv_is_treated_as_empty(self):
        self.assertEqual(build_model_chain("gemini-2.5-flash", None), ["gemini-2.5-flash"])


class GeminiModelRouterTests(SimpleTestCase):

    # ── 1. Primary succeeds -> fallback never called ───────────────────
    def test_primary_success_never_calls_fallback(self):
        client = _FakeClient([_Response("ok")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        response = router.generate(contents="hi")

        self.assertEqual(response.text, "ok")
        self.assertEqual(len(client.models.calls), 1)
        self.assertEqual(client.models.calls[0]["model"], "gemini-2.5-flash")

    # ── 2/3. Primary 429 / 503 -> fallback model is called ─────────────
    def test_primary_429_falls_back(self):
        client = _FakeClient([_client_error_429(), _Response("ok")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        response = router.generate(contents="hi")

        self.assertEqual(response.text, "ok")
        self.assertEqual([c["model"] for c in client.models.calls], ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

    def test_primary_503_falls_back(self):
        client = _FakeClient([_server_error_503(), _Response("ok")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        response = router.generate(contents="hi")

        self.assertEqual(response.text, "ok")
        self.assertEqual([c["model"] for c in client.models.calls], ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

    # ── 4. Primary 429, second succeeds -> final answer returned ───────
    def test_final_answer_returned_from_second_model(self):
        client = _FakeClient([_client_error_429(), _Response("from second model")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        response = router.generate(contents="hi")

        self.assertEqual(response.text, "from second model")

    # ── 5. Primary 429, second 429, third succeeds ──────────────────────
    def test_two_fallbacks_exhausted_before_third_succeeds(self):
        client = _FakeClient([_client_error_429(), _client_error_429(), _Response("ok")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"])

        response = router.generate(contents="hi")

        self.assertEqual(response.text, "ok")
        self.assertEqual(
            [c["model"] for c in client.models.calls],
            ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"],
        )

    # ── 6. All models fail 429 -> AllModelsExhaustedError ───────────────
    def test_all_models_fail_raises_all_models_exhausted(self):
        client = _FakeClient([_client_error_429(), _client_error_429(), _server_error_503()])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"])

        with self.assertRaises(AllModelsExhaustedError):
            router.generate(contents="hi")

        self.assertEqual(len(client.models.calls), 3)

    # ── 7. Primary 400 -> no fallback ────────────────────────────────
    def test_400_invalid_argument_does_not_fall_back(self):
        client = _FakeClient([_client_error_400(), _Response("should never be reached")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        with self.assertRaises(genai_errors.ClientError):
            router.generate(contents="hi")

        self.assertEqual(len(client.models.calls), 1)

    # ── 8. Primary 401/403 -> no fallback ────────────────────────────
    def test_401_unauthenticated_does_not_fall_back(self):
        client = _FakeClient([_client_error_401(), _Response("should never be reached")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        with self.assertRaises(genai_errors.ClientError):
            router.generate(contents="hi")

        self.assertEqual(len(client.models.calls), 1)

    def test_403_permission_denied_does_not_fall_back(self):
        client = _FakeClient([_client_error_403(), _Response("should never be reached")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        with self.assertRaises(genai_errors.ClientError):
            router.generate(contents="hi")

        self.assertEqual(len(client.models.calls), 1)

    def test_unrecognized_exception_type_does_not_fall_back(self):
        # A programming/configuration error (e.g. a bug in how the caller
        # built the request) is not a google.genai APIError at all - the
        # router must not treat an unrecognized exception as transient.
        client = _FakeClient([RuntimeError("boom"), _Response("should never be reached")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        with self.assertRaises(RuntimeError):
            router.generate(contents="hi")

        self.assertEqual(len(client.models.calls), 1)

    # ── 9. No duplicate model attempts ──────────────────────────────
    def test_duplicate_models_in_chain_are_each_only_attempted_once_as_given(self):
        # The router itself trusts the chain it's given (deduplication is
        # build_model_chain's job) - this proves it never re-attempts a
        # model beyond what's in the chain, i.e. no internal retry-same-
        # model loop hidden inside generate().
        client = _FakeClient([_client_error_429(), _Response("ok")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash", "gemini-3.5-flash-lite"])

        router.generate(contents="hi")

        models_tried = [c["model"] for c in client.models.calls]
        self.assertEqual(len(models_tried), len(set(models_tried)))

    # ── 10. Model order is respected ─────────────────────────────────
    def test_model_order_is_respected(self):
        client = _FakeClient([_client_error_429(), _client_error_429(), _Response("ok")])
        router = GeminiModelRouter(client, ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"])

        router.generate(contents="hi")

        self.assertEqual(
            [c["model"] for c in client.models.calls],
            ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"],
        )

    # ── Kwargs pass-through ───────────────────────────────────────────
    def test_arbitrary_kwargs_are_forwarded_unchanged_to_generate_content(self):
        client = _FakeClient([_Response("ok")])
        router = GeminiModelRouter(client, ["gemini-2.5-flash"])
        sentinel_config = object()

        router.generate(contents=["a", "b"], config=sentinel_config)

        call = client.models.calls[0]
        self.assertEqual(call["contents"], ["a", "b"])
        self.assertIs(call["config"], sentinel_config)

    def test_empty_model_list_raises_value_error(self):
        client = _FakeClient([])
        with self.assertRaises(ValueError):
            GeminiModelRouter(client, [])
