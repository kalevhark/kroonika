import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'

import django
django.setup()

# from django.conf import settings
# settings.configure()

from django.test.utils import setup_test_environment
setup_test_environment()

from django.test import Client

# create an instance of the client for our use
client = Client()
# get a response from '/'
response = client.get('/')
print(response.status_code)

from django.urls import reverse
response = client.get(reverse('algus'))
print(response.status_code)
print(response.context.keys())