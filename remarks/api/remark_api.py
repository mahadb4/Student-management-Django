import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.decorators import enforce_permissions
from common.messages import Messages
from common.utils import paginate_queryset
from remarks.authorization import get_remarks_queryset_for_user, teacher_can_access_student_in_offering
from remarks.models import Remark
from students.models import Student
from course_offerings.models import CourseOffering



# The caller always already knows who they are and, for a teacher, which
# student/class they're looking at (the Remarks modal is opened from a
# specific student row) - so each role gets only the fields it doesn't
# already have, same as AttendanceMapper's to_teacher_list_dto /
# to_student_list_dto split.

# Teacher view: student/course are already known client-side (the row the
# Remarks modal was opened from). "teacher" is kept only so the frontend can
# show Edit/Delete solely on remarks this teacher wrote.
def serialize_remark_for_teacher(remark):
    return {
        "id": remark.id,
        "teacher": remark.teacher_id,
        "remark_text": remark.remark_text,
        "visibility": remark.visibility,
        "created_at": remark.created_at,
    }


# Student view: aggregates remarks across different classes/teachers, so
# course/teacher names are needed to tell rows apart. The student's own
# identity and the authoring teacher's raw id aren't needed for display.
# "visibility" is omitted here (unlike the teacher serializer) because a
# student only ever sees their own already-STUDENT_VISIBLE remarks and the
# UI never reads the field.
def serialize_remark_for_student(remark):
    return {
        "id": remark.id,
        "teacher_name": remark.teacher.user.name,
        "course_name": remark.course_offering.course.name,
        "course_code": remark.course_offering.course.code,
        "remark_text": remark.remark_text,
        "created_at": remark.created_at,
    }


def _serializer_for(user):
    if getattr(user, "teacher_profile", None):
        return serialize_remark_for_teacher
    return serialize_remark_for_student


def _get_teacher_or_error(request):
    teacher = getattr(request.user, "teacher_profile", None)
    if not teacher:
        return None, JsonResponse({"error": Messages.REMARK_TEACHER_NOT_FOUND}, status = 400)
    return teacher, None


def _validate_visibility(value):
    valid_values = [choice[0] for choice in Remark.Visibility.choices]
    if value not in valid_values:
        raise ValueError(Messages.REMARK_INVALID_VISIBILITY.format(value, ", ".join(valid_values)))


@csrf_exempt
@enforce_permissions('remarks', 'remark')
def remark_api(request, remark_id = None):
    try:
        if request.method == "GET":
            # get_remarks_queryset_for_user is the single place role-based
            # visibility is decided (student: own + STUDENT_VISIBLE only;
            # teacher: only classes they teach; superuser: everything).
            student_id = request.GET.get("student")
            course_offering_id = request.GET.get("course_offering")
            scoped_qs = get_remarks_queryset_for_user(request.user, student_id).select_related(
                "teacher__user", "course_offering__course"
            )
            if course_offering_id:
                scoped_qs = scoped_qs.filter(course_offering_id = course_offering_id)

            serialize = _serializer_for(request.user)

            if remark_id is not None:
                remark = scoped_qs.filter(id = remark_id).first()
                if not remark:
                    # Same response whether the remark doesn't exist or the
                    # caller isn't allowed to see it - a 404 for "exists but
                    # not yours" would itself leak information.
                    return JsonResponse({"error": Messages.REMARK_NOT_FOUND_BY_ID.format(remark_id)}, status = 404)
                return JsonResponse(serialize(remark))

            return paginate_queryset(request, scoped_qs.order_by("-created_at"), serialize)

        if request.method == "POST":
            teacher, error = _get_teacher_or_error(request)
            if error:
                return error

            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            student_id = data.get("student")
            course_offering_id = data.get("course_offering")
            remark_text = (data.get("remark_text") or "").strip()
            visibility = data.get("visibility", Remark.Visibility.PRIVATE)

            if not student_id:
                raise ValueError(Messages.REMARK_STUDENT_REQUIRED)
            if not course_offering_id:
                raise ValueError(Messages.REMARK_COURSE_OFFERING_REQUIRED)
            if not remark_text:
                raise ValueError(Messages.REMARK_TEXT_REQUIRED)
            _validate_visibility(visibility)

            student = Student.objects.filter(id = student_id).first()
            if not student:
                raise ValueError(Messages.INVALID_STUDENT.format(student_id))

            course_offering = CourseOffering.objects.filter(id = course_offering_id).first()
            if not course_offering:
                raise ValueError(Messages.INVALID_COURSE_OFFERING.format(course_offering_id))

            # The core authorization rule: a teacher may only write a remark
            # for a student who is genuinely enrolled in a course offering
            # THAT TEACHER teaches. This is checked in the backend, before
            # any data is written - never left to the caller's say-so.
            if not teacher_can_access_student_in_offering(teacher, student, course_offering):
                return JsonResponse({"error": Messages.REMARK_NOT_AUTHORIZED_FOR_STUDENT}, status = 403)

            remark = Remark.objects.create(
                student = student,
                teacher = teacher,
                course_offering = course_offering,
                remark_text = remark_text,
                visibility = visibility,
            )
            return JsonResponse(serialize_remark_for_teacher(remark), status = 201)

        if request.method in ("PUT", "PATCH"):
            if remark_id is None:
                return JsonResponse({"error": Messages.REMARK_ID_REQUIRED}, status = 400)

            teacher, error = _get_teacher_or_error(request)
            if error:
                return error

            remark = Remark.objects.filter(id = remark_id).first()
            if not remark:
                return JsonResponse({"error": Messages.REMARK_NOT_FOUND_BY_ID.format(remark_id)}, status = 404)

            # Ownership check: only the authoring teacher may edit a remark.
            # (Since a remark's teacher is always the offering's teacher at
            # creation time, this also guarantees the editor still teaches
            # that offering.)
            if remark.teacher_id != teacher.id:
                return JsonResponse({"error": Messages.REMARK_NOT_OWNED}, status = 403)

            data = json.loads(request.body)
            if not isinstance(data, dict):
                raise ValueError(Messages.REQUEST_BODY_MUST_BE_JSON_OBJECT)

            if "remark_text" in data:
                remark_text = (data.get("remark_text") or "").strip()
                if not remark_text:
                    raise ValueError(Messages.REMARK_TEXT_REQUIRED)
                remark.remark_text = remark_text

            if "visibility" in data:
                _validate_visibility(data["visibility"])
                remark.visibility = data["visibility"]

            remark.save()
            return JsonResponse(serialize_remark_for_teacher(remark))

        if request.method == "DELETE":
            if remark_id is None:
                return JsonResponse({"error": Messages.REMARK_ID_REQUIRED}, status = 400)

            teacher, error = _get_teacher_or_error(request)
            if error:
                return error

            remark = Remark.objects.filter(id = remark_id).first()
            if not remark:
                return JsonResponse({"error": Messages.REMARK_NOT_FOUND_BY_ID.format(remark_id)}, status = 404)

            if remark.teacher_id != teacher.id:
                return JsonResponse({"error": Messages.REMARK_NOT_OWNED}, status = 403)

            remark.delete()
            return HttpResponse(status = 204)

        return JsonResponse({"error": Messages.METHOD_NOT_ALLOWED}, status = 405)

    except json.JSONDecodeError:
        return JsonResponse({"error": Messages.INVALID_JSON}, status = 400)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status = 400)
