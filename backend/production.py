import os
from .settings import *

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
USE_X_FORWARDED_HOST = True

# Read ALLOWED_HOSTS from environment variable
# Fallback to APP_HOST for backwards compatibility
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split(',')
else:
    # Legacy fallback using APP_HOST
    APP_HOST = os.environ.get('APP_HOST', 'localhost').strip("'").strip('"')
    ALLOWED_HOSTS = [APP_HOST, 'localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': os.environ.get('POSTGRES_USER', 'postgres').strip("'").strip('"'),
        'HOST': 'db',
        'PORT': 5432,
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD').strip("'").strip('"'),
    }
}

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    f"http://{host}" for host in ALLOWED_HOSTS if host not in ["*", "localhost", "127.0.0.1"]
] + [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ["*", "localhost", "127.0.0.1"]
]

# CSRF settings - trust the same origins as ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = [
    f"http://{host}" for host in ALLOWED_HOSTS if host not in ["*", "localhost", "127.0.0.1"]
] + [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ["*", "localhost", "127.0.0.1"]
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')