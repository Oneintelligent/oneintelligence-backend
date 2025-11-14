"""
Django settings for OneIntelligence project.
"""
import os

from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-placeholder-key'
DEBUG = True
ALLOWED_HOSTS = ['192.168.1.9', '127.0.0.1', 'localhost:3000', 'localhost', '3.109.211.100', '13.235.73.171', '52.66.11.128']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'app.onboarding.users',
    'app.onboarding.companies',
    'app.subscriptions',
    'app.onboarding.invites',
    'app.products',
    'app.oneintelligentai',  # <--- THIS LINE IS CRUCIAL
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist', 


]

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

CORS_ALLOW_ALL_ORIGINS = True


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
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "userId",
    "USER_ID_CLAIM": "userId",

    "AUTH_COOKIE": "oi_refresh_token",   # cookie name
    "AUTH_COOKIE_SECURE": False,          # HTTPS only (turn off for local dev)
    "AUTH_COOKIE_HTTP_ONLY": True,       # prevent JS access
    "AUTH_COOKIE_SAMESITE": "None",      # needed for cross-domain FE
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

    # 👇 THIS IS THE IMPORTANT PART
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,

    "SECURITY": [
        {
            "bearerAuth": []
        }
    ],

    "SECURITY_SCHEMES": {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    },
}

