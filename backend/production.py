# printvault/backend/production.py
from .settings import *
import os

DEBUG = False

ALLOWED_HOSTS = ['*']

# These two lines are the definitive fix. They tell Django to trust the
# headers sent by the Tailscale reverse proxy. This ensures that when
# Django generates the full URL for your media files, it correctly
# uses https:// instead of http://.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

# MEDIA_URL should be a relative path.
MEDIA_URL = '/media/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': DB_PASSWORD,
        'HOST': 'db',
        'PORT': '5432',
    }
}

CORS_ALLOW_ALL_ORIGINS = True

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')