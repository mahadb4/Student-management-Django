# Django Student Management System

A robust, modular Django backend for managing students, teachers, departments, courses, course offerings, enrollments, and attendance. The project is designed using a strict **Layered Architecture** (Model-Repository-Service-Validator-View/API-URL) to maintain clean separation of concerns, high testability, and clear maintainability.

---

## 1. Project Overview

The **Student Management System** provides administrative and API capabilities to track academic operations within an educational institution. 

### Installed Modules & Applications
* **`students`**: Manages student demographics, contact info, group allocations, active status, and department/teacher assignments. Includes both JSON API endpoints and Django HTML template views.
* **`teachers`**: Manages faculty records including employee IDs, academic qualifications, designations, salaries, joining dates, and department assignments. Includes JSON API endpoints and HTML views.
* **`departments`**: Handles academic department definitions, department codes, and descriptions. Includes JSON API endpoints and HTML views.
* **`courses`**: Manages course catalogs, course codes, credit hours, offering departments, and assigned primary teachers. Includes JSON API endpoints and HTML views.
* **`course_offerings`**: Manages specific course sections offered during an academic term (`SPRING`, `SUMMER`, `FALL`) and year, assigned to specific teachers. Includes JSON API endpoints and HTML views.
* **`enrollments`**: Tracks student enrollments in specific course offerings with status tracking (`ACTIVE`, `DROPPED`, `COMPLETED`). Includes JSON API endpoints and HTML views.
* **`attendance`**: Records daily student attendance (`PRESENT`, `ABSENT`, `LATE`) against active enrollments with optional remarks. Includes JSON API endpoints and HTML views.
* **`authentication`**: SimpleJWT-based authentication endpoints for user token issuance, refreshing, token blacklisting (logout), and current user identity resolution (`/api/auth/me/`).
* **`common`**: Core infrastructure library containing abstract base classes (`BaseRepository`, `BaseService`), global input validators (`CommonValidator`), standardized response formatting (`ApiResponse`), and centralized message definitions (`Messages`).

---

## 2. Architecture

The application strictly enforces a **Layered Architecture** pattern across all domain modules:

```
[ HTTP Request ]
       │
       ▼
   URL Router  (urls.py)
       │
       ▼
 API Handler / View  (api/*.py / views.py)
       │
       ▼
 Service Layer  (services/*_service.py) ──► Validator Layer (services/*_validator.py)
       │
       ▼
 Repository Layer  (repositories/*_repository.py)
       │
       ▼
 Model / Database  (models.py / PostgreSQL / SQLite)
```

### Layer Responsibilities

1. **URL Layer (`urls.py`)**
   * Routes incoming HTTP requests to their designated API handlers or HTML view functions.

2. **API Handler / View Layer (`api/*.py` & `views.py`)**
   * Deserializes request body data (`json.loads`).
   * Manages HTTP status codes (`200 OK`, `201 Created`, `204 No Content`, `400 Bad Request`, `404 Not Found`, `405 Method Not Allowed`, `409 Conflict`).
   * Handles exception mapping (e.g., `DoesNotExist` to 404, `ProtectedError` to 409, `ValueError` to 400).
   * Transforms models/queries into serialized JSON dictionaries or renders HTML templates.

3. **Service Layer (`*_service.py` & `BaseService`)**
   * Encapsulates domain business rules and use-case workflows.
   * Invokes the **Validator Layer** before executing mutation operations.
   * Checks business logic rules (e.g., duplicate email verification, duplicate enrollment checks).
   * Handles entity update merging (`_merge_data`) for partial updates (`PATCH`).
   * Interacts exclusively with the **Repository Layer** for persistence.

4. **Validator Layer (`*_validator.py` & `CommonValidator`)**
   * Executes field validation and format verification.
   * Uses `CommonValidator` for email regex parsing, phone number digit validation, age calculations (e.g., minimum student age of 5), and date range checks.
   * Raises `ValueError` with clear messages from `Messages` when validation fails.

5. **Repository Layer (`*_repository.py` & `BaseRepository`)**
   * Abstracts database querying and Django ORM interaction.
   * Provides model-level field assignment (`fill()`), filter routines (`email_exists()`, `employee_id_exists()`), and object retrieval.

6. **Model / Database Layer (`models.py`)**
   * Defines database schemas, field types, default values, database constraints (`UniqueConstraint`), and relational integrity rules (`on_delete=models.PROTECT`, `on_delete=models.SET_NULL`, `on_delete=models.CASCADE`).

### Purpose of the `common` Module

The `common` package serves as the shared foundation across all domain apps:
* **`BaseRepository`**: Generic base repository providing standard ORM methods (`get(id)`, `get_all()`, `delete(id)`).
* **`BaseService`**: Generic base service delegating standard read and delete calls to repositories.
* **`CommonValidator`**: Centralized, reusable static validation routines for names, emails, phone numbers, ages, dates, lengths, and choices.
* **`ApiResponse`**: Helper class providing standard JSON structures (`ApiResponse.success(...)`, `ApiResponse.error(...)`).
* **`Messages`**: Centralized string constants repository ensuring uniform validation messages, response notifications, and error strings across all apps.

---

## 3. Project Structure

Below is the clean directory layout of the `student_ms` codebase:

```
student_ms/
├── attendance/               # Attendance app
│   ├── api/                  # Attendance JSON API endpoints & URLs
│   ├── repositories/         # Attendance Repository layer
│   ├── services/             # Attendance Service & Validator layer
│   ├── models.py             # Attendance database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── authentication/           # SimpleJWT authentication & me/ user endpoint
│   ├── urls.py               # Token obtain, refresh, blacklist & me URLs
│   └── views.py              # MeView endpoint controller
├── common/                   # Shared infrastructure components
│   ├── repositories/         # BaseRepository implementation
│   ├── services/             # BaseService implementation
│   ├── messages.py           # Centralized string message constants
│   ├── responses.py          # Standardized JsonResponse builder
│   └── validators.py         # Reusable CommonValidator static helpers
├── course_offerings/         # Course Offering app
│   ├── api/                  # Offering JSON API endpoints & URLs
│   ├── repositories/         # Offering Repository layer
│   ├── services/             # Offering Service & Validator layer
│   ├── models.py             # CourseOffering database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── courses/                  # Course Catalog app
│   ├── api/                  # Course JSON API endpoints & URLs
│   ├── repositories/         # Course Repository layer
│   ├── services/             # Course Service & Validator layer
│   ├── models.py             # Course database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── departments/              # Department app
│   ├── api/                  # Department JSON API endpoints & URLs
│   ├── repositories/         # Department Repository layer
│   ├── services/             # Department Service & Validator layer
│   ├── models.py             # Department database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── enrollments/              # Student Enrollment app
│   ├── api/                  # Enrollment JSON API endpoints & URLs
│   ├── repositories/         # Enrollment Repository layer
│   ├── services/             # Enrollment Service & Validator layer
│   ├── models.py             # Enrollment database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── students/                 # Student Management app
│   ├── api/                  # Student JSON API endpoints & URLs
│   ├── repositories/         # Student Repository layer
│   ├── services/             # Student Service & Validator layer
│   ├── models.py             # Student database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── teachers/                 # Teacher / Faculty app
│   ├── api/                  # Teacher JSON API endpoints & URLs
│   ├── repositories/         # Teacher Repository layer
│   ├── services/             # Teacher Service & Validator layer
│   ├── models.py             # Teacher database model
│   ├── urls.py               # HTML View routing
│   └── views.py              # HTML View controllers
├── student_ms/               # Root Django Configuration
│   ├── settings.py           # Project settings (Databases, Apps, SimpleJWT)
│   ├── urls.py               # Master URL routing table
│   ├── wsgi.py / asgi.py     # Gateway interface handlers
├── manage.py                 # Django management CLI utility
└── seed_data.py              # Comprehensive database seeding script
```

---

## 4. Database Models and Tables

All database models inherit from Django's `models.Model`.

| Model Name | Table Name | Key Purpose | Primary Fields & Types | Key Relationships & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **`Department`** | `departments_department` | Represents an academic department. | `name` (Char), `code` (Char), `description` (Text), `is_active` (Bool) | `name` (Unique), `code` (Unique). |
| **`Teacher`** | `teachers_teacher` | Faculty member details. | `first_name`, `last_name`, `employee_id`, `email`, `phone_number`, `designation`, `qualification`, `gender`, `date_of_birth`, `date_of_joining`, `salary`, `address`, `is_active` | `employee_id` (Unique), `email` (Unique). `department`: Foreign Key to `Department` (`PROTECT`, Nullable). |
| **`Student`** | `students_student` | Student profile and contact info. | `first_name`, `last_name`, `student_email`, `parents_phone_number`, `date_of_birth`, `gender`, `address`, `student_group`, `date_of_enrollment`, `is_active` | `student_email` (Unique). `department`: Foreign Key to `Department` (`PROTECT`, Nullable). `teacher`: Foreign Key to `Teacher` (`SET_NULL`, Nullable). |
| **`Course`** | `courses_course` | Subject catalog entry. | `name` (Char), `code` (Char), `description` (Text), `credits` (PositiveInt), `is_active` (Bool) | `code` (Unique). `department`: Foreign Key to `Department` (`PROTECT`). `teacher`: Foreign Key to `Teacher` (`SET_NULL`, Nullable). |
| **`CourseOffering`** | `course_offerings_courseoffering` | Specific section of a course offered in a term. | `semester` (TextChoices: `SPRING`, `SUMMER`, `FALL`), `academic_year` (PositiveInt), `section` (Char), `is_active` | `course`: Foreign Key to `Course` (`PROTECT`). `teacher`: Foreign Key to `Teacher` (`PROTECT`). `UniqueConstraint` on (`course`, `teacher`, `semester`, `academic_year`, `section`). |
| **`Enrollment`** | `enrollments_enrollment` | Links a student to a course offering. | `status` (TextChoices: `ACTIVE`, `DROPPED`, `COMPLETED`), `enrolled_at` | `student`: Foreign Key to `Student` (`PROTECT`). `course_offering`: Foreign Key to `CourseOffering` (`PROTECT`). `UniqueConstraint` on (`student`, `course_offering`). |
| **`Attendance`** | `attendance_attendance` | Daily attendance log per enrollment. | `date` (Date), `status` (TextChoices: `PRESENT`, `ABSENT`, `LATE`), `remarks` (Char) | `enrollment`: Foreign Key to `Enrollment` (`CASCADE`, Nullable). `UniqueConstraint` on (`enrollment`, `date`). |

---

## 5. Application Flow

### Request Life Cycle (Example: Creating a Student via API)

When a client sends a request `POST /api/students/` with JSON data:

1. **Client**: Sends `POST /api/students/` with body `{"first_name": "Ali", "last_name": "Raza", ...}`.
2. **URL Router (`student_ms/urls.py` ➔ `students/api/urls.py`)**: Resolves the path to the `student_api` view function.
3. **API Handler (`student_api.py`)**: 
   * Receives `request` with `request.method == "POST"`.
   * Parses JSON body (`json.loads`).
   * Calls `student_service.create(data)`.
4. **Service Layer (`StudentService`)**:
   * Calls `student_validator.validate(data)`.
   * Invokes `student_repository.email_exists(email)` to ensure email uniqueness.
   * If valid, calls `student_repository.create(data)`.
5. **Validator Layer (`StudentValidator`)**:
   * Uses `CommonValidator` to verify email syntax, phone format, and student minimum age (>= 5 years).
   * Raises `ValueError` if any check fails.
6. **Repository Layer (`StudentRepository`)**:
   * Instantiates `Student`, maps dictionary fields via `fill()`, and calls `student.save()`.
   * Returns saved `Student` instance to `StudentService`.
7. **Model / Database**: Django ORM executes an `INSERT INTO students_student ...` SQL command.
8. **Response Generation**: `student_api` serializes the returned model instance to JSON and sends a `201 Created` HTTP response.

```
 Client             urls.py           student_api         StudentService        StudentValidator     StudentRepository        Database
   │                   │                   │                    │                     │                      │                   │
   │──POST /students/─►│                   │                    │                     │                      │                   │
   │                   │──student_api()───►│                    │                     │                      │                   │
   │                   │                   │──create(data)─────►│                     │                      │                   │
   │                   │                   │                    │──validate(data)────►│                      │                   │
   │                   │                   │                    │◄──(Success)─────────│                      │                   │
   │                   │                   │                    │──create(data)─────────────────────────────►│                   │
   │                   │                   │                    │                                            │──save()──────────►│
   │                   │                   │                    │                                            │◄──Instance────────│
   │                   │                   │◄──Instance─────────│                                            │                   │
   │◄──201 Created─────│───────────────────│                    │                     │                      │                   │
```

---

## 6. API Documentation

All API endpoints accept and return JSON. Endpoints returning single entities return a JSON object, while list endpoints return a JSON array.

### Authentication Endpoints (`/api/auth/`)

* **`POST /api/auth/login/`**
  * **Purpose**: Authenticate user and obtain JWT access & refresh tokens.
  * **Request Body**: `{"username": "admin", "password": "password"}`
  * **Response (200 OK)**: `{"refresh": "<refresh_token>", "access": "<access_token>"}`

* **`POST /api/auth/refresh/`**
  * **Purpose**: Refresh an expired access token using a valid refresh token.
  * **Request Body**: `{"refresh": "<refresh_token>"}`
  * **Response (200 OK)**: `{"access": "<new_access_token>"}`

* **`POST /api/auth/logout/`**
  * **Purpose**: Blacklist the refresh token to log out the user.
  * **Request Body**: `{"refresh": "<refresh_token>"}`
  * **Response (200 OK)**: `{}`

* **`GET /api/auth/me/`**
  * **Purpose**: Get current authenticated user details.
  * **Header Required**: `Authorization: Bearer <access_token>`
  * **Response (200 OK)**: `{"id": 1, "username": "admin", "role": "Admin", "is_staff": true, "is_superuser": true}`

---

### Student Endpoints (`/api/students/`)

* **`GET /api/students/`**: List all students. Returns array of student objects.
* **`POST /api/students/`**: Create a new student. Body requires `first_name`, `last_name`, `student_email`, `parents_phone_number`, `date_of_birth`, `gender`, `student_group`. Optional: `department`, `teacher`, `address`, `is_active`. Returns `201 Created`.
* **`GET /api/students/<student_id>/`**: Get student details by ID. Returns `200 OK` or `404 Not Found`.
* **`PUT /api/students/<student_id>/`**: Full update student record. Returns `200 OK`.
* **`PATCH /api/students/<student_id>/`**: Partial update student record. Returns `200 OK`.
* **`DELETE /api/students/<student_id>/`**: Delete student. Returns `204 No Content` or `409 Conflict` (if protected by foreign keys).

---

### Teacher Endpoints (`/api/teachers/`)

* **`GET /api/teachers/`**: List all teachers.
* **`POST /api/teachers/`**: Create a teacher. Requires `first_name`, `last_name`, `employee_id`, `email`, `phone_number`, `designation`, `qualification`, `gender`, `date_of_birth`, `salary`. Optional: `department`, `date_of_joining`, `address`, `is_active`.
* **`GET /api/teachers/<teacher_id>/`**: Get teacher detail.
* **`PUT /api/teachers/<teacher_id>/`**: Full update teacher record.
* **`PATCH /api/teachers/<teacher_id>/`**: Partial update teacher record.
* **`DELETE /api/teachers/<teacher_id>/`**: Delete teacher record.

---

### Department Endpoints (`/api/departments/`)

* **`GET /api/departments/`**: List all departments.
* **`POST /api/departments/`**: Create a department. Requires `name`, `code`. Optional: `description`, `is_active`.
* **`GET /api/departments/<department_id>/`**: Get department details.
* **`PUT /api/departments/<department_id>/`**: Full update department.
* **`PATCH /api/departments/<department_id>/`**: Partial update department.
* **`DELETE /api/departments/<department_id>/`**: Delete department.

---

### Course Endpoints (`/api/courses/`)

* **`GET /api/courses/`**: List all courses.
* **`POST /api/courses/`**: Create a course. Requires `name`, `code`, `credits`, `department`. Optional: `description`, `teacher`, `is_active`.
* **`GET /api/courses/<course_id>/`**: Get course details.
* **`PUT /api/courses/<course_id>/`**: Full update course.
* **`PATCH /api/courses/<course_id>/`**: Partial update course.
* **`DELETE /api/courses/<course_id>/`**: Delete course.

---

### Course Offering Endpoints (`/api/course_offerings/`)

* **`GET /api/course_offerings/`**: List all course offerings.
* **`POST /api/course_offerings/`**: Create a course offering. Requires `course`, `teacher`, `semester` (`SPRING`/`SUMMER`/`FALL`), `academic_year`, `section`.
* **`GET /api/course_offerings/<offering_id>/`**: Get offering details.
* **`PUT /api/course_offerings/<offering_id>/`**: Full update offering.
* **`PATCH /api/course_offerings/<offering_id>/`**: Partial update offering.
* **`DELETE /api/course_offerings/<offering_id>/`**: Delete offering.

---

### Enrollment Endpoints (`/api/enrollments/`)

* **`GET /api/enrollments/`**: List all enrollments.
* **`POST /api/enrollments/`**: Enroll a student in a course offering. Requires `student`, `course_offering`. Optional: `status` (`ACTIVE`/`DROPPED`/`COMPLETED`).
* **`GET /api/enrollments/<enrollment_id>/`**: Get enrollment details.
* **`PUT /api/enrollments/<enrollment_id>/`**: Full update enrollment.
* **`PATCH /api/enrollments/<enrollment_id>/`**: Partial update enrollment.
* **`DELETE /api/enrollments/<enrollment_id>/`**: Delete enrollment.

---

### Attendance Endpoints (`/api/attendance/`)

* **`GET /api/attendance/`**: List all attendance records.
* **`POST /api/attendance/`**: Mark attendance for an enrollment. Requires `enrollment`, `date` (`YYYY-MM-DD`), `status` (`PRESENT`/`ABSENT`/`LATE`). Optional: `remarks`.
* **`GET /api/attendance/<attendance_id>/`**: Get attendance record detail.
* **`PUT /api/attendance/<attendance_id>/`**: Full update attendance record.
* **`PATCH /api/attendance/<attendance_id>/`**: Partial update attendance record.
* **`DELETE /api/attendance/<attendance_id>/`**: Delete attendance record.

---

## 7. Authentication and User Management

### Current Authentication Implementation
* **JWT Integration**: Uses `rest_framework_simplejwt` in `student_ms/urls.py` for issuing standard JSON Web Tokens (`login/`, `refresh/`, `logout/`).
* **Me Endpoint**: `/api/auth/me/` (`MeView`) uses `rest_framework.permissions.IsAuthenticated` to inspect the JWT bearer token and return current user details (`id`, `username`, primary `role` from Django `Group`, `is_staff`, `is_superuser`).

### Known Missing / Incomplete Auth Features
> [!NOTE]
> * **`authentication` App Registration**: The `authentication` module exists in the folder structure and is routed in `student_ms/urls.py`, but `'authentication'` is currently **not listed** in `INSTALLED_APPS` inside `settings.py`.
> * **Custom User Model**: No custom user model exists; default Django `django.contrib.auth.models.User` is used.
> * **API Endpoint Security**: Domain API views (e.g., `student_api`, `teacher_api`, `department_api`) use `@csrf_exempt` and standard function-based views without DRF authentication/permission decorators. Domain CRUD endpoints are currently un-authenticated.
> * **User Registration & Password Recovery**: Endpoints for user sign-up (`/api/auth/register/`) or password resets are not implemented.

---

## 8. Setup and Installation

### Prerequisites
* **Python**: 3.10 or higher
* **PostgreSQL**: (Optional, default configured in settings.py) or SQLite

### Installation Steps (Windows PowerShell)

1. **Clone the repository**:
   ```powershell
   git clone <repository_url>
   cd student-management-django\student_ms
   ```

2. **Create a virtual environment**:
   ```powershell
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. **Install dependencies**:
   ```powershell
   pip install django djangorestframework djangorestframework-simplejwt psycopg2-binary
   ```

5. **Apply database migrations**:
   ```powershell
   python manage.py migrate
   ```

6. **(Optional) Seed the database with sample data**:
   Run the seeding script to populate departments, teachers, students, courses, offerings, enrollments, and attendance:
   ```powershell
   python seed_data.py
   ```

7. **Run the development server**:
   ```powershell
   python manage.py runserver
   ```
   Access the server at `http://127.0.0.1:8000/`.

---

## 9. Development Commands

Common Django management commands for local development:

* **Start server**:
  ```powershell
  python manage.py runserver
  ```
* **Make database migrations**:
  ```powershell
  python manage.py makemigrations
  ```
* **Apply database migrations**:
  ```powershell
  python manage.py migrate
  ```
* **Create administrative superuser**:
  ```powershell
  python manage.py createsuperuser
  ```
* **Execute seed script**:
  ```powershell
  python seed_data.py
  ```
* **Open Django Interactive Shell**:
  ```powershell
  python manage.py shell
  ```

---

## 10. Current Status

### Implemented Features
* Complete Layered Architecture (Model ➔ Repository ➔ Service ➔ Validator ➔ View/API ➔ URL).
* Full CRUD JSON API endpoints for Students, Teachers, Departments, Courses, Course Offerings, Enrollments, and Attendance.
* Strict database integrity constraints (`UniqueConstraint` on course offerings, enrollments, and attendance).
* Centralized validation helpers and exception handling across all domain apps.
* Working `seed_data.py` script populating test data across all tables.
* SimpleJWT routing for token login, refresh, blacklist, and user profile (`/api/auth/me/`).

### Partially Implemented Features
* **Authentication App**: SimpleJWT routes and `MeView` exist, but `'authentication'` is missing from `INSTALLED_APPS` in `settings.py`.
* **HTML Views**: Django templates views (`views.py` and `urls.py`) exist alongside API handlers, but some template files are placeholders.

### Planned / Missing Features
* Adding JWT `IsAuthenticated` and role-based permissions (`IsAdminUser`, `IsTeacher`) to domain API endpoints.
* User registration (`/api/auth/register/`) and password reset flows.
* Custom `User` model integration.
* Automated test suite (unit and integration tests for services and endpoints).
* Production-ready deployment configuration (CORS headers, environment variables `.env`, static files collection).

---

## 11. Future Frontend Integration

The backend is structured to seamlessly support integration with a modern decoupled single-page application (SPA), such as **React with TypeScript**:

* **RESTful JSON API**: All domain entities expose standardized JSON endpoints suitable for client-side HTTP clients (Axios or Fetch API).
* **JWT Authentication Flow**: The frontend can store JWT access tokens in memory or HTTP-only cookies, passing `Authorization: Bearer <access_token>` headers on API calls.
* **Mock Service Replacement**: Mock frontend services or state can be replaced directly with real API requests hitting `/api/students/`, `/api/courses/`, etc.
* **CORS Middleware**: To connect a React development server (e.g. running on `http://localhost:5173`), `django-cors-headers` should be installed and added to `MIDDLEWARE` in `settings.py`.
