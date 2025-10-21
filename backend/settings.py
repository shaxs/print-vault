import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-default-key-for-dev"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "inventory",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Tracker file storage configuration
TRACKER_STORAGE = {
    # Storage paths
    'BASE_PATH': os.path.join(MEDIA_ROOT, 'trackers'),
    
    # Size limits
    'MAX_FILE_SIZE': 5 * 1024 * 1024 * 1024,    # 5 GB per file
    'MAX_TOTAL_SIZE': 100 * 1024 * 1024 * 1024, # 100 GB per tracker
    'WARN_THRESHOLD': 1 * 1024 * 1024 * 1024,   # Warn if > 1 GB
    'MIN_FREE_SPACE': 5 * 1024 * 1024 * 1024,   # Require 5 GB free
    
    # Download settings
    'DOWNLOAD_TIMEOUT': 600,      # 10 minutes
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 2,             # Exponential backoff base
    'CHUNK_SIZE': 8192,           # 8 KB chunks
    
    # Features
    'ORGANIZE_BY_CATEGORY': True,  # Create category subfolders
    'VERIFY_CHECKSUMS': False,     # SHA256 verification (slower)
    'CLEANUP_ON_DELETE': True,     # Delete files when tracker deleted
}

# Allowed domains for file downloads (security)
ALLOWED_DOWNLOAD_DOMAINS = [
    'github.com',
    'raw.githubusercontent.com',
    'thingiverse.com',
    'thingiverse-production-new.s3.amazonaws.com',
    'printables.com',
    'media.printables.com',
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True

# Django REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

# Set max upload size to 250MB (250 * 1024 * 1024 bytes)
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144000