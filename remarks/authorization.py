from enrollments.models import Enrollment
from remarks.models import Remark


# An enrollment counts as "real" for remark purposes if it isn't soft-deleted
# and the student hasn't dropped the course. A remark can still reference a
# COMPLETED enrollment (e.g. end-of-semester feedback), just not a DROPPED one.
_VALID_ENROLLMENT_STATUSES = [Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]


def teacher_can_access_student_in_offering(teacher, student, course_offering):
    """
    True only if this teacher actually teaches course_offering AND this
    student is (or was) genuinely enrolled in it. Both checks are required -
    teaching the offering isn't enough if the student was never enrolled in
    it, and being enrolled isn't enough if a different teacher teaches it.
    """
    if course_offering.teacher_id != teacher.id:
        return False

    return Enrollment.objects.filter(
        student = student,
        course_offering = course_offering,
        status__in = _VALID_ENROLLMENT_STATUSES,
        is_deleted = False,
    ).exists()


def get_remarks_queryset_for_user(user, student_id = None):
    """
    Role-based READ scoping - the single place that decides which Remark
    rows a given user is allowed to see. Returns Remark.objects.none() for
    anyone who isn't a recognized student or teacher (or superuser).
    """
    if user.is_superuser:
        qs = Remark.objects.all()
        if student_id:
            qs = qs.filter(student_id = student_id)
        return qs

    teacher = getattr(user, "teacher_profile", None)
    if teacher:
        # A teacher only ever sees remarks tied to course offerings they
        # teach. Since Remark.teacher is always set to the offering's
        # teacher at creation time (enforced in the view), filtering by
        # course_offering__teacher is equivalent to "remarks I wrote" plus
        # "remarks written for classes I teach" in one condition.
        qs = Remark.objects.filter(course_offering__teacher = teacher)

        if student_id:
            student = getattr(user, "student_profile", None)  # never set for a teacher; kept for symmetry
            qs = qs.filter(student_id = student_id)
            # A teacher may only query a specific student if that student is
            # actually enrolled in one of the teacher's course offerings -
            # otherwise a teacher could probe for unrelated students by ID
            # and get back an (empty but revealing) 200 instead of a 403.
            is_authorized_for_student = Enrollment.objects.filter(
                student_id = student_id,
                course_offering__teacher = teacher,
                status__in = _VALID_ENROLLMENT_STATUSES,
                is_deleted = False,
            ).exists()
            if not is_authorized_for_student:
                return Remark.objects.none()

        return qs

    student = getattr(user, "student_profile", None)
    if student:
        # A student can only ever see their OWN remarks, and only the ones
        # explicitly marked STUDENT_VISIBLE. This is the rule that keeps
        # PRIVATE remarks (and every other student's remarks) out of reach -
        # regardless of what student_id is passed in the query string.
        return Remark.objects.filter(
            student = student,
            visibility = Remark.Visibility.STUDENT_VISIBLE,
        )

    return Remark.objects.none()


def user_can_view_remark(user, remark):
    return get_remarks_queryset_for_user(user).filter(id = remark.id).exists()
