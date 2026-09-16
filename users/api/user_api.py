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
from students.cache.student_cache import StudentCache
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator
from students.repositories.student_repository import StudentRepository
from teachers.cache.teacher_cache import TeacherCache
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator
from teachers.repositories.teacher_repository import TeacherRepository
from common.cache.cache_service import CacheService


user_validator = UserValidator()
user_repository = UserRepository()
user_service = UserService(user_validator, user_repository)

#Onboarding creates Student/Teacher profiles through these services, so they must
#be given the same entity caches the main APIs use - a raw CacheService has no
#invalidate_on_write() and would fail at write time, and a separate cache instance
#would leave the list caches stale after a profile is created.
student_service = StudentService(StudentValidator(), StudentRepository(), StudentCache(CacheService()))
teacher_service = TeacherService(TeacherValidator(), TeacherRepository(), TeacherCache(CacheService()))


#Fields a student can never set for themself during onboarding, including by
#crafting the request body - Department/Section are admin-assigned academic
#placement, decided AFTER onboarding via the admin-only PATCH
#/students/<id>/ path (see StudentValidator.validate() for the server-side
#rule that placement_confirmed can only ever become True there, and only
#once both are set). A brand-new Student is therefore always created with
#department/section null and placement_confirmed False regardless of what
#the student submits - that's what puts them into academic review instead
#of the dashboard (see complete_onboarding_api's response and
#App.tsx's ProtectedRoute on the frontend).
STUDENT_ONBOARDING_BLOCKED_FIELDS = ("department", "section", "placement_confirmed")


def _create_own_profile(user, profile):
    # Email/role come from the authenticated User, not the payload, so a
    # user can only create a profile for themself.
    if user.role == "student":
        student_profile = {
            key: value for key, value in profile.items()
            if key not in STUDENT_ONBOARDING_BLOCKED_FIELDS
        }
        return student_service.create({**student_profile, "student_email": user.email}, user = user)
    if user.role == "teacher":
        return teacher_service.create({**profile, "email": user.email}, user = user)
    return None

from common.utils import paginate_queryset
from users.mappers.user_mapper import UserMapper


# Display name shown to the client (Navbar). Used at login/onboarding.
def resolve_authenticated_display_name(user):
    return user.name


from common.decorators import enforce_permissions


@csrf_exempt
@enforce_permissions('users', 'user')
def user_api(request, user_id = None):
    try:
        if request.method == "GET":
            if user_id is not None:
                user = user_service.get(user_id)
                return JsonResponse(UserMapper.to_detail_dto(user))

            users = user_service.get_all()
            return paginate_queryset(request, users, UserMapper.to_list_dto)

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
                "user": UserMapper.to_detail_dto(user),
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

        user_payload = UserMapper.to_identity_dto(result["user"])
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
                "user": UserMapper.to_detail_dto(user),
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
                "user": UserMapper.to_detail_dto(user),
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
    return paginate_queryset(request, users, UserMapper.to_list_dto)


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
            {"user": UserMapper.to_detail_dto(user)}
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

        user_payload = UserMapper.to_detail_dto(user)
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