import json
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.cache.cache_service import CacheService
from common.messages import Messages
from common.services.s3_service import S3Service
from teachers.cache.teacher_cache import TeacherCache
from teachers.models import Teacher
from teachers.repositories.teacher_repository import DEFAULT_ORDERING, ORDERING_FIELDS, TeacherRepository
from teachers.services.teacher_service import TeacherService
from teachers.services.teacher_validator import TeacherValidator

teacher_validator = TeacherValidator()
teacher_repository = TeacherRepository()
teacher_cache = TeacherCache(CacheService())
teacher_service = TeacherService(teacher_validator, teacher_repository, teacher_cache)
s3_service = S3Service()

from common.utils import attach_profile_picture_urls, build_paginated_payload, paginate_queryset, resolve_ordering_param, resolve_pagination_params

def serialize_teacher_profile(teacher):
    # The Profile page renders the name as one string ("Muhammad Owais"), never
    # first/last separately, so this profile-only DTO returns it pre-joined -
    # unlike serialize_teacher() below (Admin's CRUD), which keeps them split
    # since Admin's edit form needs them as separate inputs.
    # phone_number/date_of_birth/gender/address/qualification are included so
    # the Profile page's own edit form (PATCH /teachers/me/, TEACHER_SELF_EDITABLE_FIELDS
    # below) can pre-fill with current values - salary/is_active/timestamps stay excluded
    # since they're admin-only and never shown here.
    return {
        "id": teacher.id,
        "name": f"{teacher.effective_first_name} {teacher.effective_last_name}",
        "employee_id": teacher.employee_id,
        "email": teacher.effective_email,
        "phone_number": teacher.phone_number,
        "date_of_birth": str(teacher.user.date_of_birth) if teacher.user.date_of_birth else None,
        "gender": teacher.user.gender,
        "address": teacher.user.address,
        "qualification": teacher.qualification,
        "department_name": teacher.department.name if teacher.department_id else None,
        "designation": teacher.designation,
        "profile_picture_url": teacher_service.get_profile_picture_view_url(teacher.id, s3_service),
    }


def serialize_teacher(teacher):
    return {
        "id": teacher.id,
        "first_name": teacher.effective_first_name,
        "last_name": teacher.effective_last_name,
        "employee_id": teacher.employee_id,
        "email": teacher.effective_email,
        "phone_number": teacher.phone_number,
        "department": teacher.department_id,
        "designation": teacher.designation,
        "qualification": teacher.qualification,
        "gender": teacher.user.gender,
        "date_of_birth": teacher.user.date_of_birth,
        "date_of_joining": teacher.date_of_joining,
        "salary": teacher.salary,
        "address": teacher.user.address,
        "is_active": teacher.is_active,
        "created_at": teacher.created_at,
        "updated_at": teacher.updated_at,
        "profile_picture_url": teacher_service.get_profile_picture_view_url(teacher.id, s3_service),
    }


from common.decorators import enforce_permissions
from teachers.mappers.teacher_mapper import TeacherMapper

@csrf_exempt
@enforce_permissions('teachers', 'teacher')
def teacher_api(request, teacher_id = None):
    try:
        from common.permissions import apply_data_scope
        from teachers.models import Teacher
        scoped_qs = apply_data_scope(request.user, Teacher.objects.all(), 'teacher')
        if teacher_id is not None and not scoped_qs.filter(id = teacher_id).exists():
            return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

        if request.method == "GET":
            if teacher_id is not None:
                teacher = teacher_service.get(teacher_id)
                return JsonResponse(serialize_teacher(teacher))

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
            payload = teacher_service.get_list(request.user, search, page_number, page_size, department_id, ordering)
            payload["results"] = attach_profile_picture_urls(payload["results"], s3_service)
            return JsonResponse(payload)

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


@csrf_exempt
@enforce_permissions('teachers', 'teacher')
def teacher_reference_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope
    department_id = request.GET.get("department_id") or None
    teachers = apply_data_scope(request.user, teacher_repository.get_queryset_for_reference(department_id = department_id), 'teacher')
    return paginate_queryset(request, teachers, TeacherMapper.to_reference_dto, default_page_size = 10)


# The only fields a teacher may change about themself, mirroring what they
# originally supply at onboarding - never employee_id/department/designation/
# date_of_joining/salary/status, which stay admin-controlled even if a client
# sends them in the PATCH body.
TEACHER_SELF_EDITABLE_FIELDS = ("phone_number", "date_of_birth", "gender", "address", "qualification")


@csrf_exempt
def my_profile_api(request):
    if request.method not in ("GET", "PATCH"):
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND}, status = 404)

    if request.method == "GET":
        return JsonResponse(serialize_teacher_profile(teacher))

    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        # Whitelist before handing off to the shared update path - resolving
        # `teacher` from request.user above already guarantees this can only
        # ever touch the caller's own record.
        allowed_data = {field: data[field] for field in TEACHER_SELF_EDITABLE_FIELDS if field in data}
        teacher_service.update(teacher.id, allowed_data, partial = True)
        return JsonResponse({"message": Messages.TEACHER_UPDATED})

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


def my_students_api(request):
    # Returns one row per enrollment (student only - no course/section fields,
    # since the frontend always calls this with a single ?course_offering_id=
    # already, making those fields identical/redundant on every row - see
    # EnrollmentMapper.to_teacher_list_dto).
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request, apply_data_scope
    from common.utils import apply_ordering
    from enrollments.models import Enrollment
    from enrollments.repositories.enrollment_repository import DEFAULT_ORDERING, ORDERING_FIELDS, EnrollmentRepository
    from enrollments.mappers.enrollment_mapper import EnrollmentMapper

    user, error = authenticate_request(request)
    if error:
        return error

    # Reuses apply_data_scope's existing teacher branch for 'enrollment':
    # enrollments in this teacher's own course offerings - the same scoping
    # rule already used by the general /enrollments/ list, just resolved for `me`.
    # ACTIVE-only: a DROPPED/COMPLETED enrollment is not a student currently
    # taking the class, so it must never appear in the roster the Attendance
    # register marks against (this was previously unfiltered here).
    qs = apply_data_scope(user, EnrollmentRepository().get_queryset_for_list(), 'enrollment').filter(
        status = Enrollment.Status.ACTIVE,
    )

    # Optional: scope down to one class's roster (e.g. for marking attendance,
    # where every student in the selected class must be selectable, not just
    # whichever page of the teacher's full cross-class enrollment list happens
    # to be loaded).
    course_offering_id = request.GET.get("course_offering_id")
    if course_offering_id:
        qs = qs.filter(course_offering_id = course_offering_id)

    # Same alphabetical-by-name ordering Admin's Enrollments list already
    # applies (ORDERING_FIELDS/DEFAULT_ORDERING = "name", i.e.
    # student__user__name) - reused here rather than left unsorted.
    qs = apply_ordering(qs, DEFAULT_ORDERING, ORDERING_FIELDS)

    # Opt-in narrower projection for the Attendance register (?view=attendance) -
    # every other caller (the My Students page) keeps the fuller default shape.
    mapper_func = (
        EnrollmentMapper.to_attendance_roster_dto
        if request.GET.get("view") == "attendance"
        else EnrollmentMapper.to_teacher_list_dto
    )

    page_number, page_size = resolve_pagination_params(request, default_page_size = 10)
    payload = build_paginated_payload(qs, page_number, page_size, mapper_func)
    payload["results"] = attach_profile_picture_urls(payload["results"], s3_service)
    return JsonResponse(payload)


def my_dashboard_api(request):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND}, status = 404)

    from course_offerings.models import CourseOffering
    from enrollments.models import Enrollment

    active_classes = CourseOffering.objects.filter(
        teacher_id = teacher.id, is_deleted = False, is_active = True,
    ).count()

    total_students = Enrollment.objects.filter(
        course_offering__teacher_id = teacher.id,
        course_offering__is_deleted = False,
        is_deleted = False,
        status = Enrollment.Status.ACTIVE,
    ).values("student_id").distinct().count()

    return JsonResponse({
        "active_classes": active_classes,
        "total_students": total_students,
    })


def _get_own_teacher(request):
    from common.permissions import authenticate_request
    user, error = authenticate_request(request)
    if error:
        return None, error

    teacher = getattr(user, "teacher_profile", None)
    if not teacher:
        return None, JsonResponse({"error": Messages.TEACHER_NOT_FOUND}, status = 404)

    return teacher, None


@csrf_exempt
def my_profile_picture_upload_url_api(request):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    teacher, error = _get_own_teacher(request)
    if error:
        return error

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        content_type = (data.get("content_type") or "").strip()
        if not content_type:
            raise ValueError(Messages.PROFILE_PICTURE_CONTENT_TYPE_REQUIRED)

        result = teacher_service.generate_profile_picture_upload_url(teacher.id, content_type, s3_service)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
def my_profile_picture_confirm_api(request):
    if request.method != "POST":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    teacher, error = _get_own_teacher(request)
    if error:
        return error

    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data, dict):
            raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

        key = (data.get("key") or "").strip()
        if not key:
            raise ValueError(Messages.PROFILE_PICTURE_KEY_REQUIRED)

        teacher_service.confirm_profile_picture_upload(teacher.id, key, s3_service)
        url = teacher_service.get_profile_picture_view_url(teacher.id, s3_service)
        return JsonResponse({"profile_picture_url": url})

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)


@csrf_exempt
def my_profile_picture_api(request):
    teacher, error = _get_own_teacher(request)
    if error:
        return error

    if request.method == "GET":
        url = teacher_service.get_profile_picture_view_url(teacher.id, s3_service)
        return JsonResponse({"profile_picture_url": url})

    if request.method == "DELETE":
        teacher_service.delete_profile_picture(teacher.id, s3_service)
        return HttpResponse(status = 204)

    return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)


def teacher_profile_picture_api(request, teacher_id):
    if request.method != "GET":
        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    from common.permissions import apply_data_scope, authenticate_request
    user, error = authenticate_request(request)
    if error:
        return error

    scoped_qs = apply_data_scope(user, Teacher.objects.all(), 'teacher')
    if not scoped_qs.filter(id = teacher_id).exists():
        return JsonResponse({"error": Messages.FORBIDDEN}, status = 403)

    try:
        url = teacher_service.get_profile_picture_view_url(teacher_id, s3_service)
        return JsonResponse({"profile_picture_url": url})

    except Teacher.DoesNotExist:
        return JsonResponse({"error": Messages.TEACHER_NOT_FOUND_BY_ID.format(teacher_id)}, status = 404)