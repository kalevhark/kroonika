import html
from datetime import datetime
import json

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse, resolve

import folium

import wiki.utils.shp_util
from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

from wiki import views, utils
from wiki.models import Objekt, Kaart, Kaardiobjekt

from wiki.tests.test_base import UserTypeUnitTest

class CalendarChoiceTest(UserTypeUnitTest):

    def setUp(self) -> None:
        super().setUp()
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        # self.user = User.objects.get(id=1)
        self.request.user = AnonymousUser()

    def tearDown(self) -> None:
        super().tearDown()

    def test_calendar_choice_getter_empty(self) -> None:
        self.request.GET = {}
        response = views.calendar_days_with_events_in_month(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('days_with_events' in json.loads(response.content).keys())

    def test_calendar_choice_getter_100aastat_tagasi(self) -> None:
        today = datetime.now()
        kwargs = {'year': today.year-100, 'month': today.month}
        self.request.GET = kwargs
        # self.request = self.factory.post(reverse('wiki:calendar_days_with_events_in_month'), {'year': '1922', 'month': '2'})
        response = views.calendar_days_with_events_in_month(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('days_with_events' in json.loads(response.content).keys())

    def test_calendar_choice_getter_empty_parameters(self) -> None:
        # default response
        today = datetime.now()
        kwargs = {'year': today.year-100, 'month': today.month}
        self.request.GET = kwargs
        response = views.calendar_days_with_events_in_month(self.request)
        result_default = json.loads(response.content)

        # empty parameters
        kwargs = {'year': '', 'month': ''}
        self.request.GET = kwargs
        response = views.calendar_days_with_events_in_month(self.request)
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('days_with_events' in result.keys())
        self.assertEqual(result, result_default)

        # empty parameters
        kwargs = {'year': None, 'month': None}
        self.request.GET = kwargs
        response = views.calendar_days_with_events_in_month(self.request)
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('days_with_events' in result.keys())
        self.assertEqual(result, result_default)

        # empty parameters
        kwargs = {'year': 'NaN', 'month': 'NaN'}
        self.request.GET = kwargs
        response = views.calendar_days_with_events_in_month(self.request)
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('days_with_events' in result.keys())
        self.assertEqual(result, result_default)

    def test_calendar_choice_getter_equals_httprequest(self) -> None:
        # default response
        today = datetime.now()
        kwargs = {'year': today.year - 100, 'month': today.month}
        self.request.GET = kwargs
        response = views.calendar_days_with_events_in_month(self.request)
        result_default = json.loads(response.content)

        self.request = self.factory.get('/')
        self.user = AnonymousUser()
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        response = self.client.get(reverse('wiki:calendar_days_with_events_in_month'))
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('days_with_events' in result.keys())
        self.assertEqual(result, result_default)

class LoadObjectListTest(UserTypeUnitTest):

    def setUp(self) -> None:
        super().setUp()
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        # self.user = User.objects.get(id=1)
        self.request.user = AnonymousUser()

    def tearDown(self) -> None:
        super().tearDown()

    def test_get_object_data4tooltip(self) -> None:
        SELECT_COUNT = 10
        # Juhuslikud objectid kontrolliks
        for model in [Artikkel, Isik, Organisatsioon, Objekt]:
            objs = model.objects.order_by('?')[:SELECT_COUNT]
            for obj in objs:
                kwargs = {
                    'model': obj.__class__.__name__,
                    'obj_id': obj.id
                }
                self.request.GET = kwargs
                response = views.get_object_data4tooltip(self.request)
                self.assertEqual(response.status_code, 200)

    def test_artikkel_month_archive_otheryears(self) -> None:
        # random response
        today = datetime.now()
        year = today.year - 100
        month = today.month
        kwargs = {'start': 0}
        self.request.GET = kwargs
        response = views.artikkel_month_archive_otheryears(self.request, year=year, month=month)
        result_random = response.content
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(result_random) > 0)
        self.assertIn('näita veel'.encode('utf8'), result_random)

        kwargs = {'start': 2000}
        self.request.GET = kwargs
        response = views.artikkel_month_archive_otheryears(self.request, year=year, month=month)
        result_overload = response.content
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(result_overload) > 0)
        self.assertIn('Ei leitud midagi'.encode('utf8'), result_overload)
        # self.assertEqual(result_overload, result_random)

class GetLeafletMapTest(UserTypeUnitTest):

    def setUp(self) -> None:
        super().setUp()
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        # self.user = User.objects.get(id=1)
        self.request.user = AnonymousUser()
        self.kaardid = Kaart.objects.exclude(tiles__exact='').order_by('aasta')

    def tearDown(self) -> None:
        super().tearDown()

    def test_get_get_big_maps_default(self) -> None:
        kwargs = {
            'kaardid': self.kaardid,
            'obj': None,
            'aasta': None
        }
        response = wiki.utils.shp_util.get_big_maps_default(**kwargs)
        assert isinstance(response, folium.Map)

    def test_get_get_big_maps_default_year(self) -> None:
        kwargs = {
            'kaardid': self.kaardid,
            'obj': None,
            'aasta': '1683'
        }
        response = wiki.utils.shp_util.get_big_maps_default(**kwargs)
        assert isinstance(response, folium.Map)

    def test_make_objekt_leaflet_combo_objekt_exists(self) -> None:
        objekt = Objekt.objects.get(id=13) # linnakirik
        response = wiki.utils.shp_util.make_objekt_leaflet_combo(objekt=objekt.id)
        assert isinstance(response, str)
        self.assertTrue(len(response) > 0)
        self.assertIn('iframe', response)

    def test_make_objekt_leaflet_combo_objekt_has_kaardiobjekt(self) -> None:
        objekt = Objekt.objects.get(id=8) # raudteejaama-hoone-kuni-1944
        response = wiki.utils.shp_util.make_objekt_leaflet_combo(objekt=objekt.id)
        assert isinstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_make_objekt_leaflet_combo_without_kaardiobjekt(self) -> None:
        objekt = Objekt.objects.get(id=1042) # linnakooli-hoone-1742-1795
        response = wiki.utils.shp_util.make_objekt_leaflet_combo(objekt=objekt.id)
        self.assertEqual(response, None)
