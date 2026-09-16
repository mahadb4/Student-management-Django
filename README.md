# Student Management System — Backend

A Django + Django REST Framework backend for a Student Management System, using JWT authentication, role-based data scoping (Admin / Teacher / Student), PostgreSQL, Redis caching, AWS S3 file storage, and a Gemini-powered AI Assistant with pgvector-based semantic retrieval.

## Tech Stack

- **Framework**: Django 6, Django REST Framework (JWT auth via `djangorestframework-simplejwt`)
- **Database**: PostgreSQL, with the `pgvector` extension for embedding storage/similarity search
- **Cache**: Redis (`django-redis`) — used for list/detail response caching, invalidated on writes
- **File storage**: AWS S3 (`boto3`) — pre-signed upload/view URLs for profile pictures and assignment/submission files
- **AI**: Google Gemini (`google-genai`) — grounded Q&A for the Student AI Assistant, and PDF assignment evaluation
- **Config**: `python-decouple`, reading from a `.env` file

## Applications

- **users** — custom `User` model (email-based login, `role`: admin/teacher/student/staff, `status`: pending/approved/rejected), registration, login/refresh/logout, admin approval workflow, onboarding
- **students / teachers** — profile CRUD, self-service `me/` endpoints, profile picture upload via S3
- **departments / sections / semesters / courses / course_offerings** — academic catalog data; course offerings tie a course, teacher, section and semester/academic year together
- **enrollments** — links a student to a course offering with status (`ACTIVE`/`DROPPED`/`COMPLETED`)
- **attendance** — per-enrollment daily attendance records (`PRESENT`/`ABSENT`/`LATE`)
- **assignments** — assignment CRUD, student submissions (file upload via S3), and AI-assisted evaluation of PDF submissions using Gemini
- **remarks** — teacher-authored remarks on students, with authorization-scoped visibility
- **ai_assistant** — Retrieval-augmented Q&A assistant for students, combining authorized data from remarks, attendance, assignments and courses, plus semantic search over remark embeddings (pgvector)
- **common** — shared base repository/service classes, permissions/data-scoping, caching helpers, S3/image services, pagination utilities, centralized messages

## Authentication & Authorization

- JWT auth (`rest_framework_simplejwt`): `POST /api/users/login/` issues access/refresh tokens; `POST /api/users/refresh/` and `POST /api/users/logout/` (blacklist) are also exposed.
- New accounts (student/teacher self-registration) start as `pending` and require admin approval (`approve`/`reject` endpoints) before becoming usable.
- Role-based data scoping is enforced server-side in `common.permissions.apply_data_scope` / `get_scope_identity`: teachers only see their own courses/students, students only see their own records, admins (superusers) see everything.
- Students must have a confirmed academic placement (department + section) before most student-portal endpoints are reachable; this is enforced in `common.permissions.authenticate_request`, independent of the frontend route guard.

## Student Onboarding & Placement Review

New students register and land in a pending state. `/api/users/onboarding/` lets a student submit their preferences; an admin reviews and confirms department/section placement via `/api/users/pending/` and the approve/reject endpoints. Only after placement confirmation can the student reach normal student-portal data (enrollments, attendance, assignments, AI assistant, etc.).

## Assignments & AI Evaluation

- Teachers create assignments per course offering; students upload submissions (one per student per assignment — resubmission overwrites the same row) via a two-step S3 upload flow (`attachment-upload-url/` then `attachment-confirm/`).
- `assignments.services.assignment_evaluation_service` sends a submitted PDF to Gemini (multimodal, structured/Pydantic JSON output) to produce a *suggested* score, strengths/weaknesses and feedback.
- The AI suggestion is never authoritative: `final_score` / `teacher_feedback` are only ever set by a teacher through the review endpoint (`assignments.api.ai_evaluation_api`), which enforces a strict order — auth → ownership checks → format check → S3 fetch → Gemini call → persist — so S3/Gemini are never touched before authorization passes.

## AI Assistant (RAG)

- `ai_assistant.orchestrator` routes a student's question to one or more domain context builders (remarks, attendance, assignments, courses), each independently authorization-scoped through the same `apply_data_scope`/remarks-authorization logic used by the regular APIs — the assistant never bypasses those checks.
- Remarks additionally support semantic retrieval: `RemarkEmbedding` (pgvector `VectorField`, 768 dimensions) stores a Gemini embedding per remark; `ai_assistant.retrieval.semantic_remarks` runs similarity search restricted to remarks the requesting user is already authorized to see.
- Combined context is sent to `GeminiGenerationService` to produce a grounded answer with sources; if no domain is relevant, Gemini is not called and a fallback/clarification message is returned.
- Gemini model selection uses a primary model with an optional fallback chain (`common.ai.model_router`), configured separately for Q&A generation and assignment evaluation, since only some models support the PDF/structured-output path.

## S3 Storage

`common.services.s3_service.S3Service` wraps `boto3` to generate pre-signed upload/view URLs (default 300s expiry). Used for:
- Student/Teacher profile pictures
- Assignment attachments and student submissions

Files are uploaded directly from the client to S3 using a pre-signed URL, then confirmed via a backend "confirm" endpoint that persists the object key — the server never proxies file bytes for uploads.

## Redis Caching

`django-redis` backs `common.cache.base_entity_cache.BaseEntityCache`, used by each app's `*_cache.py` (students, teachers, departments, sections, courses, course_offerings, enrollments). List and detail responses are cached per scope/search/filter/page; any write invalidates the affected detail key and drops all cached list pages for that entity.

## API Structure

All endpoints are mounted under `/api/` (see `student_ms/urls.py`):

| Prefix | App |
| --- | --- |
| `/api/users/` | Auth, registration, onboarding, admin approval |
| `/api/students/`, `/api/teachers/` | Profile CRUD + self-service `me/` endpoints |
| `/api/departments/`, `/api/sections/`, `/api/courses/`, `/api/course_offerings/` | Academic catalog |
| `/api/enrollments/` | Enrollments |
| `/api/attendance/` | Attendance |
| `/api/assignments/` | Assignments, submissions, AI evaluation |
| `/api/remarks/` | Remarks |
| `/api/ai-assistant/ask/` | AI Assistant Q&A |

Each domain app follows a layered structure: `api/` (view functions) → `services/` (business rules) → `repositories/` (ORM queries), with `validators/`, `mappers/` and `dtos/` where the domain needs them, plus a `cache/` layer for cached entities.

## Environment Variables

Configured via `python-decouple`, read from a `.env` file in `student_ms/`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key | required |
| `AWS_ACCESS_KEY_ID` | S3 credentials | required |
| `AWS_SECRET_ACCESS_KEY` | S3 credentials | required |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | required |
| `AWS_S3_REGION_NAME` | S3 region | required |
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `GEMINI_PRIMARY_MODEL` | Primary model for AI Assistant Q&A | `gemini-2.5-flash` |
| `GEMINI_FALLBACK_MODELS` | Comma-separated fallback models for Q&A | empty (no fallback) |
| `GEMINI_ASSIGNMENT_PRIMARY_MODEL` | Primary model for assignment evaluation | `gemini-2.5-flash` |
| `GEMINI_ASSIGNMENT_FALLBACK_MODELS` | Comma-separated fallback models for evaluation | empty (no fallback) |

The database (PostgreSQL, `student_management` DB) and Redis (`redis://127.0.0.1:6379/1`) connections are currently hardcoded in `settings.py` rather than read from `.env`.

## Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL with the `pgvector` extension available
- Redis server
- AWS S3 bucket and credentials (or a compatible substitute) for file uploads
- A Google Gemini API key

### Steps (Windows PowerShell)

```powershell
cd student-management-django\student_ms
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in `student_ms/` with the variables listed above.

Create the PostgreSQL database and enable pgvector:

```sql
CREATE DATABASE student_management;
\c student_management
CREATE EXTENSION IF NOT EXISTS vector;
```

Apply migrations and run the server:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Server runs at `http://127.0.0.1:8000/`, with the frontend dev server expected at `http://localhost:5173` (configured in `CORS_ALLOWED_ORIGINS`).

### Useful management commands

- `python manage.py create_admin` — create an admin user
- `python manage.py seed_academic_data` (course_offerings) — seed departments/courses/sections/offerings
- `python manage.py seed_dev_students` (students) — seed sample students
- `python manage.py generate_remark_embeddings` (ai_assistant) — backfill Gemini embeddings for existing remarks
- `python manage.py list_gemini_models` / `print_ai_model_chains` (ai_assistant) — inspect available Gemini models and configured fallback chains
