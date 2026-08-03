import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from students.services.retrieve import get_student
from students.services.update import update_student
from students.services.delete import delete_student


@csrf_exempt
def student(request, student_id):

    try:

        if request.method == "GET":

            student = get_student(student_id)

            return JsonResponse(
                {
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "student_email": student.student_email,
                    "parents_phone_number": student.parents_phone_number,
                    "date_of_birth": student.date_of_birth,
                    "gender": student.gender,
                    "address": student.address,
                    "student_group": student.student_group,
                    "date_of_enrollment": student.date_of_enrollment,
                    "is_active": student.is_active,
                }
            )

        elif request.method == "PUT":

            data = json.loads(request.body)

            update_student(
                student_id,
                data,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Student updated successfully.",
                }
            )

        elif request.method == "DELETE":

            delete_student(student_id)

            return JsonResponse(
                {
                    "success": True,
                    "message": "Student deleted successfully.",
                }
            )

        return JsonResponse(
            {
                "message": "Method Not Allowed",
            },
            status=405,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=400,
        )