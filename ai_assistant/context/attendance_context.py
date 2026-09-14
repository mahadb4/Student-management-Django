"""
Phase 10B: structured Attendance context - the "SQL side" of the hybrid
assistant. Attendance is relational/countable data, so it is never
embedded or semantically searched; it's aggregated directly from the
database and handed to Gemini as an already-computed summary. Gemini's
job here is explanation, not arithmetic.

This module performs no authorization of its own beyond calling the
existing common.permissions.apply_data_scope("attendance") - the exact
same function every other Attendance view in this project already uses.
"""
from attendance.models import Attendance
from common.permissions import apply_data_scope


def build_attendance_context(user, course_offering_id=None):
    """
    Returns:
        {
            "prompt_item": {...},  # Option A compatibility wrapper for
                                    # GeminiGenerationService's existing
                                    # {teacher_name, course_name, created_at,
                                    # text} item shape (Phase 7, unchanged).
                                    # created_at is deliberately "" - this
                                    # is a computed summary, not a dated
                                    # record, and must never look like one
                                    # to the model.
            "sources": [...],      # honest, domain-specific source entries
                                    # for the frontend - {"type": "attendance",
                                    # "course_name", "detail"} per course.
        }

    `course_offering_id` (Phase 10E), if given, narrows the ALREADY-
    authorized attendance queryset to just that offering - applied AFTER
    apply_data_scope, never instead of it.
    """
    qs = apply_data_scope(user, Attendance.objects.all(), "attendance").select_related(
        "enrollment__course_offering__course"
    )
    if course_offering_id:
        qs = qs.filter(enrollment__course_offering_id=course_offering_id)

    total = present = late = absent = 0
    by_course = {}

    for record in qs:
        total += 1
        course_name = (
            record.enrollment.course_offering.course.name if record.enrollment_id else "Unknown course"
        )
        stats = by_course.setdefault(course_name, {"total": 0, "present": 0, "late": 0, "absent": 0})
        stats["total"] += 1

        if record.status == Attendance.Status.PRESENT:
            present += 1
            stats["present"] += 1
        elif record.status == Attendance.Status.LATE:
            late += 1
            stats["late"] += 1
        elif record.status == Attendance.Status.ABSENT:
            absent += 1
            stats["absent"] += 1

    sources = []

    if total == 0:
        summary_text = "This student doesn't have any attendance records yet."
    else:
        overall_percentage = round((present / total) * 100)
        lines = [
            f"Overall: {total} total classes, {present} present, {late} late, {absent} absent "
            f"({overall_percentage}% attendance).",
            "By course:",
        ]
        for course_name, stats in by_course.items():
            course_percentage = round((stats["present"] / stats["total"]) * 100) if stats["total"] else 0
            lines.append(
                f"- {course_name}: {stats['present']}/{stats['total']} present ({course_percentage}%), "
                f"{stats['late']} late, {stats['absent']} absent."
            )
            sources.append({
                "type": "attendance",
                "course_name": course_name,
                "detail": f"{course_percentage}% present ({stats['present']}/{stats['total']})",
            })
        summary_text = "\n".join(lines)

    prompt_item = {
        "teacher_name": "Attendance Summary",
        "course_name": "Overall",
        "created_at": "",
        "text": summary_text,
    }

    return {"prompt_item": prompt_item, "sources": sources}
