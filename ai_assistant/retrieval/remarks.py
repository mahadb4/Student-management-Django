"""
The remarks retrieval layer. Authorization is entirely delegated to
remarks.authorization.get_remarks_queryset_for_user; this module only shapes
the already-authorized queryset into a small, LLM-context-ready list of dicts.
"""
from remarks.authorization import get_remarks_queryset_for_user
from remarks.models import VISIBILITY_CODE_TO_LABEL


def get_remark_context_for_user(user, *, student_id=None, limit=20):
    """
    Returns the authorized remarks for `user` as a list of small dicts,
    most recent first.
    """
    qs = get_remarks_queryset_for_user(user, student_id=student_id)
    qs = qs.select_related("teacher__user", "course_offering__course").order_by("-created_at")[:limit]

    return [
        {
            "id": remark.id,
            "text": remark.remark_text,
            "teacher_name": remark.teacher.user.name,
            "course_name": remark.course_offering.course.name,
            "visibility": VISIBILITY_CODE_TO_LABEL[remark.visibility],
            "created_at": remark.created_at.isoformat(),
        }
        for remark in qs
    ]
