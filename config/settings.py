"""
Django settings for OneIntelligence project.
"""
import os
import logging

from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
SALES_AI_MODEL = "gpt-4o-mini"  # set to desired model
SALES_AI_CACHE_TTL = 60 * 60 * 12

# Security: SECRET_KEY from environment variable
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set. Generate one with: openssl rand -hex 32")

# Security: DEBUG from environment variable (defaults to False for production safety)
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Django cache configuration
# In development: Uses local memory cache if Redis is not available
# In production: Uses Redis (must be available)
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")

# Check if Redis is available (only in development)
USE_REDIS = True
if DEBUG:
    try:
        import redis
        r = redis.from_url(REDIS_URL, socket_connect_timeout=1)
        r.ping()
        USE_REDIS = True
    except Exception as e:
        USE_REDIS = False
        logger.warning(f"Redis not available ({type(e).__name__}), using local memory cache for development")

if DEBUG and not USE_REDIS:
    # Development: Use local memory cache when Redis is not available
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "oneintelligence-cache",
            "KEY_PREFIX": "oneintelligence",
            "TIMEOUT": 300,
        }
    }
else:
    # Production or Development with Redis: Use Redis
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,  # Graceful degradation - don't fail if Redis is temporarily unavailable
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {
                    "retry_on_timeout": True,
                    "health_check_interval": 30,
                },
            },
            "KEY_PREFIX": "oneintelligence",
            "TIMEOUT": 300,
        }
    }
    if not DEBUG:
        # Production: Add compression
        CACHES["default"]["OPTIONS"]["COMPRESSOR"] = "django_redis.compressors.zlib.ZlibCompressor"

ALLOWED_HOSTS = [
    '192.168.1.9',
    '127.0.0.1',
    'localhost:3000',
    'localhost',
    '3.109.211.100',
    '13.235.73.171',
    '52.66.11.128',
    '192.168.1.9'
]

# ─────────────────────────────────────────
# Security Headers & Settings
# ─────────────────────────────────────────
# Security: Browser XSS protection
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Security: Frame options (prevent clickjacking)
# Allow SAMEORIGIN for Swagger UI to work properly
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Security: HSTS (HTTP Strict Transport Security) - only in production
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # SECURE_SSL_REDIRECT = True  # Disabled for HTTP access. Enable when HTTPS is configured

# Security: Cookie settings
# Disabled for HTTP access. Enable when HTTPS is configured
SESSION_COOKIE_SECURE = False  # Set to True when HTTPS is configured
CSRF_COOKIE_SECURE = False  # Set to True when HTTPS is configured
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax' if DEBUG else 'None'  # Lax for local, None for cross-domain

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
    'app.platform.consent',
    'app.core',                      # shared base models + audit/attachments
    'app.platform.accounts',         # auth & user management
    'app.platform.companies',        # org + workspace provisioning
    'app.platform.invites',          # invite tokens + onboarding
    'app.platform.licensing',        # seat buckets + enforcement
    'app.platform.products',          # product registry & company enablement
    'app.platform.flac',             # field-level access control
    'app.platform.subscriptions',    # plans, licensing, billing
    'app.platform.teams',            # org structure (teams/departments)
    'app.platform.onboarding',       # onboarding flow management
    'app.platform.rbac',             # role-based access control
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
    "http://127.0.0.1:3000",  # Alternative localhost
    "http://192.168.1.9:3000",
    "http://13.235.73.171",
    "http://52.66.11.128",
    "http://192.168.1.9",
    ]

# Optional: allow cookies (for CSRF/auth)
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = False

# Additional CORS settings for streaming
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


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

# Security: Database credentials from environment variables
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'oneintelligence-db'),
        'USER': os.environ.get('DB_USER', 'oneintelligence'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
        'CONN_MAX_AGE': 600,  # Reuse connections for 10 minutes
    }
}

# Validate critical database credentials in production
if not DEBUG:
    if not os.environ.get('DB_PASSWORD'):
        raise ValueError("DB_PASSWORD environment variable must be set in production")

# Security: Password validators for strong passwords
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # Minimum 8 characters
        }
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
    # Security: API rate limiting
    # Enabled in both development and production
    # Uses cache backend (Redis in production, local memory in dev if Redis unavailable)
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # Anonymous users
        'user': '1000/hour',  # Authenticated users
    },
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

# Twilio SendGrid (for Email)
# Note: SendGrid requires a separate API key from your Twilio account
# Get it from: https://app.sendgrid.com/settings/api_keys
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', DEFAULT_FROM_EMAIL)
