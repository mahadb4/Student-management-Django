import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.cache.cache_service import CacheService
from common.messages import Messages
from common.services.s3_service import S3Service
from students.models import Student
from students.cache.student_cache import StudentCache
from students.repositories.student_repository import StudentRepository
from students.services.student_service import StudentService
from students.services.student_validator import StudentValidator

student_validator = StudentValidator()
student_repository = StudentRepository()
student_cache = StudentCache(CacheService())
student_service = StudentService(student_validator, student_repository, student_cache)
s3_service = S3Service()

from common.utils import attach_profile_picture_urls, paginate_queryset, resolve_ordering_param, resolve_pagination_params
from students.repositories.student_repository import DEFAULT_ORDERING, ORDERING_FIELDS

def serialize_student(student):
    return {
        "id": student.id,
        "first_name": student.effective_first_name,
        "last_name": student.effective_last_name,
        "student_email": student.effective_email,
        "parents_phone_number": student.parents_phone_number,
        "date_of_birth": str(student.user.date_of_birth),
        "gender": student.user.gender,
        "address": student.user.address,
        "department": student.department_id,
        "section": student.section_id,
        "date_of_enrollment": str(student.date_of_enrollment),
        "is_active": student.is_active,
        "profile_picture_url": student_service.get_profile_picture_view_url(student.id, s3_service),
    }


from common.decorators import enforce_permissions
from students.mappers.student_mapper import StudentMapper

@csrf_exempt
@enforce_permissions('students', 'student')
def student_api(request, student_id = None):
    try:
        from common.permissions import apply_data_scope
        # List responses use a projected, JOINed queryset (id/name fields + department/section
        # names only) so the Students list never needs separate Department/Section round trips.
        scoped_qs = apply_data_scope(request.user, student_repository.get_queryset_for_list(), 'student')
        if student_id is not None and not scoped_qs.filter(id = student_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

        if request.method == "GET":
            if student_id is not None:
                student = student_service.get(student_id)
                return JsonResponse(serialize_student(student))

            search = request.GET.get("search", "").strip() or None
            department_id = request.GET.get("department", "").strip() or None
            if department_id is not None:
                try:
                    department_id = int(department_id)
                except ValueError:
                    department_id = None
            #Normalize paging/ordering first so the cache key reflects the effective
            #values, not the raw query string. Scope filtering, ordering, pagination
            #and DTO mapping all happen inside the service, behind the Redis list cache.
            page_number, page_size = resolve_pagination_params(request)
            ordering = resolve_ordering_param(request, ORDERING_FIELDS, DEFAULT_ORDERING)
            payload = student_service.get_list(request.user, search, page_number, page_size, department_id, ordering)
            #Signed URLs are generated here, AFTER the cache lookup, so the cached
            #payload (a cache hit or a fresh loader() result) only ever carries the
            #raw profile_picture_key - never a presigned URL.
            payload["results"] = attach_profile_picture_urls(payload["results"], s3_service)
            return JsonResponse(payload)

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


@csrf_exempt
@enforce_permissions('students', 'student')
def student_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope
    students = apply_data_scope(request.user, student_repository.get_queryset_for_reference(), 'student')
    return paginate_queryset(request, students, StudentMapper.to_reference_dto, default_page_size = 10)


def serialize_student_profile(student):
    return {
        "id": student.id,
        "first_name": student.effective_first_name,
        "last_name": student.effective_last_name,
        "student_email": student.effective_email,
        "parents_phone_number": student.parents_phone_number,
        "date_of_birth": str(student.user.date_of_birth),
        "gender": student.user.gender,
        "address": student.user.address,
        "department_name": student.department.name if student.department_id else None,
        "section_name": student.section.name if student.section_id else None,
        "date_of_enrollment": str(student.date_of_enrollment),
        "profile_picture_url": student_service.get_profile_picture_view_url(student.id, s3_service),
    }


def my_profile_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    student = getattr(user, "student_profile", None)
    if not student:
        return JsonResponse({"error": Messages.STUDENT_NOT_FOUND}, status = 404)

    return JsonResponse(serialize_student_profile(student))


def my_summary_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    student = getattr(user, "student_profile", None)
    if not student:
        return JsonResponse({"error": Messages.STUDENT_NOT_FOUND}, status = 404)

    from enrollments.models import Enrollment
    from attendance.models import Attendance

    active_enrollments_count = Enrollment.objects.filter(
        student = student, is_deleted = False, status = Enrollment.Status.ACTIVE,
    ).count()

    attendance_qs = Attendance.objects.filter(
        enrollment__student = student, is_deleted = False,
    )

    present_count = attendance_qs.filter(status = Attendance.Status.PRESENT).count()
    absent_count = attendance_qs.filter(status = Attendance.Status.ABSENT).count()

    recent_attendance = [
        {"id": a.id, "date": str(a.date), "status": a.status}
        for a in attendance_qs.order_by("-date", "-id")[:3]
    ]

    return JsonResponse({
        "active_enrollments_count": active_enrollments_count,
        "present_count": present_count,
        "absent_count": absent_count,
        "recent_attendance": recent_attendance,
    })


#── Profile picture (self-service, "me") ──────────────────────────────────────

def _get_own_student(request):
    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return None, error

    student = getattr(user, "student_profile", None)
    if not student:
        return None, JsonResponse({"error": Messages.STUDENT_NOT_FOUND}, status = 404)

    return student, None


@csrf_exempt
def my_profile_picture_upload_url_api(request):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    student, error = _get_own_student(request)
    if error:
        return error

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        content_type = (data.get("content_type") or "").strip()
        if not content_type:
            raise ValueError(Messages.PROFILE_PICTURE_CONTENT_TYPE_REQUIRED)

        result = student_service.generate_profile_picture_upload_url(student.id, content_type, s3_service)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
def my_profile_picture_confirm_api(request):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    student, error = _get_own_student(request)
    if error:
        return error

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError(Messages.PROFILE_PICTURE_KEY_REQUIRED)

        student_service.confirm_profile_picture_upload(student.id, key, s3_service)
        url = student_service.get_profile_picture_view_url(student.id, s3_service)
        return JsonResponse({"profile_picture_url": url})

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
def my_profile_picture_api(request):
    student, error = _get_own_student(request)
    if error:
        return error

    if request.method == "GET":
        url = student_service.get_profile_picture_view_url(student.id, s3_service)
        return JsonResponse({"profile_picture_url": url})

    if request.method == "DELETE":
        student_service.delete_profile_picture(student.id, s3_service)
        return HttpResponse(status = 204)

    return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)


#── Profile picture (viewed by admin/teacher/self via id) ─────────────────────

def student_profile_picture_api(request, student_id):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope, authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    #Reuses the exact same data-scope rule as the main student_api endpoint:
    #admin sees everyone, a teacher only sees students enrolled in their own
    #course offerings, a student only sees themself. Prevents a student from
    #reading another student's picture by changing the ID in the URL, and a
    #teacher from reading an arbitrary student's picture.
    scoped_qs = apply_data_scope(user, student_repository.get_queryset_for_list(), 'student')
    if not scoped_qs.filter(id = student_id).exists():
        return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

    try:
        url = student_service.get_profile_picture_view_url(student_id, s3_service)
        return JsonResponse({"profile_picture_url": url})

    except Student.DoesNotExist:
        return JsonResponse({"error": Messages.STUDENT_NOT_FOUND_BY_ID.format(student_id)}, status = 404)