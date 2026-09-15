class Messages:
    # ── Student ──────────────────────────────────────────────────────────────
    STUDENT_CREATED = "Student created successfully."
    STUDENT_UPDATED = "Student updated successfully."
    STUDENT_DELETED = "Student deleted successfully."
    STUDENT_NOT_FOUND = "Student not found."
    STUDENT_NOT_FOUND_BY_ID = "Student with ID {} not found."
    STUDENT_ID_REQUIRED = "Student ID is required."
    STUDENT_CANNOT_BE_DELETED = "Student with ID {} cannot be deleted because related records exist."
    STUDENT_AGE_MINIMUM = "Student age must be at least 5 years."

    # ── Teacher ───────────────────────────────────────────────────────────────
    TEACHER_CREATED = "Teacher created successfully."
    TEACHER_UPDATED = "Teacher updated successfully."
    TEACHER_DELETED = "Teacher deleted successfully."
    TEACHER_NOT_FOUND = "Teacher not found."
    TEACHER_NOT_FOUND_BY_ID = "Teacher with ID {} not found."
    TEACHER_ID_REQUIRED = "Teacher ID is required."
    TEACHER_CANNOT_BE_DELETED = "Teacher with ID {} cannot be deleted because related records exist."

    # ── Department ────────────────────────────────────────────────────────────
    DEPARTMENT_CREATED = "Department created successfully."
    DEPARTMENT_UPDATED = "Department updated successfully."
    DEPARTMENT_DELETED = "Department deleted successfully."
    DEPARTMENT_NOT_FOUND = "Department not found."
    DEPARTMENT_NOT_FOUND_BY_ID = "Department with ID {} not found."
    DEPARTMENT_ID_REQUIRED = "Department ID is required."
    DEPARTMENT_CANNOT_BE_DELETED = "Department with ID {} cannot be deleted because related records exist."
    DEPARTMENT_NAME_EXISTS = "Department name '{}' already exists."
    DEPARTMENT_CODE_EXISTS = "Department code '{}' already exists."

    # ── Section ───────────────────────────────────────────────────────────────
    SECTION_CREATED = "Section created successfully."
    SECTION_UPDATED = "Section updated successfully."
    SECTION_DELETED = "Section deleted successfully."
    SECTION_NOT_FOUND = "Section not found."
    SECTION_NOT_FOUND_BY_ID = "Section with ID {} not found."
    SECTION_ID_REQUIRED = "Section ID is required."
    SECTION_CANNOT_BE_DELETED = "Section with ID {} cannot be deleted because related records exist."
    SECTION_EXISTS = "A section with the same name, department, semester and academic year already exists."

    # ── Course ────────────────────────────────────────────────────────────────
    COURSE_CREATED = "Course created successfully."
    COURSE_UPDATED = "Course updated successfully."
    COURSE_DELETED = "Course deleted successfully."
    COURSE_NOT_FOUND = "Course not found."
    COURSE_NOT_FOUND_BY_ID = "Course with ID {} not found."
    COURSE_ID_REQUIRED = "Course ID is required."
    COURSE_CANNOT_BE_DELETED = "Course with ID {} cannot be deleted because related records exist."
    COURSE_CODE_EXISTS = "Course code '{}' already exists."

    # ── Course Offering ───────────────────────────────────────────────────────
    COURSE_OFFERING_CREATED = "Course offering created successfully."
    COURSE_OFFERING_UPDATED = "Course offering updated successfully."
    COURSE_OFFERING_DELETED = "Course offering deleted successfully."
    COURSE_OFFERING_EXISTS = "Course offering already exists."

    # ── Enrollment ────────────────────────────────────────────────────────────
    ENROLLMENT_CREATED = "Student enrolled successfully."
    ENROLLMENT_UPDATED = "Enrollment updated successfully."
    ENROLLMENT_DELETED = "Enrollment deleted successfully."
    ENROLLMENT_NOT_FOUND = "Enrollment not found."
    ENROLLMENT_NOT_FOUND_BY_ID = "Enrollment with ID {} not found."
    ENROLLMENT_ID_REQUIRED = "Enrollment ID is required."
    ENROLLMENT_CANNOT_BE_DELETED = "Enrollment with ID {} cannot be deleted because related records exist."
    ENROLLMENT_ALREADY_EXISTS = "Student with ID {} is already enrolled in course offering with ID {}."

    # ── Attendance ────────────────────────────────────────────────────────────
    ATTENDANCE_MARKED = "Attendance marked successfully."
    ATTENDANCE_NOT_FOUND = "Attendance record not found."
    ATTENDANCE_NOT_FOUND_BY_ID = "Attendance record with ID {} not found."
    ATTENDANCE_ID_REQUIRED = "Attendance ID is required."
    ATTENDANCE_CANNOT_BE_DELETED = "Attendance record with ID {} cannot be deleted because related records exist."
    ATTENDANCE_ALREADY_EXISTS = "An attendance record already exists for enrollment {} on {}."
    ATTENDANCE_DATE_IN_FUTURE = "Attendance date cannot be in the future."
    ATTENDANCE_DATE_INVALID_FORMAT = "Invalid date format. Use YYYY-MM-DD."
    ATTENDANCE_NO_ACTIVE_STUDENTS = "No active students are enrolled in this course offering."

    # ── Validation — General ──────────────────────────────────────────────────
    INVALID_JSON = "Invalid JSON."
    METHOD_NOT_ALLOWED = "Method not allowed."
    INVALID_REQUEST = "Invalid request."
    REQUEST_BODY_MUST_BE_JSON_OBJECT = "Request body must be a JSON object."
    REQUEST_DATA_MUST_BE_JSON_OBJECT = "Request data must be a JSON object."
    FORBIDDEN = "Forbidden."
    AUTHENTICATION_REQUIRED = "Authentication required."
    AUTH_CREDENTIALS_NOT_PROVIDED = "Authentication credentials were not provided."
    ACADEMIC_PLACEMENT_PENDING = "Your academic placement is still under review. This will be available once an administrator confirms your Department and Section."
    INVALID_OR_EXPIRED_TOKEN = "Invalid or expired token."
    PERMISSION_DENIED = "Permission denied: {} required."
    ADMIN_ACCESS_REQUIRED = "Admin access required."

    # ── Validation — Email ────────────────────────────────────────────────────
    EMAIL_REQUIRED = "Email is required."
    EMAIL_TOO_LONG = "Email cannot exceed 254 characters."
    INVALID_EMAIL = "Invalid email address."
    EMAIL_ALREADY_EXISTS = "Email '{}' already exists."

    # ── Validation — Phone ────────────────────────────────────────────────────
    PHONE_REQUIRED = "Phone number is required."
    PHONE_INVALID_CHARS = (
        "Phone number must contain digits, spaces, hyphens, parentheses "
        "and an optional leading '+'."
    )
    PHONE_INVALID_LENGTH = "Phone number must contain between 7 and 15 digits."

    # ── Validation — Name ─────────────────────────────────────────────────────
    NAME_REQUIRED = "Name is required."
    NAME_TOO_LONG = "Name cannot exceed 100 characters."
    NAME_INVALID_CHARS = "Name can contain only letters, spaces, hyphens and apostrophes."

    # ── Validation — Date of Birth ────────────────────────────────────────────
    DATE_OF_BIRTH_REQUIRED = "Date of birth is required."

    # ── Validation — FK / Lookup ──────────────────────────────────────────────
    INVALID_DEPARTMENT = "Invalid department with ID {}."
    INVALID_TEACHER = "Invalid teacher with ID {}."
    INVALID_COURSE = "Invalid course with ID {}."
    INVALID_COURSE_OFFERING = "Invalid course offering with ID {}."
    INVALID_STUDENT = "Invalid student with ID {}."
    INVALID_ENROLLMENT = "Invalid enrollment with ID {}."
    INVALID_SEMESTER = "Invalid semester '{}'."
    INVALID_SEMESTER_NUMBER = "Invalid semester number '{}'. Must be between 1 and 8."
    INVALID_SECTION = "Invalid section with ID {}."
    SECTION_NOT_IN_DEPARTMENT = "Section with ID {} does not belong to department with ID {}."
    PLACEMENT_REQUIRES_DEPARTMENT_AND_SECTION = "A student's academic placement cannot be confirmed without both a Department and a Section assigned."

    # ── Validation — Uniqueness ───────────────────────────────────────────────
    EMPLOYEE_ID_EXISTS = "Employee ID '{}' already exists."

    # ── Legacy / Generic (kept for backward compatibility) ────────────────────
    NOT_FOUND = "Object not found."

    # ── User ────────────────────────────────────────────────────────────────────
    USER_CREATED = "User created successfully."
    USER_UPDATED = "User updated successfully."
    USER_DELETED = "User deleted successfully."
    USER_NOT_FOUND = "User not found."
    USER_NOT_FOUND_BY_ID = "User with ID {} not found."
    USER_ID_REQUIRED = "User ID is required."

    USER_REGISTRATION_SUCCESSFUL = "Registration successful. Your account is pending approval."
    USER_APPROVED_SUCCESSFULLY = "User approved successfully."
    USER_REJECTED_SUCCESSFULLY = "User rejected successfully."

    INVALID_EMAIL_OR_PASSWORD = "Invalid email or password."
    ACCOUNT_PENDING_APPROVAL = "Your account is pending approval by an administrator."
    REGISTRATION_REJECTED = "Your registration was rejected."
    REFRESH_TOKEN_REQUIRED = "Refresh token is required."

    PASSWORD_REQUIRED = "Password is required."
    PASSWORD_TOO_SHORT = "Password must be at least 8 characters long."

    STUDENT_SECTION_REQUIRED = "Student is not assigned to any section."
    STUDENT_SECTION_MISMATCH = "Student can only enroll in course offerings for their assigned section."

    ENROLLMENT_SECTION_MISMATCH = "Student can only be enrolled in a course offering for their own section."
    STUDENT_INACTIVE = "Inactive student cannot be enrolled."
    COURSE_OFFERING_INACTIVE = "Inactive course offering cannot be used for enrollment."
    COURSE_OFFERING_COURSE_INACTIVE = "Course offering's course is inactive and cannot be used for enrollment."
    COURSE_OFFERING_TEACHER_INACTIVE = "Course offering's teacher is inactive and cannot be used for enrollment."
    COURSE_OFFERING_SECTION_INACTIVE = "Course offering's section is inactive and cannot be used for enrollment."

    COURSE_SECTION_SEMESTER_MISMATCH = "Course is designed for semester {} but the selected section is semester {}."


    ATTENDANCE_UPDATED = "Attendance updated successfully."
    ATTENDANCE_DELETED = "Attendance deleted successfully."
    ATTENDANCE_INVALID_STATUS = "Invalid attendance status. Must be one of: {}."
    ATTENDANCE_TEACHER_NOT_FOUND = "Teacher profile not found for the current user."
    ATTENDANCE_COURSE_OFFERING_NOT_FOUND = "Course offering not found."
    ATTENDANCE_COURSE_OFFERING_NOT_ASSIGNED = "You are not assigned to this course offering."
    ATTENDANCE_ENROLLMENT_NOT_FOUND = "Enrollment not found or is not active."
    ATTENDANCE_BULK_PAYLOAD_INVALID = "course_offering_id, date and a non-empty records list are required."
    ATTENDANCE_BULK_INCOMPLETE = "Attendance must include every active enrolled student for this course offering and date."

    # ── Remark ────────────────────────────────────────────────────────────────
    REMARK_CREATED = "Remark created successfully."
    REMARK_UPDATED = "Remark updated successfully."
    REMARK_DELETED = "Remark deleted successfully."
    REMARK_NOT_FOUND_BY_ID = "Remark with ID {} not found."
    REMARK_ID_REQUIRED = "Remark ID is required."
    REMARK_TEXT_REQUIRED = "Remark text is required."
    REMARK_STUDENT_REQUIRED = "Student is required."
    REMARK_COURSE_OFFERING_REQUIRED = "Course offering is required."
    REMARK_INVALID_VISIBILITY = "Invalid visibility '{}'. Must be one of: {}."
    REMARK_TEACHER_NOT_FOUND = "Teacher profile not found for the current user."
    REMARK_STUDENT_NOT_ENROLLED = "Student with ID {} is not enrolled in this course offering."
    REMARK_NOT_OWNED = "You can only modify remarks you created."
    REMARK_NOT_AUTHORIZED_FOR_STUDENT = "You are not authorized to add remarks for this student in this course offering."

    # ── Assignment ────────────────────────────────────────────────────────────
    ASSIGNMENT_NOT_FOUND_BY_ID = "Assignment with ID {} not found."
    ASSIGNMENT_ID_REQUIRED = "Assignment ID is required."
    ASSIGNMENT_TITLE_REQUIRED = "Title is required."
    ASSIGNMENT_DUE_AT_REQUIRED = "Due date is required."
    ASSIGNMENT_DUE_AT_INVALID = "Invalid due date format."
    ASSIGNMENT_COURSE_OFFERING_REQUIRED = "Course offering is required."
    ASSIGNMENT_TEACHER_NOT_FOUND = "Teacher profile not found for the current user."
    ASSIGNMENT_STUDENT_NOT_FOUND = "Student profile not found for the current user."
    ASSIGNMENT_NOT_AUTHORIZED_FOR_OFFERING = "You are not authorized to create assignments for this course offering."
    ASSIGNMENT_NOT_OWNED = "You can only modify assignments you created."
    ASSIGNMENT_FILE_CONTENT_TYPE_REQUIRED = "content_type is required."
    ASSIGNMENT_FILE_INVALID_CONTENT_TYPE = "Unsupported file type '{}'. Allowed types: PDF, DOC, DOCX, ZIP."
    ASSIGNMENT_FILE_TOO_LARGE = "File exceeds the maximum allowed size of {} MB."
    ASSIGNMENT_FILE_KEY_REQUIRED = "key is required."
    ASSIGNMENT_FILE_KEY_MISMATCH = "The provided key does not belong to this assignment."
    ASSIGNMENT_FILE_UPLOAD_NOT_FOUND = "No uploaded object was found for this key. Upload the file to S3 before confirming."
    ASSIGNMENT_PAST_DUE = "The due date for this assignment has passed."
    SUBMISSION_NOT_ENROLLED = "You are not enrolled in the course this assignment belongs to."
    SUBMISSION_FILE_KEY_MISMATCH = "The provided key does not belong to your submission."
    SUBMISSION_NOT_FOUND = "No submission found."

    # ── AI Assignment Evaluation ─────────────────────────────────────────────
    AI_EVALUATION_UNSUPPORTED_FORMAT = "AI evaluation isn't available for this file type yet. Only PDF submissions are currently supported."
    AI_EVALUATION_UNAVAILABLE = "AI evaluation is temporarily unavailable. Please try again later."
    AI_EVALUATION_NOT_FOUND = "No AI evaluation found for this submission."
    AI_EVALUATION_SCORE_INVALID = "Score must be a whole number between 0 and 100."
    AI_EVALUATION_STATUS_INVALID = "Invalid status '{}'. Must be one of: {}."

    # ── Profile Picture ───────────────────────────────────────────────────────
    PROFILE_PICTURE_CONTENT_TYPE_REQUIRED = "content_type is required."
    PROFILE_PICTURE_INVALID_CONTENT_TYPE = (
        "Unsupported image type '{}'. Allowed types: JPEG, PNG, WebP."
    )
    PROFILE_PICTURE_KEY_REQUIRED = "key is required."
    PROFILE_PICTURE_KEY_MISMATCH = "The provided key does not belong to this profile."
    PROFILE_PICTURE_UPLOAD_NOT_FOUND = (
        "No uploaded object was found for this key. Upload the file to S3 before confirming."
    )
    PROFILE_PICTURE_TOO_LARGE = "Profile picture exceeds the maximum allowed size of {} MB."
    PROFILE_PICTURE_NOT_FOUND = "No profile picture is set."

    # ── AI Assistant ──────────────────────────────────────────────────────────
    AI_ASSISTANT_QUESTION_REQUIRED = "Question is required."
    AI_ASSISTANT_QUESTION_TOO_LONG = "Question must be at most {} characters."
    AI_ASSISTANT_UNAVAILABLE = "The AI assistant is temporarily unavailable. Please try again later."
