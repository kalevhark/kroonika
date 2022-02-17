from datetime import datetime
import time

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

class APITestWikiListingCase(TestCase):
    """
    wiki API Test Case
    """

    def test_allrouters_listing_api(self):
        self.list_api_routers = self.client.get('/api/', format='json')
        self.assertEquals(self.list_api_routers.status_code, 200)
        routers = ['artikkel', 'isik', 'organisatsioon', 'objekt', 'pilt', 'i', 'j']
        for router in routers:
            self.assertTrue(router in self.list_api_routers.json().keys())

    def test_artikkel_listing_api(self):
        count = Artikkel.objects.daatumitega(request=None).count()
        self.list_api_result = self.client.get('/api/artikkel/', format='json')
        self.assertEquals(self.list_api_result.json()["count"], count)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_artikkel_detail_api(self):
        id = 1000
        slug = Artikkel.objects.get(id=id).slug
        self.list_api_result = self.client.get(f'/api/artikkel/{id}/', format='json')
        self.assertEquals(self.list_api_result.json()["slug"], slug)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_isik_listing_api(self):
        count = Isik.objects.daatumitega(request=None).count()
        self.list_api_result = self.client.get('/api/isik/', format='json')
        self.assertEquals(self.list_api_result.json()["count"], count)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_isik_detail_api(self):
        id = 19 # Johannes Märtson
        slug = Isik.objects.get(id=id).slug
        self.list_api_result = self.client.get(f'/api/isik/{id}/', format='json')
        self.assertEquals(self.list_api_result.json()["slug"], slug)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_organisatsioon_listing_api(self):
        count = Organisatsioon.objects.daatumitega(request=None).count()
        self.list_api_result = self.client.get('/api/organisatsioon/', format='json')
        self.assertEquals(self.list_api_result.json()["count"], count)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_organisatsioon_detail_api(self):
        id = 13 # Säde selts
        slug = Organisatsioon.objects.get(id=id).slug
        self.list_api_result = self.client.get(f'/api/organisatsioon/{id}/', format='json')
        self.assertEquals(self.list_api_result.json()["slug"], slug)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_objekt_listing_api(self):
        count = Objekt.objects.daatumitega(request=None).count()
        self.list_api_result = self.client.get('/api/objekt/', format='json')
        self.assertEquals(self.list_api_result.json()["count"], count)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_objekt_detail_api(self):
        id = 13 # Jaani kirik
        slug = Objekt.objects.get(id=id).slug
        self.list_api_result = self.client.get(f'/api/objekt/{id}/', format='json')
        self.assertEquals(self.list_api_result.json()["slug"], slug)
        self.assertEquals(self.list_api_result.status_code, 200)

    def tearDown(self) -> None:
        super().tearDown()
