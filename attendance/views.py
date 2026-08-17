from datetime import date
from django.shortcuts import get_object_or_404, redirect, render
from attendance.models import Attendance
from attendance.repositories.attendance_repository import AttendanceRepository
from attendance.services.attendance_service import AttendanceService
from attendance.services.attendance_validator import AttendanceValidator
from common.messages import Messages
from course_offerings.models import CourseOffering
from enrollments.models import Enrollment

attendance_validator = AttendanceValidator()
attendance_repository = AttendanceRepository()
attendance_service = AttendanceService(attendance_validator, attendance_repository)


def attendance_list_view(request):
    offerings = (
        CourseOffering.objects
        .filter(is_active = True)
        .select_related("course", "teacher")
        .order_by("academic_year", "semester", "course__code", "section")
    )
    return render(request, "attendance/attendance_list.html", {"offerings": offerings})


def attendance_mark_view(request, offering_id):
    offering = get_object_or_404(
        CourseOffering.objects.select_related("course", "teacher"),
        id = offering_id,
        is_active = True,
    )

    enrollments = (
        offering.enrollments
        .filter(status = Enrollment.Status.ACTIVE)
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )

    if not enrollments.exists():
        return render(request, "attendance/attendance_mark.html", {"offering": offering, "enrollments": enrollments, "error": Messages.ATTENDANCE_NO_ACTIVE_STUDENTS})

    selected_date = request.POST.get("date") if request.method == "POST" else date.today().isoformat()

    existing_attendance = Attendance.objects.filter(
        enrollment__in = enrollments,
        date = selected_date,
    )

    attendance_records = {record.enrollment_id: record for record in existing_attendance}

    for enrollment in enrollments:
        enrollment.attendance_record = attendance_records.get(enrollment.id)

    if request.method == "POST":
        try:
            attendance_date = AttendanceValidator.validate_date(request.POST.get("date"))
            attendance_data = []

            for enrollment in enrollments:
                status = request.POST.get(f"status_{enrollment.id}")
                AttendanceValidator.validate_status(status)
                remarks = request.POST.get(f"remarks_{enrollment.id}", "").strip()
                attendance_data.append({
                    "enrollment": enrollment,
                    "date": attendance_date,
                    "status": status,
                    "remarks": remarks,
                })

            attendance_service.mark_bulk(attendance_data)
            return redirect("attendance_mark", offering_id = offering.id)

        except Exception as e:
            return render(request, "attendance/attendance_mark.html", {"offering": offering, "enrollments": enrollments, "error": str(e), "selected_date": request.POST.get("date")})

    return render(request, "attendance/attendance_mark.html", {"offering": offering, "enrollments": enrollments, "selected_date": selected_date})