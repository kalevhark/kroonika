"""
WSGI config for kroonika project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
import sys

print(f'Python {sys.version_info[0]}.{sys.version_info[1]}')

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kroonika.settings')

application = get_wsgi_application()
