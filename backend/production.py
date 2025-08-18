import os
from .settings import *

DEBUG = False
USE_X_FORWARDED_HOST = True

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

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')