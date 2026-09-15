"""
Generation-only Gemini model router/fallback.

Shared by ai_assistant.services.gemini_generation_service and
assignments.services.assignment_evaluation_service - the two independent
AI capabilities in this project that call client.models.generate_content().
This module has no opinion about prompts, response schemas, or what the
caller does with the response - it only decides WHICH model name(s) to
try, in order, and WHEN to move on to the next one. It is not a generic
multi-provider abstraction (no LangChain/LangGraph-style framework) - it
is a thin, deliberately small retry-over-model-names loop around the
already-instantiated google-genai client the caller passes in.

Not used for the Gemini EMBEDDING model (ai_assistant.services
.gemini_embedding_service) - embeddings are a separate, single-model flow
and are explicitly out of scope for this router.

Fallback is ONLY for errors that mean "this model can't serve the request
right now" - HTTP 429 (RESOURCE_EXHAUSTED) and 503 (UNAVAILABLE) service
errors from the Gemini API. Anything else (invalid request, auth/permission
errors, a bug in how the caller built the request) is a real application
error - a different model will not fix it, so it is raised immediately
without trying further models. When the installed google-genai SDK
exposes typed exceptions (google.genai.errors.APIError and its
ClientError/ServerError subclasses), those are used instead of string
matching; if that import ever becomes unavailable, this module falls back
to duck-typing the SDK's own `code`/`status` attributes rather than
failing to import.
"""
import logging

logger = logging.getLogger(__name__)

try:
    from google.genai import errors as genai_errors
except ImportError:  # pragma: no cover - google-genai is a hard dependency of this project
    genai_errors = None

# HTTP status codes that indicate the current model is temporarily
# unavailable (quota/rate-limit or transient service outage), not that the
# request itself is invalid.
_TRANSIENT_STATUS_CODES = {429, 503}
_TRANSIENT_STATUS_NAMES = {"RESOURCE_EXHAUSTED", "UNAVAILABLE"}


class AllModelsExhaustedError(Exception):
    """
    Raised when every model in the configured chain failed with a
    transient (quota/availability) error. Callers catch this alongside
    other exceptions from generate() - it carries no more information
    than a normal API failure would, so it never leaks model names or
    provider details to anything outside this module's own logging.
    """
    pass


def _is_transient_error(exc):
    """
    True only for errors that mean "try a different model", per the
    module docstring above. Deliberately conservative: an exception type
    this function doesn't recognize is treated as non-transient (no
    fallback), since retrying on an unrecognized error would risk masking
    a real bug behind a slower, multi-model retry loop.
    """
    if genai_errors is not None and isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        status = getattr(exc, "status", None)
        return code in _TRANSIENT_STATUS_CODES or status in _TRANSIENT_STATUS_NAMES

    # Duck-typed fallback for environments where the typed exception
    # import above is unavailable - still attribute-based, not string
    # matching against exception messages.
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    return code in _TRANSIENT_STATUS_CODES or status in _TRANSIENT_STATUS_NAMES


def _error_reason(exc):
    status = getattr(exc, "status", None)
    return status or type(exc).__name__


def build_model_chain(primary, fallback_csv):
    """
    Builds an ordered, deduplicated model name list: `primary` first, then
    each entry of `fallback_csv` (a comma-separated string, as read from
    settings/environment) in the order given. Handles the configuration-
    safety cases called out for this feature: surrounding whitespace,
    empty entries, and duplicates (including a fallback entry that
    happens to repeat `primary`) are all silently collapsed rather than
    producing a duplicate attempt or a blank model name.
    """
    candidates = [primary] + (fallback_csv or "").split(",")
    chain = []
    seen = set()
    for name in candidates:
        name = (name or "").strip()
        if not name or name in seen:
            continue
        chain.append(name)
        seen.add(name)
    return chain


class GeminiModelRouter:
    """
    Tries `models` in order against `client.models.generate_content(...)`,
    moving to the next model only on a transient (quota/availability)
    error. Returns the first successful response object unchanged - it
    never inspects or transforms the response, so it works identically
    for GeminiGenerationService's plain-text config and
    AssignmentEvaluationService's multimodal/structured-output config.

    Performs no authorization, no context construction, no database
    access - it is purely a model-selection layer sitting between an
    already-built request and the google-genai client.
    """

    def __init__(self, client, models):
        if not models:
            raise ValueError("models must be a non-empty list of model names.")
        self.client = client
        self.models = models

    def generate(self, **kwargs):
        last_error = None

        for model in self.models:
            logger.info("AI generation attempt: model=%s", model)
            try:
                response = self.client.models.generate_content(model=model, **kwargs)
            except Exception as exc:
                if not _is_transient_error(exc):
                    logger.warning(
                        "AI generation failed (non-transient, no fallback): model=%s reason=%s",
                        model, _error_reason(exc),
                    )
                    raise
                logger.warning(
                    "AI generation failed: model=%s reason=%s", model, _error_reason(exc),
                )
                last_error = exc
                continue
            else:
                logger.info("AI generation succeeded: model=%s", model)
                return response

        logger.error("AI generation failed for all %d configured model(s).", len(self.models))
        raise AllModelsExhaustedError(
            "All configured Gemini models are currently unavailable."
        ) from last_error
