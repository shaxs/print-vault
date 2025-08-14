# printvault/backend/wsgi.py
"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# This file will now correctly use the DJANGO_SETTINGS_MODULE environment
# variable set in the docker-compose.yml file.
# The incorrect os.environ.setdefault line has been removed.

application = get_wsgi_application()