"""
Phase 2 of the RAG effort: the remarks retrieval layer.

This module adds no authorization logic of its own. Every call here
delegates entirely to remarks.authorization.get_remarks_queryset_for_user,
which Phase 1 already proved scopes correctly for students, teachers,
superusers, and unauthorized/anonymous users alike. This module's only job
is to shape that already-authorized queryset into a small, LLM-context-
ready list of dicts.
"""
from remarks.authorization import get_remarks_queryset_for_user


def get_remark_context_for_user(user, *, student_id=None, limit=20):
    """
    Returns the authorized remarks for `user` as a list of small dicts,
    most recent first.

    Authorization is entirely delegated to get_remarks_queryset_for_user -
    this function adds no filtering of its own beyond ordering and limit.
    `student_id` is passed straight through, inheriting that function's
    existing anti-enumeration behavior (empty result for an unauthorized
    probe) unchanged.
    """
    qs = get_remarks_queryset_for_user(user, student_id=student_id)
    qs = qs.select_related("teacher__user", "course_offering__course").order_by("-created_at")[:limit]

    return [
        {
            "id": remark.id,
            "text": remark.remark_text,
            "teacher_name": remark.teacher.user.name,
            "course_name": remark.course_offering.course.name,
            "visibility": remark.visibility,
            "created_at": remark.created_at.isoformat(),
        }
        for remark in qs
    ]
