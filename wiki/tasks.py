#!/home/ec2-user/django/kroonika_env/bin/python3

#
# Salvestatud kaardivaadete regulaarseks uuendamiseks
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-wiki-app/tasks.py

from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    import os
    import django
    from django.test.utils import setup_test_environment

    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    setup_test_environment()
    from django.conf import settings
    UTIL_DIR = Path(__file__).resolve().parent  / 'utils'
    # Build paths inside the project like this: UTIL_DIR / 'subdir'.
    # print('Töökataloog:', UTIL_DIR)
else:
    from django.conf import settings
    UTIL_DIR = settings.BASE_DIR / 'wiki' / 'utils'

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory

factory = RequestFactory()
# Create an instance of a GET request.
request = factory.get('/')
middleware = SessionMiddleware(lambda x: x)
middleware.process_request(request)
request.session.save()
request.user = AnonymousUser()

try:
    from wiki.utils import shp_util
    from wiki.views import algus
except: # kui käivitatakse lokaalselt
    from utils import shp_util
    from views import algus

if __name__ == '__main__':
    now = datetime.now()
    algus(request)
    if now.minute % 10 == 0: # uuendame iga 10 minuti j2rel
        shp_util.kaardiobjektid2geojson()
