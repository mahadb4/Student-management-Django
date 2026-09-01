import json
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.messages import Messages
from users.models import User
from users.repositories.user_repository import UserRepository
from users.services.user_service import UserService
from users.services.user_validator import UserValidator
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from students.repositories.student_repository import StudentRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator
from teachers.repositories.teacher_repository import TeacherRepository


user_validator = UserValidator()
user_repository = UserRepository()
user_service = UserService(user_validator, user_repository)

student_service = StudentService(StudentValidator(), StudentRepository())
teacher_service = TeacherService(TeacherValidator(), TeacherRepository())


def _create_own_profile(user, profile):
    # Onboarding profile creation: the email/role identity comes from the
    # already-authenticated User, never from the submitted payload, so a
    # user can only ever create and link a profile for themself.
    if user.role == "student":
        student = student_service.create({**profile, "student_email": user.email})
        student.user = user
        student.save(update_fields = ["user"])
        return student
    if user.role == "teacher":
        teacher = teacher_service.create({**profile, "email": user.email})
        teacher.user = user
        teacher.save(update_fields = ["user"])
        return teacher
    return None

from common.utils import paginate_queryset


def serialize_user(user):
    student = getattr(user, "student_profile", None)
    teacher = getattr(user, "teacher_profile", None)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "permissions": [],
        "student_id": student.id if student else None,
        "teacher_id": teacher.id if teacher else None,
    }


# The one authenticated-identity name shown to the client (Navbar, stored
# localStorage user) - resolved from the linked Student/Teacher profile when
# one exists, since that profile (not the standalone User.name set at
# registration) is the maintained source of truth for a Student/Teacher's
# actual name elsewhere in the app (e.g. GET /students/me/). Only used at
# login/onboarding, where the client's cached identity is (re)issued -
# serialize_user itself is left untouched since it's also used by the
# Admin-facing user list/register/approval responses, which show the
# registered account name regardless of profile linkage.
def resolve_authenticated_display_name(user):
    student = getattr(user, "student_profile", None)
    if student:
        return f"{student.first_name} {student.last_name}"

    teacher = getattr(user, "teacher_profile", None)
    if teacher:
        return f"{teacher.first_name} {teacher.last_name}"

    return user.name


from common.decorators import enforce_permissions


@csrf_exempt
@enforce_permissions('users', 'user')
def user_api(request, user_id = None):
    try:
        if request.method == "GET":
            if user_id is not None:
                user = user_service.get(user_id)
                return JsonResponse(serialize_user(user))

            users = user_service.get_all()
            return paginate_queryset(request, users, serialize_user)

        return JsonResponse(
            {"error": Messages.METHOD_NOT_ALLOWED},
            status = 405,
        )

    except User.DoesNotExist:
        return JsonResponse(
            {"error": Messages.USER_NOT_FOUND_BY_ID.format(user_id)},
            status = 404,
        )


@csrf_exempt
def register_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        user = user_service.register(data)

        return JsonResponse(
            {
                "message": Messages.USER_REGISTRATION_SUCCESSFUL,
                "user": serialize_user(user),
            },
            status = 201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status = 400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status = 400,
        )


@csrf_exempt
def login_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        result = user_service.login(data)

        user_payload = serialize_user(result["user"])
        user_payload["name"] = resolve_authenticated_display_name(result["user"])

        return JsonResponse(
            {
                "user": user_payload,
                "access": result["access"],
                "refresh": result["refresh"],
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status = 400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status = 400,
        )


@csrf_exempt
@enforce_permissions('users', 'user')
def approve_user_api(request, user_id):
    try:
        if request.method != "PATCH":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        # One-click for every role: approval only grants login + Group access.
        # Student/Teacher profile completion happens separately, by the user
        # themself, via the onboarding flow after their first login.
        user = user_service.approve(user_id)

        return JsonResponse(
            {
                "message": Messages.USER_APPROVED_SUCCESSFULLY,
                "user": serialize_user(user),
            }
        )

    except User.DoesNotExist:
        return JsonResponse(
            {"error": Messages.USER_NOT_FOUND_BY_ID.format(user_id)},
            status = 404,
        )


@csrf_exempt
@enforce_permissions('users', 'user')
def reject_user_api(request, user_id):
    try:
        if request.method != "PATCH":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        user = user_service.reject(user_id)

        return JsonResponse(
            {
                "message": Messages.USER_REJECTED_SUCCESSFULLY,
                "user": serialize_user(user),
            }
        )

    except User.DoesNotExist:
        return JsonResponse(
            {"error": Messages.USER_NOT_FOUND_BY_ID.format(user_id)},
            status = 404,
        )


@csrf_exempt
def logout_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        refresh_token = data.get("refresh")

        if not refresh_token:
            raise ValueError(Messages.REFRESH_TOKEN_REQUIRED)

        user_service.logout(refresh_token)

        return HttpResponse(status = 204)

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status = 400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status = 400,
        )


@enforce_permissions('users', 'user')
def pending_users_api(request):
    if request.method != "GET":
        return JsonResponse(
            {"error": Messages.METHOD_NOT_ALLOWED},
            status = 405,
        )

    users = user_service.get_pending()
    return paginate_queryset(request, users, serialize_user)


def me_api(request):
    try:
        if request.method != "GET":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        authentication = JWTAuthentication()
        authentication_result = authentication.authenticate(request)

        if authentication_result is None:
            return JsonResponse(
                {"error": Messages.AUTH_CREDENTIALS_NOT_PROVIDED},
                status = 401,
            )

        user, _ = authentication_result

        return JsonResponse(
            {"user": serialize_user(user)}
        )

    except Exception:
        return JsonResponse(
            {"error": Messages.INVALID_OR_EXPIRED_TOKEN},
            status = 401,
        )


@csrf_exempt
def complete_onboarding_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status = 405,
            )

        authentication = JWTAuthentication()
        authentication_result = authentication.authenticate(request)

        if authentication_result is None:
            return JsonResponse(
                {"error": Messages.AUTH_CREDENTIALS_NOT_PROVIDED},
                status = 401,
            )

        user, _ = authentication_result

        if user.role not in ("student", "teacher"):
            return JsonResponse(
                {"error": Messages.INVALID_REQUEST},
                status = 400,
            )

        if getattr(user, "student_profile", None) or getattr(user, "teacher_profile", None):
            return JsonResponse(
                {"error": Messages.INVALID_REQUEST},
                status = 400,
            )

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        with transaction.atomic():
            _create_own_profile(user, data)

        user_payload = serialize_user(user)
        user_payload["name"] = resolve_authenticated_display_name(user)

        return JsonResponse(
            {"user": user_payload},
            status = 201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status = 400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status = 400,
        )

    except Exception:
        return JsonResponse(
            {"error": Messages.INVALID_OR_EXPIRED_TOKEN},
            status = 401,
        )