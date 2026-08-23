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
    # Shared by every /me/ endpoint: returns (user, None) on success, or
    # (None, error_response) - callers just do `if error: return error`.
    try:
        result = JWTAuthentication().authenticate(request)
    except Exception:
        result = None

    if result is None:
        return None, JsonResponse({"error": Messages.AUTH_CREDENTIALS_NOT_PROVIDED}, status=401)

    user, _ = result
    return user, None


def apply_data_scope(user, queryset, model_type):
    if hasattr(queryset.model, "is_deleted"):
        queryset = queryset.filter(is_deleted=False)

    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    user_student = _get_profile(user, "student_profile")
    user_teacher = _get_profile(user, "teacher_profile")

    if model_type == "student":
        if user_teacher:
            return queryset.filter(
                enrollments__course_offering__teacher=user_teacher
            ).distinct()

        if user_student:
            return queryset.filter(id=user_student.id)

        return queryset.none()

    if model_type == "teacher":
        if user_teacher:
            return queryset.filter(id=user_teacher.id)

        if user_student:
            return queryset.filter(
                course_offerings__enrollments__student=user_student
            ).distinct()

        return queryset.none()

    if model_type in ["course_offering", "courseoffering"]:
        if user_teacher:
            return queryset.filter(teacher=user_teacher)

        if user_student:
            return queryset.filter(
                enrollments__student=user_student
            ).distinct()

        return queryset.none()

    if model_type == "enrollment":
        if user_teacher:
            return queryset.filter(
                course_offering__teacher=user_teacher
            )

        if user_student:
            return queryset.filter(student=user_student)

        return queryset.none()

    if model_type == "attendance":
        if user_teacher:
            return queryset.filter(
                enrollment__course_offering__teacher=user_teacher
            )

        if user_student:
            return queryset.filter(
                enrollment__student=user_student
            )

        return queryset.none()

    if model_type in ["course", "department"]:
        return queryset

    return queryset.none()