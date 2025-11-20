"""
Django settings for OneIntelligence project.
"""
import os

from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SALES_AI_MODEL = "gpt-4o-mini"  # set to desired model
SALES_AI_CACHE_TTL = 60 * 60 * 12
SECRET_KEY = 'django-insecure-placeholder-key'
DEBUG = True

# Django cache configured to Redis recommended:
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

ALLOWED_HOSTS = [
    '192.168.1.9',
    '127.0.0.1',
    'localhost:3000',
    'localhost',
    '3.109.211.100',
    '13.235.73.171',
    '52.66.11.128',
]

# ─────────────────────────────────────────
# App registry (mirrors architecture layers)
# ─────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
]

PLATFORM_APPS = [
    'app.core',                      # shared base models + audit/attachments
    'app.platform.accounts',         # auth & user management
    'app.platform.companies',        # org + workspace provisioning
    'app.platform.invites',          # invite tokens + onboarding
    'app.platform.licensing',        # seat buckets + enforcement
    'app.platform.modules',          # module registry & company enablement
    'app.platform.flac',             # field-level access control
    'app.platform.subscriptions',    # plans, licensing, billing
    'app.platform.teams',            # org structure (teams/departments)
    'app.platform.onboarding',       # onboarding flow management
]

WORKSPACE_APPS = [
    'app.workspace.sales',           # CRM / pipeline
    'app.workspace.projects',        # Project management
    'app.workspace.tasks',           # Task management
    'app.workspace.support',         # Support & Tickets
    # TODO: add marketing modules as they are created
]

AI_APPS = [
    'app.ai.oneintelligentai',          # AI services / chat endpoints
    # TODO: add ai.recommendations, ai.insights, etc.
]

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + PLATFORM_APPS
    + WORKSPACE_APPS
    + AI_APPS
)


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be at top
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Next.js frontend
    "http://192.168.1.9:3000",
    "http://13.235.73.171",
    "http://192.168.1.9:3000",
    "http://52.66.11.128"
]

# Optional: allow cookies (for CSRF/auth)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = False


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'oneintelligence-db',
        'USER': 'oneintelligence',
        'PASSWORD': 'Onei@123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')  # <-- this is required for collectstatic

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'app.utils.exception_handler.custom_exception_handler',
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "userId",
    "USER_ID_CLAIM": "userId",

    "AUTH_COOKIE": "oi_refresh_token",   # cookie name
    "AUTH_COOKIE_SECURE": not DEBUG,     # HTTPS only in production (False for local dev)
    "AUTH_COOKIE_HTTP_ONLY": True,       # prevent JS access
    "AUTH_COOKIE_SAMESITE": "Lax" if DEBUG else "None",  # Lax for local, None for cross-domain
    "AUTH_COOKIE_PATH": "/",             # cookie scope
}




AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = "users.User"

SPECTACULAR_SETTINGS = {
    "TITLE": "OneIntelligence API",
    "DESCRIPTION": "OneIntelligence Backend API Documentation",
    "VERSION": "1.0.0",

    # MUST be true for Swagger auth to work correctly
    "SERVE_INCLUDE_SCHEMA": True,
    "COMPONENT_SPLIT_REQUEST": True,

    # Security definition for Swagger
    "SECURITY_SCHEMES": {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    },

    # Apply security by default
    "SECURITY": [
        {"bearerAuth": []}
    ],
}

FRONTEND_BASE = "http://localhost:3000"

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')
# =====================
# EMAIL SETTINGS (GMAIL)
# =====================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
# Twilio (optional - for SMS)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
