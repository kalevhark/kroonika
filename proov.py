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

# get a response from '/'
urls = [
    '/',
    '/wiki/kroonika/1922/',
    '/wiki/kroonika/1922/4/',
    '/wiki/kroonika/1922/4/20'
]

for url in urls:
    response = client.get(url)
    print(response.status_code)

pages = [
    'algus',
    'ilm:index',
    'wiki:info',
    'wiki:otsi'
]

for page in pages:
    response = client.get(reverse(page))
    print(page, response.status_code)
    # print(response.context.keys())