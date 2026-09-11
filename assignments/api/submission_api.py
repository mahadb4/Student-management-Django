import json
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from common.constants import ASSIGNMENT_FILE_CONTENT_TYPES, ASSIGNMENT_FILE_URL_EXPIRY_SECONDS, MAX_ASSIGNMENT_FILE_SIZE_BYTES
from common.decorators import enforce_permissions
from common.messages import Messages
from common.services.s3_service import S3Service
from common.utils import extension_for_allowed_content_type, paginate_queryset
from assignments.authorization import student_enrolled_in_offering
from assignments.models import Assignment, Submission
from enrollments.models import Enrollment

s3_service = S3Service()


def _get_student_or_error(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_STUDENT_NOT_FOUND}, status = 400)
    return student, None


def _get_teacher_or_error(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not teacher:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_TEACHER_NOT_FOUND}, status = 400)
    return teacher, None


def _get_assignment_for_own_student(assignment_id, student):
    """
    Returns (assignment, error_response). Also enforces that the student is
    genuinely enrolled in the assignment's course offering - the core
    "student can only submit to assignments they're allowed to access" rule.
    """
    assignment = Assignment.objects.select_related("course_offering").filter(id = assignment_id).first()
    if not assignment:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_NOT_FOUND_BY_ID.format(assignment_id)}, status = 404)

    if not student_enrolled_in_offering(student, assignment.course_offering):
        return None, JsonResponse({"error": Messages.SUBMISSION_NOT_ENROLLED}, status = 403)

    return assignment, None


@enforce_permissions('assignments', 'submission')
def my_submission_api(request, assignment_id):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    student, error = _get_student_or_error(request)
    if error:
        return error

    assignment, error = _get_assignment_for_own_student(assignment_id, student)
    if error:
        return error

    submission = Submission.objects.filter(assignment = assignment, student = student).first()
    if not submission:
        return JsonResponse({"status": "PENDING", "submitted_at": None, "file_url": None})

    return JsonResponse({
        "status": "SUBMITTED",
        "submitted_at": submission.submitted_at,
        "file_url": s3_service.generate_view_url(submission.file_key, expires_in = ASSIGNMENT_FILE_URL_EXPIRY_SECONDS),
    })


@csrf_exempt
@enforce_permissions('assignments', 'submission')
def submission_upload_url_api(request, assignment_id):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    student, error = _get_student_or_error(request)
    if error:
        return error

    assignment, error = _get_assignment_for_own_student(assignment_id, student)
    if error:
        return error

    if timezone.now() > assignment.due_at:
        return JsonResponse({"error": Messages.ASSIGNMENT_PAST_DUE}, status = 400)

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        content_type = (data.get("content_type") or "").strip()
        if not content_type:
            raise ValueError(Messages.ASSIGNMENT_FILE_CONTENT_TYPE_REQUIRED)

        extension = extension_for_allowed_content_type(
            content_type, ASSIGNMENT_FILE_CONTENT_TYPES, Messages.ASSIGNMENT_FILE_INVALID_CONTENT_TYPE
        )
        key = f"submissions/{assignment.id}/{student.id}/file.{extension}"
        upload_url = s3_service.generate_upload_url(key, content_type, expires_in = ASSIGNMENT_FILE_URL_EXPIRY_SECONDS)
        return JsonResponse({"upload_url": upload_url, "key": key, "content_type": content_type})

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('assignments', 'submission')
def submission_confirm_api(request, assignment_id):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    student, error = _get_student_or_error(request)
    if error:
        return error

    assignment, error = _get_assignment_for_own_student(assignment_id, student)
    if error:
        return error

    if timezone.now() > assignment.due_at:
        return JsonResponse({"error": Messages.ASSIGNMENT_PAST_DUE}, status = 400)

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError(Messages.ASSIGNMENT_FILE_KEY_REQUIRED)

        expected_prefix = f"submissions/{assignment.id}/{student.id}/file."
        if not key.startswith(expected_prefix):
            raise ValueError(Messages.SUBMISSION_FILE_KEY_MISMATCH)

        metadata = s3_service.head_object(key)
        if metadata is None:
            raise ValueError(Messages.ASSIGNMENT_FILE_UPLOAD_NOT_FOUND)

        content_length = metadata.get("content_length") or 0
        if content_length > MAX_ASSIGNMENT_FILE_SIZE_BYTES:
            s3_service.delete_object(key)
            raise ValueError(Messages.ASSIGNMENT_FILE_TOO_LARGE.format(MAX_ASSIGNMENT_FILE_SIZE_BYTES // (1024 * 1024)))

        # Upsert: resubmitting before the due date replaces the existing row
        # (and its S3 object) rather than creating a second one - see
        # Submission's unique_together.
        submission = Submission.objects.filter(assignment = assignment, student = student).first()
        old_key = submission.file_key if submission else None

        if submission:
            submission.file_key = key
            submission.save()
        else:
            submission = Submission.objects.create(assignment = assignment, student = student, file_key = key)

        if old_key and old_key != key:
            s3_service.delete_object(old_key)

        return JsonResponse({
            "status": "SUBMITTED",
            "submitted_at": submission.submitted_at,
            "file_url": s3_service.generate_view_url(key, expires_in = ASSIGNMENT_FILE_URL_EXPIRY_SECONDS),
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


# Teacher's "View Submissions" roster: every student currently enrolled in
# the assignment's course offering, with Submitted/Pending status. Only
# students with a submission get a file_url (download link) - avoids a
# separate per-student download endpoint. Paginated via the project's
# standard paginate_queryset (page_size=10 by default) - the DB does the
# actual LIMIT/OFFSET on the Enrollment queryset, not a full-roster fetch
# sliced in Python.
@enforce_permissions('assignments', 'submission')
def assignment_submissions_api(request, assignment_id):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    teacher, error = _get_teacher_or_error(request)
    if error:
        return error

    assignment = Assignment.objects.filter(id = assignment_id, teacher = teacher).first()
    if not assignment:
        return JsonResponse({"error": Messages.ASSIGNMENT_NOT_OWNED}, status = 403)

    enrollments = Enrollment.objects.filter(
        course_offering = assignment.course_offering,
        status__in = [Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
        is_deleted = False,
    ).select_related("student__user").order_by("student__user__name")

    # One cheap lookup query for the whole roster (not per-page, not per-row) -
    # same "single extra query, not N+1" approach the old roster endpoint used.
    submissions_by_student = {
        s.student_id: s for s in Submission.objects.filter(assignment = assignment)
    }

    def serialize(enrollment):
        submission = submissions_by_student.get(enrollment.student_id)
        return {
            "student_id": enrollment.student_id,
            "student_name": enrollment.student.user.name,
            "status": "SUBMITTED" if submission else "PENDING",
            "submitted_at": submission.submitted_at if submission else None,
            "file_url": (
                s3_service.generate_view_url(submission.file_key, expires_in = ASSIGNMENT_FILE_URL_EXPIRY_SECONDS)
                if submission else None
            ),
        }

    return paginate_queryset(request, enrollments, serialize)
