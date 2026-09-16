from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.messages import Messages


def _get_profile(user, attribute):
    try:
        return getattr(user, attribute)
    except ObjectDoesNotExist:
        return None

def authenticate_request(request):
    try:
        result = JWTAuthentication().authenticate(request)
    except Exception:
        result = None

    if result is None:
        return None, JsonResponse({"error": Messages.AUTH_CREDENTIALS_NOT_PROVIDED}, status = 401)

    user, _ = result

    # Server-side placement gate: a student whose academic placement
    # (Department + Section) hasn't been confirmed by an admin yet must be
    # rejected here even if a crafted request bypasses the frontend's route
    # guard. /users/me/ and /users/onboarding/ intentionally don't use this
    # helper, so the review page can still show identity and poll status.
    if user.role == "student":
        student = _get_profile(user, "student_profile")
        if student and not student.placement_confirmed:
            return None, JsonResponse({"error": Messages.ACADEMIC_PLACEMENT_PENDING}, status = 403)

    return user, None


# Resolves viewer identity for data-scoping; cache layers key on this so
# cached data can never leak across permission scopes.
def get_scope_identity(user):
    if not user.is_authenticated:
        return "anon", None

    if user.is_superuser:
        return "all", None

    user_teacher = _get_profile(user, "teacher_profile")
    if user_teacher:
        return "teacher", user_teacher

    user_student = _get_profile(user, "student_profile")
    if user_student:
        return "student", user_student

    return "none", None


def apply_data_scope(user, queryset, model_type):

    if hasattr(queryset.model, "is_deleted"):
        queryset = queryset.filter(is_deleted = False)

    kind, profile = get_scope_identity(user)

    if kind == "anon":
        return queryset.none()

    if kind == "all":
        return queryset

    user_teacher = profile if kind == "teacher" else None
    user_student = profile if kind == "student" else None

    if model_type == "student":
        if user_teacher:
            return queryset.filter(
                enrollments__course_offering__teacher = user_teacher
            ).distinct()

        if user_student:
            return queryset.filter(id = user_student.id)

        return queryset.none()

    if model_type == "teacher":
        if user_teacher:
            return queryset.filter(id = user_teacher.id)

        if user_student:
            return queryset.filter(
                course_offerings__enrollments__student = user_student
            ).distinct()

        return queryset.none()

    if model_type in ["course_offering", "courseoffering"]:
        if user_teacher:
            return queryset.filter(teacher = user_teacher)

        if user_student:
            return queryset.filter(
                enrollments__student = user_student
            ).distinct()

        return queryset.none()

    if model_type == "enrollment":
        if user_teacher:
            return queryset.filter(
                course_offering__teacher = user_teacher
            )

        if user_student:
            return queryset.filter(student = user_student)

        return queryset.none()

    if model_type == "attendance":
        if user_teacher:
            return queryset.filter(
                enrollment__course_offering__teacher = user_teacher
            )

        if user_student:
            return queryset.filter(
                enrollment__student = user_student
            )

        return queryset.none()

    if model_type in ["course", "department"]:
        return queryset

    return queryset.none()