from pathlib import Path
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME")
GEMINI_API_KEY = config("GEMINI_API_KEY")

# Model fallback chain for the Student AI Assistant's grounded Q&A
# generation (ai_assistant.services.gemini_generation_service). Not used
# for the Gemini embedding model, which remains a fixed single model.
# GEMINI_FALLBACK_MODELS is a comma-separated list, tried in order only
# after GEMINI_PRIMARY_MODEL fails with a transient (quota/availability)
# error - see common.ai.model_router. Left empty by default: an unset/
# empty value means "no fallback configured", not "misconfiguration".
GEMINI_PRIMARY_MODEL = config("GEMINI_PRIMARY_MODEL", default="gemini-2.5-flash")
GEMINI_FALLBACK_MODELS = config("GEMINI_FALLBACK_MODELS", default="")

# Separate chain for AI Assignment Evaluation (assignments.services
# .assignment_evaluation_service), which requires PDF/multimodal input and
# structured (Pydantic) JSON output - NOT every text-generation model
# supports that, so this must never simply reuse GEMINI_FALLBACK_MODELS.
# Only add a model here once you've confirmed it supports PDF input,
# multimodal generation, and response_schema-based structured output.
GEMINI_ASSIGNMENT_PRIMARY_MODEL = config("GEMINI_ASSIGNMENT_PRIMARY_MODEL", default="gemini-2.5-flash")
GEMINI_ASSIGNMENT_FALLBACK_MODELS = config("GEMINI_ASSIGNMENT_FALLBACK_MODELS", default="")

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'ai_assistant',
    'students',
    'teachers',
    'courses',
    'enrollments',
    'departments',
    'attendance',
    'remarks',
    'assignments',
    'course_offerings',
    'semesters',
    'sections',
    'users',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
]


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'student_ms.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'student_ms.wsgi.application'


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "student_management",
        "USER": "postgres",
        "PASSWORD": "abc.123",
        "HOST": "localhost",
        "PORT": "5432",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]


AUTH_USER_MODEL = 'users.User'


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}


CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}