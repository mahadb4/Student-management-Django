import json
from django.http import JsonResponse
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
    student_id = getattr(user, 'student_profile', None)
    teacher_id = getattr(user, 'teacher_profile', None)
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "permissions": list(user.get_all_permissions()),
        "student_id": student_id.id if student_id else None,
        "teacher_id": teacher_id.id if teacher_id else None,
    }


@csrf_exempt
def register_api(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

        user = user_service.register(json.loads(request.body))

        return JsonResponse({
            "success": True,
            "user": serialize_user(user),
        }, status = 201)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
def login_api(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

        result = user_service.login(json.loads(request.body))

        return JsonResponse({
            "success": True,
            "user": serialize_user(result["user"]),
            "access": result["access"],
            "refresh": result["refresh"],
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


def user_api(request, user_id = None):
    try:
        if request.method == "GET":
            if user_id is not None:
                return JsonResponse(serialize_user(user_service.get(user_id)))

            return JsonResponse(
                [serialize_user(user) for user in user_service.get_all()],
                safe = False,
            )

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except User.DoesNotExist:
        return JsonResponse({"error": Messages.USER_NOT_FOUND}, status = 404)


def pending_users_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    users = user_service.get_pending()

    return JsonResponse(
        [serialize_user(user) for user in users],
        safe = False,
    )


@csrf_exempt
def approve_user_api(request, user_id):
    try:
        if request.method != "PATCH":
            return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

        user = user_service.approve(user_id)

        return JsonResponse({
            "success": True,
            "user": serialize_user(user),
        })

    except User.DoesNotExist:
        return JsonResponse({"error": Messages.USER_NOT_FOUND}, status = 404)


@csrf_exempt
def reject_user_api(request, user_id):
    try:
        if request.method != "PATCH":
            return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

        user = user_service.reject(user_id)

        return JsonResponse({
            "success": True,
            "user": serialize_user(user),
        })

    except User.DoesNotExist:
        return JsonResponse({"error": Messages.USER_NOT_FOUND}, status = 404)


@csrf_exempt
def logout_api(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

        data = json.loads(request.body)

        if not data.get("refresh"):
            raise ValueError(Messages.REFRESH_TOKEN_REQUIRED)

        user_service.logout(data["refresh"])

        return JsonResponse({
            "success": True,
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


def me_api(request):
    try:
        if request.method != "GET":
            return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

        authentication = JWTAuthentication()
        authentication_result = authentication.authenticate(request)

        if authentication_result is None:
            return JsonResponse({"error": Messages.AUTH_CREDENTIALS_NOT_PROVIDED}, status = 401)

        user, token = authentication_result

        return JsonResponse({
            "success": True,
            "user": serialize_user(user),
        })

    except Exception:
        return JsonResponse({"error": Messages.INVALID_OR_EXPIRED_TOKEN}, status = 401)