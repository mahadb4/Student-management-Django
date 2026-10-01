from enrollments.models import Enrollment
from assignments.models import Assignment

_VALID_ENROLLMENT_STATUSES = [Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]


def teacher_owns_offering(teacher, course_offering):
    return course_offering.teacher_id == teacher.id


def student_enrolled_in_offering(student, course_offering):
    return Enrollment.objects.filter(
        student = student,
        course_offering = course_offering,
        status__in = _VALID_ENROLLMENT_STATUSES,
        is_deleted = False,
    ).exists()


def get_assignments_queryset_for_user(user, course_offering_id = None):
    """
    Role-based READ scoping - the single place that decides which
    Assignment rows a given user is allowed to see. Mirrors
    remarks/authorization.py's get_remarks_queryset_for_user.
    """
    if user.is_superuser:
        qs = Assignment.objects.all()
        if course_offering_id:
            qs = qs.filter(course_offering_id = course_offering_id)
        return qs

    teacher = getattr(user, "teacher_profile", None)
    if teacher:
        qs = Assignment.objects.filter(course_offering__teacher = teacher)
        if course_offering_id:
            qs = qs.filter(course_offering_id = course_offering_id)
        return qs

    student = getattr(user, "student_profile", None)
    if student:
        qs = Assignment.objects.filter(
            course_offering__enrollments__student = student,
            course_offering__enrollments__status__in = _VALID_ENROLLMENT_STATUSES,
            course_offering__enrollments__is_deleted = False,
        ).distinct()
        if course_offering_id:
            qs = qs.filter(course_offering_id = course_offering_id)
        return qs

    return Assignment.objects.none()
