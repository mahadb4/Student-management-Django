"""
Phase 10C: structured Assignments context - the second "SQL side" source
of the hybrid assistant, alongside Attendance (Phase 10B). Assignments are
relational/countable data, never embedded or semantically searched.

This module performs no authorization of its own beyond calling the
existing assignments.authorization.get_assignments_queryset_for_user -
the exact same function the real /api/assignments/ endpoint uses.

Student-focused only, per Phase 10C scope: a caller with no student_profile
(a teacher, or anyone else) gets a safe "not available" response rather
than any teacher-side assignment analytics - that's explicitly deferred,
not silently built here.

Status is derived, never stored, from two real fields:
    submitted -> a Submission row exists for this student+assignment
    overdue   -> no submission AND due_at is in the past
    pending   -> no submission AND due_at is still in the future
"submitted" never implies graded/reviewed - no such field exists anywhere
in this schema, and this module never claims otherwise.

Attachment content is never read, extracted, or sent anywhere - only
whether attachment_key is set (a plain presence/absence boolean) is
surfaced, matching the project's confirmed lack of any text-extraction
pipeline for S3 attachments.
"""
from django.utils import timezone

from assignments.authorization import get_assignments_queryset_for_user


def build_assignment_context(user, course_offering_id=None):
    """
    Returns:
        {
            "prompt_item": {...},  # Option A compatibility wrapper for
                                    # GeminiGenerationService's existing
                                    # item shape (Phase 7, unchanged).
            "sources": [...],      # {"type": "assignment", "title",
                                    # "course_name", "due_at", "status",
                                    # "attachment_available"} per assignment.
        }

    `course_offering_id` (Phase 10E), if given, is threaded straight into
    get_assignments_queryset_for_user's own existing parameter - that
    function already supported this narrowing; it was simply unused here
    until now. No authorization logic changes.
    """
    student = getattr(user, "student_profile", None)
    if not student:
        return {
            "prompt_item": {
                "teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "",
                "text": "No assignment information is available for this account.",
            },
            "sources": [],
        }

    qs = get_assignments_queryset_for_user(user, course_offering_id=course_offering_id).select_related(
        "course_offering__course"
    )
    now = timezone.now()

    sources = []
    lines = []
    counts = {"overdue": 0, "pending": 0, "submitted": 0}

    for assignment in qs.order_by("due_at"):
        has_submission = assignment.submissions.filter(student=student).exists()
        if has_submission:
            status = "submitted"
        elif assignment.due_at < now:
            status = "overdue"
        else:
            status = "pending"
        counts[status] += 1

        attachment_available = bool(assignment.attachment_key)
        note = " Has an attachment." if attachment_available else ""
        lines.append(
            f"- \"{assignment.title}\" ({assignment.course_offering.course.name}), "
            f"due {assignment.due_at.isoformat()}, status: {status}.{note}"
        )
        sources.append({
            "type": "assignment",
            "title": assignment.title,
            "course_name": assignment.course_offering.course.name,
            "due_at": assignment.due_at.isoformat(),
            "status": status,
            "attachment_available": attachment_available,
        })

    if not sources:
        summary_text = "This student doesn't currently have any assignments recorded."
    else:
        summary_text = "\n".join([
            f"{len(sources)} total assignments "
            f"({counts['overdue']} overdue, {counts['pending']} pending, {counts['submitted']} submitted). "
            f"\"Submitted\" means a file was uploaded - it does not mean graded or reviewed, since this "
            f"system does not track grades.",
            *lines,
        ])

    prompt_item = {
        "teacher_name": "Assignments Summary", "course_name": "Overall", "created_at": "",
        "text": summary_text,
    }

    return {"prompt_item": prompt_item, "sources": sources}
