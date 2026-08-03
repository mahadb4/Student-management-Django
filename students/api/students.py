import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from students.services.create import create_student
from students.services.retrieve import get_all_students


@csrf_exempt
def students(request):

    if request.method == "GET":

        students = get_all_students()

        data = []

        for student in students:

            data.append(
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

        return JsonResponse(
            data,
            safe=False,
        )

    elif request.method == "POST":

        try:

            if request.content_type == "application/json":

                data = json.loads(request.body)

            else:

                data = request.POST

            student = create_student(data)

            return JsonResponse(
                {
                    "success": True,
                    "message": "Student created successfully.",
                    "student_id": student.id,
                },
                status=201,
            )

        except Exception as e:

            return JsonResponse(
                {
                    "success": False,
                    "message": str(e),
                },
                status=400,
            )

    return JsonResponse(
        {
            "message": "Method Not Allowed",
        },
        status=405,
    )