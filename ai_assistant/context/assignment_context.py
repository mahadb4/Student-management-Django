"""
Structured Assignments context. Assignments are relational/countable data,
never embedded or semantically searched. Authorization is delegated to
assignments.authorization.get_assignments_queryset_for_user.

Status is derived, never stored:
    submitted -> a Submission row exists for this student+assignment
    overdue   -> no submission and due_at is in the past
    pending   -> no submission and due_at is still in the future
"submitted" never implies graded/reviewed - no such field exists in this schema.

Attachment content is never read or extracted - only whether attachment_key
is set is surfaced.
"""
from django.utils import timezone

from assignments.authorization import get_assignments_queryset_for_user


def build_assignment_context(user, course_offering_id=None):
    """
    Returns:
        {
            "prompt_item": {...},  # compatibility wrapper for
                                    # GeminiGenerationService's item shape.
            "sources": [...],      # {"type": "assignment", "title",
                                    # "course_name", "due_at", "status",
                                    # "attachment_available"} per assignment.
        }

    `course_offering_id`, if given, is threaded into
    get_assignments_queryset_for_user's own existing parameter.
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
