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

urls = [
    '/',
    # '/wiki/kroonika/1922/',
    # '/wiki/kroonika/1922/4/',
    # '/wiki/kroonika/1922/4/20/',
]

for url in urls:
    time_start = datetime.now()
    response = client.get(url)
    time_stopp = datetime.now() - time_start
    print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')

pages = [
    'algus',
    'wiki:info',
    'wiki:otsi',
    'ilm:index',
    'ilm:history',
    'ilm:mixed_ilmateade',
]

print('Kontrollime põhilinke:')
for page in pages:
    time_start = datetime.now()
    response = client.get(reverse(page))
    time_stopp = datetime.now() - time_start
    print(page, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
    # print(response.context.keys())

print('Kontrollime avalikult nähtavate artikleid:')
objs = Artikkel.objects.filter(kroonika__isnull=True)
OK = objs.count()
NOK = 0
for obj in objs:
    url = f'/wiki/{obj.id}-{obj.slug}/'
    time_start = datetime.now()
    response = client.get(url)
    time_stopp = datetime.now() - time_start
    if response.status_code != 200 or time_stopp.seconds > 1:
        NOK += 1
        print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
print(f'Avalikud ariklid NOK: {NOK}/{OK}')

objs = Artikkel.objects.filter(kroonika__isnull=False)
OK = objs.count()
NOK = 0
for obj in objs:
    url = f'/wiki/{obj.id}-{obj.slug}/'
    response = client.get(url)
    if response.status_code != 404:
        NOK += 1
        print(url, response.status_code)
print(f'Mitteavalikud ariklid NOK: {NOK}/{OK}')

# isikud = Isik.objects.all()
# for isik in isikud:
#     url = f'/wiki/isik/{isik.id}-{isik.slug}/'
#     time_start = datetime.now()
#     response = client.get(url)
#     time_stopp = datetime.now() - time_start
#     if response.status_code != 200 or time_stopp.seconds > 1:
#         print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
