from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,redirect,render
from attendance.models import Attendance
from attendance.repositories.attendance_repository import AttendanceRepository
from attendance.services.attendance_service import AttendanceService
from attendance.services.attendance_validator import AttendanceValidator
from common.messages import Messages
from course_offerings.models import CourseOffering
from enrollments.models import Enrollment
from teachers.models import Teacher

attendance_validator = AttendanceValidator()
attendance_repository = AttendanceRepository()
attendance_service = AttendanceService(attendance_validator,attendance_repository)

@login_required
def attendance_list_view(request):
    teacher = Teacher.objects.filter(
        user = request.user,
        is_deleted = False,
        is_active = True,
    ).first()

    if not teacher:
        return render(request,"attendance/attendance_list.html",{
            "offerings": [],
            "error": Messages.ATTENDANCE_TEACHER_NOT_FOUND,
        })

    offerings = CourseOffering.objects.filter(
        teacher = teacher,
        is_active = True,
        is_deleted = False,
    ).select_related(
        "course",
        "teacher",
        "section",
    ).order_by(
        "academic_year",
        "semester",
        "course__code",
    )

    return render(request,"attendance/attendance_list.html",{
        "offerings": offerings,
    })

@login_required
def attendance_mark_view(request,offering_id):
    teacher = Teacher.objects.filter(
        user = request.user,
        is_deleted = False,
        is_active = True,
    ).first()

    if not teacher:
        return render(request,"attendance/attendance_mark.html",{
            "error": Messages.ATTENDANCE_TEACHER_NOT_FOUND,
        })

    offering = CourseOffering.objects.filter(
        id = offering_id,
        teacher = teacher,
        is_active = True,
        is_deleted = False,
    ).select_related(
        "course",
        "teacher",
        "section",
    ).first()

    if not offering:
        return render(request,"attendance/attendance_mark.html",{
            "error": Messages.ATTENDANCE_COURSE_OFFERING_NOT_ASSIGNED,
        })

    enrollments = Enrollment.objects.filter(
        course_offering = offering,
        status = Enrollment.Status.ACTIVE,
        is_deleted = False,
        student__is_deleted = False,
        student__is_active = True,
    ).select_related(
        "student",
    ).order_by(
        "student__first_name",
        "student__last_name",
    )

    if not enrollments.exists():
        return render(request,"attendance/attendance_mark.html",{
            "offering": offering,
            "enrollments": enrollments,
            "error": Messages.ATTENDANCE_NO_ACTIVE_STUDENTS,
        })

    selected_date = request.POST.get("date") if request.method == "POST" else date.today().isoformat()

    existing_attendance = Attendance.objects.filter(
        enrollment__in = enrollments,
        date = selected_date,
        is_deleted = False,
    )

    attendance_records = {
        record.enrollment_id: record
        for record in existing_attendance
    }

    for enrollment in enrollments:
        enrollment.attendance_record = attendance_records.get(enrollment.id)

    if request.method == "POST":
        try:
            attendance_date = attendance_validator._parse_date(request.POST.get("date"))
            attendance_data = []

            for enrollment in enrollments:
                status = request.POST.get(f"status_{enrollment.id}")
                remarks = request.POST.get(f"remarks_{enrollment.id}","").strip()

                attendance_data.append({
                    "enrollment_id": enrollment.id,
                    "date": attendance_date.isoformat(),
                    "status": status,
                    "remarks": remarks,
                })

            attendance_service.mark_bulk(attendance_data,teacher)

            return redirect(
                "attendance_mark",
                offering_id = offering.id,
            )

        except ValueError as error:
            return render(request,"attendance/attendance_mark.html",{
                "offering": offering,
                "enrollments": enrollments,
                "error": str(error),
                "selected_date": request.POST.get("date"),
            })

    return render(request,"attendance/attendance_mark.html",{
        "offering": offering,
        "enrollments": enrollments,
        "selected_date": selected_date,
    })