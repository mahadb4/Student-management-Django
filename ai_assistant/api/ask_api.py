"""
Phase 8 (updated in Phase 10B) of the RAG effort: the public HTTP entry
point for the Student Academic Assistant.

This view is a thin orchestrator wrapper. It does not query
RemarkEmbedding/Attendance directly, does not build Gemini prompts, does
not route questions to a domain, and does not implement any authorization
logic of its own - it only calls
ai_assistant.orchestrator.answer_academic_question, which in turn calls
the existing, independently-authorized per-domain context builders
(Phase 5 remarks retrieval, Phase 10B attendance context) and Phase 7's
generation service.

request.user (resolved from the JWT, exactly like every other view in this
project) is the ONLY source of identity. The request body is never allowed
to specify who the requester is - there is deliberately no student_id (or
any other identity-shaped field) read from the request body anywhere in
this view.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ai_assistant.orchestrator import answer_academic_question
from ai_assistant.services.gemini_embedding_service import EmbeddingGenerationError
from ai_assistant.services.gemini_generation_service import AnswerGenerationError
from common.messages import Messages

# Mirrors GeminiGenerationService.MAX_QUESTION_LENGTH - validated here first
# so an over-length question is rejected before any routing/retrieval/
# embedding call is made, not just before the Gemini generation call.
MAX_QUESTION_LENGTH = 2000


@csrf_exempt
def ask_api(request):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status=405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT}, status=400)

    # Deliberately: no student_id, teacher_id, or any other identity field
    # is ever read from `data`. Only "question" is consumed from the body.
    question = (data.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": Messages.AI_ASSISTANT_QUESTION_REQUIRED}, status=400)
    if len(question) > MAX_QUESTION_LENGTH:
        return JsonResponse(
            {"error": Messages.AI_ASSISTANT_QUESTION_TOO_LONG.format(MAX_QUESTION_LENGTH)}, status=400
        )

    try:
        # `user` here is the JWT-resolved request.user - never anything
        # derived from the request body. The orchestrator's router only
        # decides WHICH already-authorized domain builder(s) to call; it
        # has no ability to widen what any of them returns.
        result = answer_academic_question(user, question)
    except (EmbeddingGenerationError, AnswerGenerationError):
        # Raw provider errors (and the API key) never reach the client.
        return JsonResponse({"error": Messages.AI_ASSISTANT_UNAVAILABLE}, status=503)

    # Sources come entirely from the orchestrator's per-domain, already-
    # authorized context builders - never from the Gemini response. The
    # LLM has no field it could use to fabricate or modify a source.
    return JsonResponse({"answer": result["answer"], "sources": result["sources"]})
