"""
Structured Courses/Enrollments context. Never embedded or semantically
searched. Authorization is delegated to common.permissions.apply_data_scope.

Only ACTIVE enrollments are included, reflecting the student's current
academic situation; DROPPED/COMPLETED are deliberately excluded.

The instructor shown is always CourseOffering.teacher (the actual teacher of
record for this offering), never Course.teacher, which can be stale.
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
            "prompt_item": {...},  # compatibility wrapper for
                                    # GeminiGenerationService's item shape.
            "sources": [...],      # {"type": "course", "course_name",
                                    # "course_code", "teacher_name",
                                    # "section_name"} per active enrollment.
                                    # No internal enrollment/offering IDs.
        }

    `course_offering_id`, if given, narrows the already-authorized queryset
    to just that offering - it never replaces the authorization check.
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
