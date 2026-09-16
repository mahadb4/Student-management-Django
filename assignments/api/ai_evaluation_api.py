"""
AI Assignment Evaluation endpoints - a teacher-triggered, single-document
evaluation, separate from the Student RAG Assistant (ai_assistant app). See
assignments.services.assignment_evaluation_service for the Gemini
integration; this module only orchestrates authorization, S3 access, and
persistence around it - it never imports google.genai directly.

Security order (deliberately never reordered):
    1. Authenticate teacher (JWT)
    2. Resolve teacher profile
    3. Find assignment
    4. Verify assignment belongs to teacher
    5. Find submission
    6. Verify submission belongs to that assignment/student
    7. Verify supported format (PDF only, V1)
    8. Fetch S3 bytes
    9. Send document to Gemini
    10. Save evaluation

The S3 object is never fetched before every authorization check above it
has passed - an unauthorized or unsupported-format request never touches
S3 or Gemini at all. The frontend never sees or sends an S3 key/URL to
this endpoint - the server resolves everything from `submission.file_key`
itself, never from client input.

AI suggestion != final grade: this module never writes final_score/
teacher_feedback except via the explicit teacher-review endpoint below,
and never creates a Remark - that remains a separate, existing, manually
teacher-triggered action (remarks.api.remark_api), untouched by this
phase.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from assignments.models import Assignment, AssignmentEvaluation, Submission
from assignments.services.assignment_evaluation_service import (
    AssignmentEvaluationError,
    AssignmentEvaluationInput,
    AssignmentEvaluationService,
)
from common.messages import Messages
from common.services.s3_service import S3Service

s3_service = S3Service()


def _get_teacher_or_error(user):
    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_TEACHER_NOT_FOUND}, status=400)
    return teacher, None


def _get_owned_assignment_or_error(assignment_id, teacher):
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_NOT_FOUND_BY_ID.format(assignment_id)}, status=404)
    if assignment.teacher_id != teacher.id:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_NOT_OWNED}, status=403)
    return assignment, None


def _get_submission_or_error(assignment, student_id):
    submission = Submission.objects.filter(assignment=assignment, student_id=student_id).first()
    if not submission:
        return None, JsonResponse({"error": Messages.SUBMISSION_NOT_FOUND}, status=404)
    return submission, None


def _serialize_evaluation(evaluation):
    return {
        "id": evaluation.id,
        "suggested_score": evaluation.suggested_score,
        "strengths": evaluation.strengths,
        "weaknesses": evaluation.weaknesses,
        "ai_feedback": evaluation.ai_feedback,
        "confidence": evaluation.confidence,
        "final_score": evaluation.final_score,
        "teacher_feedback": evaluation.teacher_feedback,
        "status": evaluation.status,
        "updated_at": evaluation.updated_at,
    }


@csrf_exempt
def assignment_ai_check_api(request, assignment_id, student_id):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status=405)

    # 1. Authenticate teacher
    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    # 2. Resolve teacher profile
    teacher, error = _get_teacher_or_error(user)
    if error:
        return error

    # 3-4. Find assignment, verify ownership
    assignment, error = _get_owned_assignment_or_error(assignment_id, teacher)
    if error:
        return error

    # 5-6. Find submission, verify it belongs to this assignment/student
    # (student_id is the URL path parameter under an assignment the caller
    # already proved they own - never taken from a JWT-derived identity,
    # since the caller here is the TEACHER, not the submitting student).
    submission, error = _get_submission_or_error(assignment, student_id)
    if error:
        return error

    # 7. Verify supported format (PDF only, V1) - checked from the stored
    # file_key itself, never from client-supplied data, BEFORE any S3 call.
    if not submission.file_key.lower().endswith(".pdf"):
        return JsonResponse({"error": Messages.AI_EVALUATION_UNSUPPORTED_FORMAT}, status=400)

    try:
        # 8. Fetch S3 bytes (only now - every authorization/format check above passed)
        pdf_bytes = s3_service.get_object_bytes(submission.file_key)

        # 9. Send document to Gemini
        evaluation_input = AssignmentEvaluationInput(
            assignment_title=assignment.title,
            assignment_description=assignment.description,
            submission_pdf_bytes=pdf_bytes,
        )
        result = AssignmentEvaluationService().evaluate(evaluation_input)
    except AssignmentEvaluationError:
        # Raw provider errors (and the API key) never reach the client.
        return JsonResponse({"error": Messages.AI_EVALUATION_UNAVAILABLE}, status=503)

    # 10. Save evaluation - update_or_create keyed by the OneToOne
    # submission, so re-running "AI Check" replaces this same row rather
    # than creating a duplicate. Only AI-generated fields are written here;
    # final_score/teacher_feedback are never touched by this endpoint.
    evaluation, _created = AssignmentEvaluation.objects.update_or_create(
        submission=submission,
        defaults={
            "suggested_score": result.suggested_score,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "ai_feedback": result.feedback,
            "confidence": result.confidence,
            "status": AssignmentEvaluation.Status.AI_SUGGESTED,
            "final_score": None,
            "teacher_feedback": "",
        },
    )

    return JsonResponse(_serialize_evaluation(evaluation), status=200)


@csrf_exempt
def assignment_evaluation_review_api(request, assignment_id, student_id):
    if request.method != "PATCH":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status=405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    teacher, error = _get_teacher_or_error(user)
    if error:
        return error

    assignment, error = _get_owned_assignment_or_error(assignment_id, teacher)
    if error:
        return error

    submission, error = _get_submission_or_error(assignment, student_id)
    if error:
        return error

    evaluation = getattr(submission, "evaluation", None)
    if not evaluation:
        return JsonResponse({"error": Messages.AI_EVALUATION_NOT_FOUND}, status=404)

    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        valid_statuses = {
            AssignmentEvaluation.Status.APPROVED,
            AssignmentEvaluation.Status.EDITED,
            AssignmentEvaluation.Status.REJECTED,
        }
        status = data.get("status")
        if status not in valid_statuses:
            raise ValueError(Messages.AI_EVALUATION_STATUS_INVALID.format(status, ", ".join(valid_statuses)))

        # The teacher is always the sole author of the authoritative fields
        # - this endpoint never reads suggested_score as a fallback or
        # defaults final_score to it silently; the caller must state a
        # score explicitly (even if it happens to match the AI's suggestion).
        # REJECTED is the one exception: rejecting the AI suggestion
        # outright doesn't require a score yet - the teacher may grade
        # manually later through a separate, existing mechanism.
        final_score = data.get("final_score")
        if status == AssignmentEvaluation.Status.REJECTED:
            if final_score is not None and (not isinstance(final_score, int) or not (0 <= final_score <= 100)):
                raise ValueError(Messages.AI_EVALUATION_SCORE_INVALID)
        else:
            if final_score is None or not isinstance(final_score, int) or not (0 <= final_score <= 100):
                raise ValueError(Messages.AI_EVALUATION_SCORE_INVALID)

        evaluation.final_score = final_score
        evaluation.teacher_feedback = (data.get("teacher_feedback") or "").strip()
        evaluation.status = status
        evaluation.save(update_fields=["final_score", "teacher_feedback", "status", "updated_at"])

        return JsonResponse(_serialize_evaluation(evaluation))

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status=400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
