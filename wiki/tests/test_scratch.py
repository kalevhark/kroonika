from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

from wiki import views

class V6rdleTest(TestCase):
    def setUp(self) -> None:
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

    def test_v6rdle_view(self):
        response = self.client.post(reverse('wiki:v6rdle'), follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse('wiki:v6rdle'),
            {'vasak_object': '19', 'parem_object': '20'},
            follow = True
        )
        self.assertEqual(response.status_code, 200)
        # TODO: See ei n2ita tegelikult midagi!
