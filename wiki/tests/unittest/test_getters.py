from datetime import datetime
import json

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse, resolve

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

from wiki import views

from wiki.tests.test_base import UserTypeUnitTest

class CalendarChoiceTest(UserTypeUnitTest):

    def setUp(self) -> None:
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_calendar_choice_getter_empty(self) -> None:
        # request = self.factory.get('wiki_artikkel_filter')
        self.request.user = self.user
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