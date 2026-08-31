from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from common.messages import Messages


@csrf_exempt
def admin_summary(request):
    if request.method != "GET":
        return JsonResponse(
            {"error": Messages.METHOD_NOT_ALLOWED},
            status = 405,
        )

    authentication = JWTAuthentication()

    try:
        authentication_result = authentication.authenticate(request)
    except Exception:
        authentication_result = None

    if authentication_result is None:
        return JsonResponse(
            {"error": Messages.AUTHENTICATION_REQUIRED},
            status = 401,
        )

    user, _ = authentication_result

    if user.role != "admin" and not user.is_superuser:
        return JsonResponse(
            {"error": Messages.ADMIN_ACCESS_REQUIRED},
            status = 403,
        )

    from students.models import Student
    from teachers.models import Teacher
    from departments.models import Department
    from courses.models import Course
    from course_offerings.models import CourseOffering
    from enrollments.models import Enrollment

    return JsonResponse({
        "total_students": Student.objects.count(),
        "total_teachers": Teacher.objects.count(),
        "total_departments": Department.objects.count(),
        "total_courses": Course.objects.count(),
        "total_course_offerings": CourseOffering.objects.count(),
        "total_enrollments": Enrollment.objects.count(),
    })