"""
Phase 10D/10E: structured Courses/Enrollments context - the third "SQL
side" source of the hybrid assistant, alongside Attendance (10B) and
Assignments (10C). Never embedded or semantically searched.

This module performs no authorization of its own beyond calling the
existing common.permissions.apply_data_scope("enrollment") - the same
function Attendance (10B) already reuses.

Student-focused only: a caller with no student_profile gets a safe "not
available" response, same pattern as assignment_context.

Scope decision (approved): only ACTIVE enrollments are included - this
reflects the student's CURRENT academic situation. DROPPED and COMPLETED
enrollments are deliberately excluded here; a historical/"what have I
completed" capability would be a separate, later addition, not silently
included in this context.

The instructor shown is always CourseOffering.teacher (the actual teacher
of record for the specific offering the student is enrolled in) - never
Course.teacher, which is a separate, potentially different/stale field on
the Course template itself.

Phase 10E adds an optional course_offering_id narrowing parameter, applied
AFTER the existing authorized queryset (never instead of it), plus
get_active_enrollments_for_user - the single authorized source both
build_course_context and ai_assistant.course_resolution.resolve_mentioned_
course read from, so course-name resolution's search space can never
include a course the student isn't already allowed to see.
"""
from common.permissions import apply_data_scope
from enrollments.models import Enrollment


def get_active_enrollments_for_user(user):
    """
    The authenticated student's own ACTIVE enrollments (queryset),
    select_related for course/teacher/section access without extra
    queries. Empty queryset for anyone without a student_profile.
    """
    student = getattr(user, "student_profile", None)
    if not student:
        return Enrollment.objects.none()

    return apply_data_scope(user, Enrollment.objects.all(), "enrollment").filter(
        status=Enrollment.Status.ACTIVE,
    ).select_related("course_offering__course", "course_offering__teacher__user", "course_offering__section")


def build_course_context(user, course_offering_id=None):
    """
    Returns:
        {
            "prompt_item": {...},  # Option A compatibility wrapper for
                                    # GeminiGenerationService's existing
                                    # item shape (Phase 7, unchanged).
            "sources": [...],      # {"type": "course", "course_name",
                                    # "course_code", "teacher_name",
                                    # "section_name"} per active enrollment
                                    # (or the single one, if narrowed).
                                    # No internal enrollment/offering IDs.
        }

    `course_offering_id`, if given, narrows the ALREADY-authorized active-
    enrollments queryset to just that offering - it never replaces or
    widens the authorization check itself.
    """
    student = getattr(user, "student_profile", None)
    if not student:
        return {
            "prompt_item": {
                "teacher_name": "Courses Summary", "course_name": "Overall", "created_at": "",
                "text": "No course information is available for this account.",
            },
            "sources": [],
        }

    qs = get_active_enrollments_for_user(user)
    if course_offering_id:
        qs = qs.filter(course_offering_id=course_offering_id)

    sources = []
    lines = []

    for enrollment in qs:
        offering = enrollment.course_offering
        teacher = offering.teacher
        teacher_name = f"{teacher.effective_first_name} {teacher.effective_last_name}" if teacher else None
        section_name = offering.section.name if offering.section_id else None

        sources.append({
            "type": "course",
            "course_name": offering.course.name,
            "course_code": offering.course.code,
            "teacher_name": teacher_name,
            "section_name": section_name,
        })
        teacher_part = f", taught by {teacher_name}" if teacher_name else ""
        lines.append(f"- {offering.course.name} ({offering.course.code}){teacher_part}.")

    if not sources:
        summary_text = "This student is not currently enrolled in any active courses."
    else:
        summary_text = "\n".join([
            f"Currently enrolled in {len(sources)} active course(s):",
            *lines,
        ])

    prompt_item = {
        "teacher_name": "Courses Summary", "course_name": "Overall", "created_at": "",
        "text": summary_text,
    }

    return {"prompt_item": prompt_item, "sources": sources}
