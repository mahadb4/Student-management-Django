from course_offerings.dtos.course_offering_list_dto import CourseOfferingListDTO
from course_offerings.dtos.course_offering_reference_dto import CourseOfferingReferenceDTO
from course_offerings.dtos.course_offering_teacher_list_dto import CourseOfferingTeacherListDTO
from course_offerings.dtos.course_offering_attendance_list_dto import CourseOfferingAttendanceListDTO
from course_offerings.dtos.course_offering_dashboard_list_dto import CourseOfferingDashboardListDTO
from course_offerings.dtos.course_offering_class_assignment_dto import CourseOfferingClassAssignmentDTO
from course_offerings.dtos.course_offering_attendance_reference_dto import CourseOfferingAttendanceReferenceDTO


class CourseOfferingMapper:
    @staticmethod
    def to_list_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None

        teacher_name = (
            f"{offering.teacher.effective_first_name} {offering.teacher.effective_last_name}"
            if offering.teacher_id else None
        )

        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingListDTO(
            id = offering.id,
            semester = offering.semester,
            academic_year = offering.academic_year,
            is_active = offering.is_active,
            course_name = course_name,
            course_code = course_code,
            teacher_name = teacher_name,
            section_name = section_name,
        ).to_dict()

    # Read-only projection for consumers that only display an offering (no
    # edit form needing raw FK ids) - e.g. the Student My Courses "browse to
    # enroll" tab and Teacher's read-only offering lookups.
    @staticmethod
    def to_reference_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None

        teacher_name = (
            f"{offering.teacher.effective_first_name} {offering.teacher.effective_last_name}"
            if offering.teacher_id else None
        )

        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingReferenceDTO(
            id = offering.id,
            semester = offering.semester,
            academic_year = offering.academic_year,
            is_active = offering.is_active,
            course_name = course_name,
            course_code = course_code,
            teacher_name = teacher_name,
            section_name = section_name,
        ).to_dict()

    # Used only by the Admin Student Edit form's Course Offering picker - that
    # dropdown already knows the section (fixed by the form's own Section
    # field) and never shows semester/academic_year/is_active, so this drops
    # them entirely instead of reusing to_list_dto's fuller shape (which
    # CourseOfferings.tsx and Enrollments.tsx still need unchanged).
    @staticmethod
    def to_class_assignment_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None

        teacher_name = (
            f"{offering.teacher.effective_first_name} {offering.teacher.effective_last_name}"
            if offering.teacher_id else None
        )

        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingClassAssignmentDTO(
            id = offering.id,
            course_name = course_name,
            course_code = course_code,
            teacher_name = teacher_name,
            section_name = section_name,
        ).to_dict()

    # Used only by the Admin Attendance page's Course/Section picker - Department
    # and Teacher are already picked in earlier steps of that same form, so this
    # drops semester/academic_year/is_active/course_name/teacher_name entirely
    # instead of reusing to_reference_dto's fuller shape (which student Courses.tsx
    # still needs unchanged).
    @staticmethod
    def to_attendance_reference_dto(offering):
        course_code = offering.course.code if offering.course_id else None
        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingAttendanceReferenceDTO(
            id = offering.id,
            course_code = course_code,
            section_name = section_name,
        ).to_dict()

    # "My Classes" (Teacher's own offerings) - no teacher_name (it's their
    # own), no raw ids, plus enrolled_students_count computed by the
    # repository's annotation rather than the frontend downloading every
    # enrollment row to count them.
    @staticmethod
    def to_teacher_list_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None
        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingTeacherListDTO(
            id = offering.id,
            course_name = course_name,
            course_code = course_code,
            semester = offering.semester,
            academic_year = offering.academic_year,
            section_name = section_name,
            is_active = offering.is_active,
            enrolled_students_count = offering.enrolled_students_count,
        ).to_dict()

    # Used only by the Teacher Attendance page's class dropdown
    # (/teachers/me/courses/?view=attendance) - that dropdown only ever
    # renders "<course_name> - <section_name>" and reads `id` to scope the
    # roster/attendance requests, so this drops course_code/semester/
    # academic_year/is_active/enrolled_students_count entirely instead of
    # reusing to_teacher_list_dto's fuller shape (which My Classes/Courses.tsx
    # still needs unchanged).
    @staticmethod
    def to_attendance_list_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingAttendanceListDTO(
            id = offering.id,
            course_name = course_name,
            section_name = section_name,
        ).to_dict()

    # Used only by the Teacher Dashboard's "My Classes" table
    # (/teachers/me/courses/?view=dashboard) - that table renders course
    # name/code/section/student-count/status but never semester/
    # academic_year (those are only shown on the full My Classes page,
    # Courses.tsx, which keeps using to_teacher_list_dto unchanged).
    @staticmethod
    def to_dashboard_list_dto(offering):
        course_name = offering.course.name if offering.course_id else None
        course_code = offering.course.code if offering.course_id else None
        section_name = offering.section.name if offering.section_id else None

        return CourseOfferingDashboardListDTO(
            id = offering.id,
            course_name = course_name,
            course_code = course_code,
            section_name = section_name,
            is_active = offering.is_active,
            enrolled_students_count = offering.enrolled_students_count,
        ).to_dict()
