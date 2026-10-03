# Student Management System — Backend

A Django + Django REST Framework backend for a Student Management System, using JWT authentication, role-based data scoping (Admin / Teacher / Student), PostgreSQL, Redis caching, AWS S3 file storage, and a Gemini-powered AI Assistant with pgvector-based semantic retrieval.

## Tech Stack

- **Framework**: Django 6, Django REST Framework (JWT auth via `djangorestframework-simplejwt`)
- **Database**: PostgreSQL, with the `pgvector` extension for embedding storage/similarity search
- **Cache**: Redis (`django-redis`) — used for list/detail response caching, invalidated on writes
- **File storage**: AWS S3 (`boto3`) — pre-signed upload/view URLs for profile pictures and assignment/submission files
- **AI**: Google Gemini (`google-genai`) — grounded Q&A for the Student AI Assistant, and PDF assignment evaluation
- **Config**: `python-decouple`, reading from a `.env` file
- **Deployment**: Docker Compose on EC2, images in ECR, deployed from GitHub Actions through AWS SSM

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

Configured with `python-decouple` from a `.env` file in `student_ms/`. Copy `.env.example` for local development; never commit `.env`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key (also signs JWTs) | required |
| `DEBUG` | Django debug mode | `False` (`.env.example` sets `True` for local use) |
| `ALLOWED_HOSTS` | Comma-separated hostnames Django accepts | `localhost,127.0.0.1` |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | PostgreSQL connection | `localhost`, `5432`, `student_management`, `postgres` |
| `DB_PASSWORD` | PostgreSQL password | required |
| `REDIS_URL` | Redis cache URL | `redis://127.0.0.1:6379/1` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins | `http://localhost:5173,http://127.0.0.1:5173` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted HTTPS origins (Django admin) | empty |
| `USE_X_FORWARDED_PROTO` | Trust the load balancer's `X-Forwarded-Proto` header | `False` |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials | required |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME` | S3 bucket and region | required |
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `GEMINI_PRIMARY_MODEL` | Primary model for AI Assistant Q&A | `gemini-2.5-flash` |
| `GEMINI_FALLBACK_MODELS` | Comma-separated fallback models for Q&A | empty (no fallback) |
| `GEMINI_ASSIGNMENT_PRIMARY_MODEL` | Primary model for assignment evaluation | `gemini-2.5-flash` |
| `GEMINI_ASSIGNMENT_FALLBACK_MODELS` | Comma-separated fallback models for evaluation | empty (no fallback) |

`docker-compose.yml` (local) overrides `DB_HOST` and `REDIS_URL` to point at its own containers. `docker-compose.prod.yml` forces `DEBUG=False` and `REDIS_URL=redis://redis:6379/1`; everything else comes from the production `.env`, plus `BACKEND_IMAGE` (the ECR image to run).

## Local Development

Requires Docker with Docker Compose. PostgreSQL + pgvector and Redis run as containers.

```bash
git clone https://github.com/mahadb4/Student-management-Django.git
cd Student-management-Django
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead of `cp`.

`.env.example` contains placeholders only. They are enough to start the app and run the tests; to use S3 uploads or the AI features, replace the `AWS_*` and `GEMINI_API_KEY` values in your own `.env`. `DB_PASSWORD` is used by both the Django container and the local `db` container. If you already have a local `pgdata` volume created with a different password, set `DB_PASSWORD` to that password or run `docker compose down -v` (this deletes local data).

The local database is a Docker container that starts empty. It is not the production RDS database.

- Backend API: `http://localhost:8000/`
- Frontend dev server (separate repository): `http://localhost:5173`

### Useful management commands

Run these with `docker compose exec web <command>`:


- `python manage.py create_admin` — create an admin user
- `python manage.py seed_academic_data` (course_offerings) — seed departments/courses/sections/offerings
- `python manage.py seed_dev_students` (students) — seed sample students
- `python manage.py generate_remark_embeddings` (ai_assistant) — backfill Gemini embeddings for existing remarks
- `python manage.py list_gemini_models` / `print_ai_model_chains` (ai_assistant) — inspect available Gemini models and configured fallback chains

## Production Architecture

```
Vercel (React/Vite frontend)
   -> Application Load Balancer
      -> EC2 instance, port 8000
         -> Docker Compose: Django/Gunicorn + Redis
            -> RDS PostgreSQL
            -> S3 (private bucket, presigned URLs)
            -> Gemini API
```

- **Frontend**: React/Vite app deployed on Vercel.
- **Backend**: Django + Gunicorn in Docker on a single EC2 instance, started with `docker-compose.prod.yml` (services `web` and `redis`).
- **Images**: stored in Amazon ECR (`student-management-backend`), tagged with the Git commit SHA.
- **Database**: PostgreSQL on AWS RDS. There is no database container in production.
- **Cache**: Redis runs as a Docker container on the EC2 instance and is not published outside the Docker network.
- **Files**: profile pictures and assignment files live in a private S3 bucket and are accessed through presigned URLs. The browser talks to S3 directly, so the bucket needs a CORS rule for the Vercel origin.
- **Traffic**: the Application Load Balancer forwards to EC2 port 8000. The EC2 private IP must be in `ALLOWED_HOSTS` so load balancer health checks pass.
- **AI**: Gemini is called from the backend for the RAG assistant, embeddings and assignment evaluation.

PostgreSQL is not a production container; Redis is the only data service running next to Django.

The server keeps `/home/ec2-user/student-management/.env` (production secrets, not in Git) and `docker-compose.prod.yml`. The `.env` needs the variables listed above plus `BACKEND_IMAGE`, which the deploy script updates on each deployment.

## Deployment / CI-CD

Pushing to `main` runs `.github/workflows/deploy.yml`:

1. GitHub Actions runs the Django checks, migration check and tests.
2. It assumes the AWS role through OIDC, builds the Docker image and pushes it to ECR, tagged with the commit SHA.
3. It sends an AWS SSM `SendCommand` to the EC2 instance, which writes `deploy/deploy.sh` from the commit and runs it with the commit SHA.
4. The script logs in to ECR with the instance's IAM role, pulls that exact image and runs `docker compose up -d`.
5. It runs `manage.py migrate`, then checks `http://127.0.0.1:8000/admin/login/` locally.
6. The workflow polls `GetCommandInvocation`, prints the command output and fails if the deployment did not succeed.

Pushes to `dev` only run the tests. `docker-compose.prod.yml` is not synced by the pipeline; copy it to the server if it changes.

GitHub repository variables used by the workflow (no secrets are stored in GitHub):

- `AWS_REGION`
- `AWS_ROLE_ARN`
- `ECR_REPOSITORY`

The workflow's AWS role (assumed through OIDC) only needs to push to ECR, call `ssm:SendCommand` and call `ssm:GetCommandInvocation`. The EC2 instance's own IAM role pulls from ECR and is what the script uses to log in.

To deploy manually on the server: `cd /home/ec2-user/student-management && ./deploy/deploy.sh <commit-sha>`.

## AWS Services

| Service | Role |
| --- | --- |
| EC2 | Runs the Django and Redis containers with Docker Compose |
| ALB | Internet-facing entry point, forwards to EC2 port 8000 |
| RDS PostgreSQL | Production database (with the `vector` extension) |
| S3 | Private bucket for profile pictures, assignment files and submissions |
| ECR | Stores the backend Docker images |
| SSM | Lets GitHub Actions run the deploy script on EC2 without SSH |
| IAM (OIDC) | GitHub Actions assumes a role to push images and send SSM commands |

S3 CORS: the browser uploads and downloads directly with presigned URLs, so the bucket needs a CORS rule that allows the `GET`, `PUT` and `HEAD` methods, all headers, and these origins: the Vercel production frontend (`https://<your-vercel-domain>`, no trailing slash) and `http://localhost:5173` for local development. Without it, uploads fail with a 403 on the preflight request.

Django CORS is separate: set `CORS_ALLOWED_ORIGINS` to the same frontend origins.

## Default passwords

Accounts created through the student and teacher create endpoints, and by the seed and reset management commands (`seed_academic_data`, `seed_dev_students`, `reset_student_teacher_passwords`), get a shared default password defined in code. These are development and onboarding defaults, not production credentials. The application does not currently force a password change on first login, so change or reset these passwords before real use.
