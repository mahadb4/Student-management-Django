import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from teachers.models import Teacher
from teachers.repositories.teacher_repository import TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator

teacher_validator = TeacherValidator()
teacher_repository = TeacherRepository()
teacher_service = TeacherService(teacher_validator, teacher_repository)

def serialize_teacher(teacher):
    return {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "employee_id": teacher.employee_id,
        "email": teacher.email,
        "phone_number": teacher.phone_number,
        "department": teacher.department_id,
        "designation": teacher.designation,
        "qualification": teacher.qualification,
        "gender": teacher.gender,
        "date_of_birth": teacher.date_of_birth,
        "date_of_joining": teacher.date_of_joining,
        "salary": teacher.salary,
        "address": teacher.address,
        "is_active": teacher.is_active,
        "created_at": teacher.created_at,
        "updated_at": teacher.updated_at,
    }

@csrf_exempt
def teacher_api(request, teacher_id = None):
    try:
        if request.method == "GET":
            if teacher_id is not None:
                return JsonResponse(serialize_teacher(teacher_service.get(teacher_id)))

            return JsonResponse([serialize_teacher(teacher) for teacher in teacher_service.get_all()], safe = False)

        if request.method == "POST":
            teacher = teacher_service.create(json.loads(request.body))
            return JsonResponse(serialize_teacher(teacher), status = 201)

        if request.method == "PUT":
            if teacher_id is None:
                return JsonResponse({"error": Messages.TEACHER_ID_REQUIRED}, status = 400)

            teacher = teacher_service.update(teacher_id, json.loads(request.body))
            return JsonResponse(serialize_teacher(teacher))

        if request.method == "PATCH":
            if teacher_id is None:
                return JsonResponse({"error": Messages.TEACHER_ID_REQUIRED}, status = 400)

            teacher = teacher_service.update(teacher_id, json.loads(request.body), partial = True)
            return JsonResponse(serialize_teacher(teacher))

        if request.method == "DELETE":
            if teacher_id is None:
                return JsonResponse({"error": Messages.TEACHER_ID_REQUIRED}, status = 400)

            teacher_service.delete(teacher_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Teacher.DoesNotExist:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND_BY_ID.format(teacher_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.TEACHER_CANNOT_BE_DELETED.format(teacher_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)