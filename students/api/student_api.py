import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.messages import Messages
from students.models import Student
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator

student_validator = StudentValidator()
student_repository = StudentRepository()
student_service = StudentService(student_validator, student_repository)

def serialize_student(student):
    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "student_email": student.student_email,
        "parents_phone_number": student.parents_phone_number,
        "date_of_birth": str(student.date_of_birth),
        "gender": student.gender,
        "address": student.address,
        "student_group": student.student_group,
        "department": student.department_id,
        "teacher": student.teacher_id,
        "date_of_enrollment": str(student.date_of_enrollment),
        "is_active": student.is_active,
    }


from common.decorators import enforce_permissions

@csrf_exempt
@enforce_permissions('students', 'student')
def student_api(request, student_id = None):
    try:
        from common.permissions import apply_data_scope
        from students.models import Student
        scoped_qs = apply_data_scope(request.user, Student.objects.all(), 'student')
        if student_id is not None and not scoped_qs.filter(id=student_id).exists():
            return JsonResponse({"error": "Forbidden"}, status=403)

        if request.method == "GET":
            if student_id is not None:
                student = student_service.get(student_id)
                return JsonResponse(serialize_student(student))

            students = scoped_qs
            return JsonResponse([serialize_student(student) for student in students], safe = False)

        if request.method == "POST":
            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student = student_service.create(data)
            return JsonResponse(serialize_student(student), status = 201)

        if request.method == "PUT":
            if student_id is None:
                return JsonResponse({"error": Messages.STUDENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student = student_service.update(student_id, data, partial = False)
            return JsonResponse(serialize_student(student))

        if request.method == "PATCH":
            if student_id is None:
                return JsonResponse({"error": Messages.STUDENT_ID_REQUIRED}, status = 400)

            data = json.loads(request.body)

            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student = student_service.update(student_id, data, partial = True)
            return JsonResponse(serialize_student(student))

        if request.method == "DELETE":
            if student_id is None:
                return JsonResponse({"error": Messages.STUDENT_ID_REQUIRED}, status = 400)

            student_service.delete(student_id)
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except Student.DoesNotExist:
        return JsonResponse({"error": Messages.STUDENT_NOT_FOUND_BY_ID.format(student_id)}, status = 404)

    except ProtectedError:
        return JsonResponse({"error": Messages.STUDENT_CANNOT_BE_DELETED.format(student_id)}, status = 409)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)