#!/home/ec2-user/django/kroonika_env/bin/python3

# Regulaarselt iga minuti tagant käivitatav skript
# 1. Kontroll kas veebiserver status 200
# 2. Anonymoususeri jaoks avakuva cache
# 3. Salvestatud kaardivaadete regulaarseks uuendamiseks (iga 10 minuti järel)
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-wiki-app/tasks.py

from datetime import datetime
from pathlib import Path

import django
from django.conf import settings
import requests

if __name__ == "__main__":
    import os
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    # setup_test_environment()
    UTIL_DIR = Path(__file__).resolve().parent  / 'utils'
else:
    UTIL_DIR = settings.BASE_DIR / 'wiki' / 'utils'

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.mail import send_mail
from django.test import Client, RequestFactory

try:
    from wiki.utils import shp_util
    from wiki.views import algus
except: # kui käivitatakse lokaalselt
    from utils import shp_util
    from views import algus

# kontrollime kas veebiserver annab korrektse vawtuse
def test_status_200():
    response = requests.head('https://valgalinn.ee')
    if response.status_code != 200:
        subject = f'Status = {response.status_code} from valgalinn.ee {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
        message = f'Status = {response.status_code}'
        from_email, to = f'valgalinn.ee <{settings.DEFAULT_FROM_EMAIL}>', 'kalevhark@gmail.com'
        send_mail(
            subject,
            message,
            from_email,
            [to],
            fail_silently=False,
        )

# initsieerime avakuva salvestamise cache
def get_algus():
    factory = RequestFactory()
    # Create an instance of a GET request.
    request = factory.get('/')
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    request.session.save()
    request.user = AnonymousUser()
    algus(request)

if __name__ == '__main__':
    now = datetime.now()
    test_status_200()
    get_algus()
    if now.minute % 10 == 0: # uuendame iga 10 minuti j2rel
        shp_util.kaardiobjektid2geojson()
