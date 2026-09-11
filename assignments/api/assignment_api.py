import json
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from common.constants import ASSIGNMENT_FILE_CONTENT_TYPES, ASSIGNMENT_FILE_URL_EXPIRY_SECONDS, MAX_ASSIGNMENT_FILE_SIZE_BYTES
from common.decorators import enforce_permissions
from common.messages import Messages
from common.services.s3_service import S3Service
from common.utils import build_paginated_payload, extension_for_allowed_content_type, paginate_queryset, resolve_pagination_params
from assignments.authorization import get_assignments_queryset_for_user, teacher_owns_offering
from assignments.models import Assignment
from course_offerings.models import CourseOffering
from enrollments.models import Enrollment

s3_service = S3Service()


def _get_teacher_or_error(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not teacher:
        return None, JsonResponse({"error": Messages.ASSIGNMENT_TEACHER_NOT_FOUND}, status = 400)
    return teacher, None


def _parse_due_at(value):
    if not value:
        raise ValueError(Messages.ASSIGNMENT_DUE_AT_REQUIRED)

    parsed = parse_datetime(value)
    if not parsed:
        raise ValueError(Messages.ASSIGNMENT_DUE_AT_INVALID)

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)

    return parsed


# Teacher list row - the course/class context is already known client-side
# (this is a course-scoped page), so only what the UI's assignment table
# actually shows: title, due date, and a submitted/pending count computed
# server-side (never every enrollment + every submission shipped to the
# frontend just to be counted there).
def _serialize_assignment_for_teacher_list(assignment):
    enrolled_count = Enrollment.objects.filter(
        course_offering_id = assignment.course_offering_id,
        status__in = [Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
        is_deleted = False,
    ).count()
    submitted_count = assignment.submissions.count()
    return {
        "id": assignment.id,
        "title": assignment.title,
        "due_at": assignment.due_at,
        "submitted_count": submitted_count,
        "pending_count": max(enrolled_count - submitted_count, 0),
    }


def _attachment_url(assignment):
    if not assignment.attachment_key:
        return None
    return s3_service.generate_view_url(assignment.attachment_key, expires_in = ASSIGNMENT_FILE_URL_EXPIRY_SECONDS)


# Teacher detail - used to prefill the Edit form. course_offering isn't
# included: it's fixed at creation and never edited.
def _serialize_assignment_for_teacher_detail(assignment):
    return {
        "id": assignment.id,
        "title": assignment.title,
        "description": assignment.description,
        "due_at": assignment.due_at,
        "attachment_url": _attachment_url(assignment),
    }


# Student view - one assignment already carries its own course context
# (aggregated across multiple classes), plus the student's own submission
# status resolved server-side so the frontend never has to cross-reference
# a separate submissions call.
def _serialize_assignment_for_student(assignment, student):
    submission = assignment.submissions.filter(student = student).first()
    return {
        "id": assignment.id,
        "title": assignment.title,
        "description": assignment.description,
        "due_at": assignment.due_at,
        "attachment_url": _attachment_url(assignment),
        "course_name": assignment.course_offering.course.name,
        "course_code": assignment.course_offering.course.code,
        "status": "SUBMITTED" if submission else "PENDING",
        "submitted_at": submission.submitted_at if submission else None,
    }


@csrf_exempt
@enforce_permissions('assignments', 'assignment')
def assignment_api(request, assignment_id = None):
    try:
        if request.method == "GET":
            course_offering_id = request.GET.get("course_offering")
            scoped_qs = get_assignments_queryset_for_user(request.user, course_offering_id).select_related(
                "course_offering__course"
            )

            teacher = getattr(request.user, "teacher_profile", None)
            student = getattr(request.user, "student_profile", None)

            if assignment_id is not None:
                assignment = scoped_qs.filter(id = assignment_id).first()
                if not assignment:
                    return JsonResponse({"error": Messages.ASSIGNMENT_NOT_FOUND_BY_ID.format(assignment_id)}, status = 404)

                if teacher:
                    return JsonResponse(_serialize_assignment_for_teacher_detail(assignment))
                return JsonResponse(_serialize_assignment_for_student(assignment, student))

            if teacher:
                page_number, page_size = resolve_pagination_params(request)
                payload = build_paginated_payload(
                    scoped_qs.order_by("-created_at"), page_number, page_size, _serialize_assignment_for_teacher_list
                )

                # The teacher's per-class Assignments page needs the class name
                # for its header. It is attached here - only when the caller
                # actually teaches this offering - so that page never has to
                # fetch the whole /teachers/me/courses/ list just to resolve
                # one label. Only the three fields the header renders.
                if course_offering_id:
                    offering = CourseOffering.objects.filter(
                        id = course_offering_id, teacher = teacher,
                    ).select_related("course", "section").first()

                    if offering:
                        payload["course"] = {
                            "id": offering.id,
                            "course_name": offering.course.name,
                            "course_code": offering.course.code,
                            "section_name": offering.section.name if offering.section_id else None,
                        }

                return JsonResponse(payload)

            return paginate_queryset(
                request, scoped_qs.order_by("due_at"), lambda a: _serialize_assignment_for_student(a, student)
            )

        if request.method == "POST":
            teacher, error = _get_teacher_or_error(request)
            if error:
                return error

            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            course_offering_id = data.get("course_offering")
            title = (data.get("title") or "").strip()
            description = (data.get("description") or "").strip()

            if not course_offering_id:
                raise ValueError(Messages.ASSIGNMENT_COURSE_OFFERING_REQUIRED)
            if not title:
                raise ValueError(Messages.ASSIGNMENT_TITLE_REQUIRED)

            due_at = _parse_due_at(data.get("due_at"))

            course_offering = CourseOffering.objects.filter(id = course_offering_id).first()
            if not course_offering:
                raise ValueError(Messages.INVALID_COURSE_OFFERING.format(course_offering_id))

            # Core authorization rule: a teacher may only create an
            # assignment for a course offering they actually teach - checked
            # in the backend before any data is written.
            if not teacher_owns_offering(teacher, course_offering):
                return JsonResponse({"error": Messages.ASSIGNMENT_NOT_AUTHORIZED_FOR_OFFERING}, status = 403)

            assignment = Assignment.objects.create(
                course_offering = course_offering,
                teacher = teacher,
                title = title,
                description = description,
                due_at = due_at,
            )
            return JsonResponse(_serialize_assignment_for_teacher_detail(assignment), status = 201)

        if request.method in ("PUT", "PATCH"):
            if assignment_id is None:
                return JsonResponse({"error": Messages.ASSIGNMENT_ID_REQUIRED}, status = 400)

            teacher, error = _get_teacher_or_error(request)
            if error:
                return error

            assignment = Assignment.objects.filter(id = assignment_id).first()
            if not assignment:
                return JsonResponse({"error": Messages.ASSIGNMENT_NOT_FOUND_BY_ID.format(assignment_id)}, status = 404)

            if assignment.teacher_id != teacher.id:
                return JsonResponse({"error": Messages.ASSIGNMENT_NOT_OWNED}, status = 403)

            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            if "title" in data:
                title = (data.get("title") or "").strip()
                if not title:
                    raise ValueError(Messages.ASSIGNMENT_TITLE_REQUIRED)
                assignment.title = title

            if "description" in data:
                assignment.description = (data.get("description") or "").strip()

            if "due_at" in data:
                assignment.due_at = _parse_due_at(data.get("due_at"))

            assignment.save()
            return JsonResponse(_serialize_assignment_for_teacher_detail(assignment))

        if request.method == "DELETE":
            if assignment_id is None:
                return JsonResponse({"error": Messages.ASSIGNMENT_ID_REQUIRED}, status = 400)

            teacher, error = _get_teacher_or_error(request)
            if error:
                return error

            assignment = Assignment.objects.filter(id = assignment_id).first()
            if not assignment:
                return JsonResponse({"error": Messages.ASSIGNMENT_NOT_FOUND_BY_ID.format(assignment_id)}, status = 404)

            if assignment.teacher_id != teacher.id:
                return JsonResponse({"error": Messages.ASSIGNMENT_NOT_OWNED}, status = 403)

            assignment.delete()
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('assignments', 'assignment')
def assignment_attachment_upload_url_api(request, assignment_id):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    teacher, error = _get_teacher_or_error(request)
    if error:
        return error

    assignment = Assignment.objects.filter(id = assignment_id, teacher = teacher).first()
    if not assignment:
        return JsonResponse({"error": Messages.ASSIGNMENT_NOT_OWNED}, status = 403)

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
        key = f"assignments/{assignment.id}/attachment.{extension}"
        upload_url = s3_service.generate_upload_url(key, content_type, expires_in = ASSIGNMENT_FILE_URL_EXPIRY_SECONDS)
        return JsonResponse({"upload_url": upload_url, "key": key, "content_type": content_type})

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
@enforce_permissions('assignments', 'assignment')
def assignment_attachment_confirm_api(request, assignment_id):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    teacher, error = _get_teacher_or_error(request)
    if error:
        return error

    assignment = Assignment.objects.filter(id = assignment_id, teacher = teacher).first()
    if not assignment:
        return JsonResponse({"error": Messages.ASSIGNMENT_NOT_OWNED}, status = 403)

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError(Messages.ASSIGNMENT_FILE_KEY_REQUIRED)

        expected_prefix = f"assignments/{assignment.id}/attachment."
        if not key.startswith(expected_prefix):
            raise ValueError(Messages.ASSIGNMENT_FILE_KEY_MISMATCH)

        metadata = s3_service.head_object(key)
        if metadata is None:
            raise ValueError(Messages.ASSIGNMENT_FILE_UPLOAD_NOT_FOUND)

        content_length = metadata.get("content_length") or 0
        if content_length > MAX_ASSIGNMENT_FILE_SIZE_BYTES:
            s3_service.delete_object(key)
            raise ValueError(Messages.ASSIGNMENT_FILE_TOO_LARGE.format(MAX_ASSIGNMENT_FILE_SIZE_BYTES // (1024 * 1024)))

        old_key = assignment.attachment_key
        assignment.attachment_key = key
        assignment.save(update_fields = ["attachment_key", "updated_at"])

        if old_key and old_key != key:
            s3_service.delete_object(old_key)

        return JsonResponse({"attachment_url": _attachment_url(assignment)})

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)
