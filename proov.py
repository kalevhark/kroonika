from datetime import datetime
import os

import django
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import reverse

os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
django.setup()
setup_test_environment()

# create an instance of the client for our use
client = Client()

from wiki.models import Artikkel, Isik
art = Artikkel.objects.latest('inp_date')
art_url = f'/wiki/{art.id}-{art.slug}/'
isik = Isik.objects.latest('inp_date')
isik_url = f'/wiki/isik/{isik.id}-{isik.slug}/'

urls = [
    '/',
    # '/wiki/kroonika/1922/',
    # '/wiki/kroonika/1922/4/',
    # '/wiki/kroonika/1922/4/20/',
    # art_url,
    # isik_url
]

for url in urls:
    time_start = datetime.now()
    response = client.get(url)
    time_stopp = datetime.now() - time_start
    print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')

pages = [
    'algus',
    'ilm:index',
    'ilm:history',
    'wiki:info',
    'wiki:otsi'
]

for page in pages:
    time_start = datetime.now()
    response = client.get(reverse(page))
    time_stopp = datetime.now() - time_start
    print(page, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
    # print(response.context.keys())

isikud = Isik.objects.all()
for isik in isikud:
    url = f'/wiki/isik/{isik.id}-{isik.slug}/'
    time_start = datetime.now()
    response = client.get(url)
    time_stopp = datetime.now() - time_start
    if response.status_code != 200 or time_stopp.seconds > 1:
        print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
