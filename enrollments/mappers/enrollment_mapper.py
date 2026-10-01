from enrollments.dtos.enrollment_list_dto import EnrollmentListDTO
from enrollments.dtos.student_enrollment_list_dto import StudentEnrollmentListDTO
from enrollments.dtos.enrollment_reference_dto import EnrollmentReferenceDTO
from enrollments.dtos.enrollment_teacher_list_dto import EnrollmentTeacherListDTO
from enrollments.dtos.enrollment_attendance_roster_dto import EnrollmentAttendanceRosterDTO
from enrollments.dtos.enrollment_attendance_picker_dto import EnrollmentAttendancePickerDTO


class EnrollmentMapper:
    @staticmethod
    def to_list_dto(enrollment):
        section_name = (
            enrollment.course_offering.section.name
            if enrollment.course_offering.section_id else None
        )

        return EnrollmentListDTO(
            id = enrollment.id,
            status = enrollment.status,
            student_name = f"{enrollment.student.effective_first_name} {enrollment.student.effective_last_name}",
            student_email = enrollment.student.effective_email,
            semester = enrollment.course_offering.semester,
            academic_year = enrollment.course_offering.academic_year,
            course_name = enrollment.course_offering.course.name,
            course_code = enrollment.course_offering.course.code,
            section_name = section_name,
        ).to_dict()

    # Used only by the Admin Attendance page's Add/Edit modal Student picker
    # (/enrollments/?course_offering_id=&view=attendance) - that modal already
    # scopes to one course offering, so this drops status/semester/
    # academic_year/course_name/section_name/student_email entirely instead of
    # reusing to_list_dto's fuller shape (which Enrollments.tsx still needs
    # unchanged).
    @staticmethod
    def to_attendance_picker_dto(enrollment):
        return EnrollmentAttendancePickerDTO(
            id = enrollment.id,
            student_name = f"{enrollment.student.effective_first_name} {enrollment.student.effective_last_name}",
            course_code = enrollment.course_offering.course.code,
        ).to_dict()

    # Used only by the authenticated Student's own /students/me/courses/ -
    # drops student_id/student_name/student_email (redundant echoes of the
    # caller's own identity) and adds teacher_name (resolved from the
    # enrollment's own course_offering) so the Student My Courses UI doesn't
    # need a separate course_offerings fetch just to show who teaches each
    # of the student's own enrolled courses.
    @staticmethod
    def to_student_list_dto(enrollment):
        section_name = (
            enrollment.course_offering.section.name
            if enrollment.course_offering.section_id else None
        )

        teacher_name = (
            f"{enrollment.course_offering.teacher.effective_first_name} {enrollment.course_offering.teacher.effective_last_name}"
            if enrollment.course_offering.teacher_id else None
        )

        return StudentEnrollmentListDTO(
            id = enrollment.id,
            status = enrollment.status,
            semester = enrollment.course_offering.semester,
            academic_year = enrollment.course_offering.academic_year,
            course_name = enrollment.course_offering.course.name,
            course_code = enrollment.course_offering.course.code,
            teacher_name = teacher_name,
            section_name = section_name,
            course_offering_id = enrollment.course_offering_id,
            profile_picture_key = (
                enrollment.course_offering.teacher.user.profile_picture_key
                if enrollment.course_offering.teacher_id else None
            ),
        ).to_dict()

    # Used by the Student Attendance course filter dropdown - the dropdown's
    # option value/key is the enrollment id (matched against attendance
    # rows' enrollment_id), course_name/course_code make up its label, and
    # semester/academic_year/section_name back the "Term"/"Section" chips
    # shown once a course is selected.
    @staticmethod
    def to_reference_dto(enrollment):
        section_name = (
            enrollment.course_offering.section.name
            if enrollment.course_offering.section_id else None
        )

        return EnrollmentReferenceDTO(
            id = enrollment.id,
            course_code = enrollment.course_offering.course.code,
            course_name = enrollment.course_offering.course.name,
            semester = enrollment.course_offering.semester,
            academic_year = enrollment.course_offering.academic_year,
            section_name = section_name,
        ).to_dict()

    # Used only by the authenticated Teacher's own /teachers/me/students/,
    # which (since the "All Classes" option was removed from its caller) is
    # ALWAYS called with a single ?course_offering_id= - so course_name/
    # course_code/section_name/course_offering_id would be identical on every
    # row of a given response: redundant data the caller already has (it's
    # the id it just filtered by, and its label is already shown once in the
    # page's own class selector). Only per-student fields are returned here.
    @staticmethod
    def to_teacher_list_dto(enrollment):
        return EnrollmentTeacherListDTO(
            enrollment_id = enrollment.id,
            student_id = enrollment.student_id,
            student_name = f"{enrollment.student.effective_first_name} {enrollment.student.effective_last_name}",
            student_email = enrollment.student.effective_email,
            status = enrollment.status,
            profile_picture_key = enrollment.student.user.profile_picture_key,
        ).to_dict()

    # Used only by the Teacher Attendance register's roster fetch
    # (/teachers/me/students/?view=attendance) - that page marks/displays
    # attendance per student and never renders email or enrollment status, so
    # this purpose-specific projection drops both instead of reusing
    # to_teacher_list_dto's fuller shape (which My Students/ClassStudents.tsx
    # still needs unchanged).
    @staticmethod
    def to_attendance_roster_dto(enrollment):
        return EnrollmentAttendanceRosterDTO(
            enrollment_id = enrollment.id,
            student_name = f"{enrollment.student.effective_first_name} {enrollment.student.effective_last_name}",
            profile_picture_key = enrollment.student.user.profile_picture_key,
        ).to_dict()
