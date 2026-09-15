from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.messages import Messages


def _get_profile(user, attribute):
    try:
        return getattr(user, attribute)
    except ObjectDoesNotExist:
        return None

#This function authenticates the incoming request
def authenticate_request(request):
    try:
        result = JWTAuthentication().authenticate(request)
    except Exception:
        result = None

    if result is None:
        return None, JsonResponse({"error": Messages.AUTH_CREDENTIALS_NOT_PROVIDED}, status = 401)

    user, _ = result

    # Every "me" endpoint that authenticates through this shared helper
    # (students/attendance/enrollments/assignments/ai_assistant/teachers) is
    # normal student-portal data - none of it should be reachable until an
    # admin has confirmed the student's academic placement (Department +
    # Section). This is the server-side half of that gate: the frontend
    # route guard keeps a pending student on the "Application Under Review"
    # page, but a crafted direct API call must be rejected here regardless.
    # /users/me/ and /users/onboarding/ authenticate independently of this
    # helper and deliberately stay reachable so the review page can still
    # show identity and poll for the admin's decision.
    if user.role == "student":
        student = _get_profile(user, "student_profile")
        if student and not student.placement_confirmed:
            return None, JsonResponse({"error": Messages.ACADEMIC_PLACEMENT_PENDING}, status = 403)

    return user, None


#Returns WHO the viewer is for data-scoping purposes, independent of model_type.
#Every branch of apply_data_scope() picks the viewer identity in exactly this way
#(teacher profile wins over student profile); only the filter expression differs.
#Cache layers key on this so cached data can never leak across permission scopes.
#Returns (kind, profile) where kind is "anon" | "all" | "teacher" | "student" | "none".
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

    #queryset.model means the Django model behind the queryset
    if hasattr(queryset.model, "is_deleted"):
        queryset = queryset.filter(is_deleted = False)

    #Single source of truth for viewer identity, shared with the cache layer.
    kind, profile = get_scope_identity(user)

    if kind == "anon":
        return queryset.none()

    #for admin, No teacher/student restrictions are applied.
    if kind == "all":
        return queryset

    user_teacher = profile if kind == "teacher" else None
    user_student = profile if kind == "student" else None

    if model_type == "student":
        if user_teacher:

        # Only return students connected to courses taught by this teacher.    
            return queryset.filter(
                enrollments__course_offering__teacher = user_teacher
            ).distinct()

        # A student can only see their own Student record.
        if user_student:
            return queryset.filter(id = user_student.id)

    #If the user is neither recognized as Teacher nor Student: Return nothing
        return queryset.none()


    #TEACHER DATA SCOPE
    if model_type == "teacher":
        #A teacher only sees their own profile
        if user_teacher:
            return queryset.filter(id = user_teacher.id)

        #The student can see teachers connected to their enrolled courses
        if user_student:
            return queryset.filter(
                course_offerings__enrollments__student = user_student
            ).distinct()

        return queryset.none()

    
    #COURSE OFFERING DATA SCOPE
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