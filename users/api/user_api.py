import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.messages import Messages
from users.models import User
from users.repositories.user_repository import UserRepository
from users.services.user_service import UserService
from users.services.user_validator import UserValidator


user_validator = UserValidator()
user_repository = UserRepository()
user_service = UserService(user_validator, user_repository)


def serialize_user(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "permissions": [],
    }


@csrf_exempt
def user_api(request, user_id=None):
    try:
        if request.method == "GET":
            if user_id is not None:
                user = user_service.get(user_id)
                return JsonResponse(serialize_user(user))

            users = user_service.get_all()
            return JsonResponse(
                [serialize_user(user) for user in users],
                safe=False,
            )

        return JsonResponse(
            {"error": Messages.METHOD_NOT_ALLOWED},
            status=405,
        )

    except User.DoesNotExist:
        return JsonResponse(
            {"error": Messages.USER_NOT_FOUND_BY_ID.format(user_id)},
            status=404,
        )


@csrf_exempt
def register_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status=405,
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
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status=400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )


@csrf_exempt
def login_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status=405,
            )

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        result = user_service.login(data)

        return JsonResponse(
            {
                "user": serialize_user(result["user"]),
                "access": result["access"],
                "refresh": result["refresh"],
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status=400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )


@csrf_exempt
def approve_user_api(request, user_id):
    try:
        if request.method != "PATCH":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status=405,
            )

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
            status=404,
        )


@csrf_exempt
def reject_user_api(request, user_id):
    try:
        if request.method != "PATCH":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status=405,
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
            status=404,
        )


@csrf_exempt
def logout_api(request):
    try:
        if request.method != "POST":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status=405,
            )

        data = json.loads(request.body)

        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        refresh_token = data.get("refresh")

        if not refresh_token:
            raise ValueError(Messages.REFRESH_TOKEN_REQUIRED)

        user_service.logout(refresh_token)

        return HttpResponse(status=204)

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": Messages.INVALID_JSON},
            status=400,
        )

    except ValueError as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )


def pending_users_api(request):
    if request.method != "GET":
        return JsonResponse(
            {"error": Messages.METHOD_NOT_ALLOWED},
            status=405,
        )

    users = user_service.get_pending()

    return JsonResponse(
        [serialize_user(user) for user in users],
        safe=False,
    )


def me_api(request):
    try:
        if request.method != "GET":
            return JsonResponse(
                {"error": Messages.METHOD_NOT_ALLOWED},
                status=405,
            )

        authentication = JWTAuthentication()
        authentication_result = authentication.authenticate(request)

        if authentication_result is None:
            return JsonResponse(
                {"error": "Authentication credentials were not provided."},
                status=401,
            )

        user, _ = authentication_result

        return JsonResponse(
            {"user": serialize_user(user)}
        )

    except Exception:
        return JsonResponse(
            {"error": "Invalid or expired token."},
            status=401,
        )