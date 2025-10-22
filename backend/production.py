import os
from .settings import *

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
USE_X_FORWARDED_HOST = True

# Trust proxy headers (for Tailscale/Nginx HTTPS termination)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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

# Security settings for production
if not DEBUG:
    # Don't force HTTPS redirect (allow both HTTP local access and HTTPS via Tailscale)
    # SECURE_SSL_REDIRECT = False (default)
    
    # Secure cookies - only applied when connection is HTTPS
    # These work per-request, so HTTP requests use regular cookies, HTTPS uses secure cookies
    SESSION_COOKIE_SECURE = False  # Allow both HTTP and HTTPS
    CSRF_COOKIE_SECURE = False     # Allow both HTTP and HTTPS
    
    # HTTP Strict Transport Security (HSTS) - only sent on HTTPS responses
    # Tells browsers to always use HTTPS for this domain (when accessed via HTTPS)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Clickjacking protection
    X_FRAME_OPTIONS = 'DENY'
    
    # Don't expose Django version in headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

# Logging configuration
# Logs are sent to stdout/stderr and captured by Docker
# Access via: docker compose logs backend
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}