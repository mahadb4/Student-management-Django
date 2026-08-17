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
    STUDENT_GROUP_REQUIRED = "Student group is required."

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

    # ── Validation — Uniqueness ───────────────────────────────────────────────
    EMPLOYEE_ID_EXISTS = "Employee ID '{}' already exists."

    # ── Legacy / Generic (kept for backward compatibility) ────────────────────
    NOT_FOUND = "Object not found."
