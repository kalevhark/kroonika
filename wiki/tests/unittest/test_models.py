from datetime import datetime
from functools import reduce
from operator import or_
import time
import urllib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import QueryDict
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki import views
from wiki.models import Artikkel, Isik, Organisatsioon, Objekt
from wiki.tests import test_base

from django.conf import settings as django_settings
from django.test import TestCase
from django.urls import reverse


class SwitchCalendarSystemTestCase(TestCase):
    def setUp(self) -> None:
        # GIVEN
        self.CALENDAR_SYSTEM_VKJ = 'vkj'
        self.CALENDAR_SYSTEM_UKJ = 'ukj'

    def test_switch_calendar_system_ukj_on_if_initial_empty(self):
        """Verify if view returns session variable and set new."""
        session = self.client.session
        # session["ukj"] = self.CALENDAR_SYSTEM_VKJ
        session.save()

        # Update session's cookie
        session_cookie_name = django_settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie_name] = session.session_key

        # WHEN
        response = self.client.get(reverse("wiki:switch_vkj_ukj", kwargs={"calendar_system": self.CALENDAR_SYSTEM_UKJ}))

        # THEN
        assert bytes.decode(response.content, 'utf8') == str(self.CALENDAR_SYSTEM_UKJ)
        assert self.client.session["calendar_system"] == self.CALENDAR_SYSTEM_UKJ

    def test_switch_calendar_system_ukj_on(self):
        """Verify if view returns session variable and set new."""
        session = self.client.session
        session["calendar_system"] = self.CALENDAR_SYSTEM_VKJ
        session.save()

        # Update session's cookie
        session_cookie_name = django_settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie_name] = session.session_key

        # WHEN
        response = self.client.get(reverse("wiki:switch_vkj_ukj", kwargs={"calendar_system": self.CALENDAR_SYSTEM_UKJ}))

        # THEN
        assert bytes.decode(response.content, 'utf8') == str(self.CALENDAR_SYSTEM_UKJ)
        assert self.client.session["calendar_system"] == self.CALENDAR_SYSTEM_UKJ

    def test_switch_calendar_system_ukj_off(self):
        """Verify if view returns session variable and set new."""
        session = self.client.session
        session["calendar_system"] = self.CALENDAR_SYSTEM_UKJ
        session.save()

        # Update session's cookie
        session_cookie_name = django_settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie_name] = session.session_key

        # WHEN
        response = self.client.get(reverse("wiki:switch_vkj_ukj", kwargs={"calendar_system": self.CALENDAR_SYSTEM_VKJ}))

        # THEN
        assert bytes.decode(response.content, 'utf8') == str(self.CALENDAR_SYSTEM_VKJ)
        assert self.client.session["calendar_system"] == self.CALENDAR_SYSTEM_VKJ

class ArtikkelQuersSetUnitTest(TestCase):
    def setUp(self) -> None:
        # calendar systems
        self.CALENDAR_SYSTEM_VKJ = 'vkj'
        self.CALENDAR_SYSTEM_UKJ = 'ukj'

        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user_admin = User.objects.get(id=1)
        self.user_anonymous = AnonymousUser()

    def test_artikkel_queryset_with_different_user_types(self):
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous
        objects = Artikkel.objects.daatumitega(self.request)
        self.assertTrue(len(objects) > 0)
        objects_count_anonymous = len(objects)
        # admin user queryset not empty
        self.request.user = self.user_admin
        objects = Artikkel.objects.daatumitega(self.request)
        self.assertTrue(len(objects) > 0)
        objects_count_admin = len(objects)
        # admin queryset bigger than anonymous queryset
        self.assertTrue(objects_count_anonymous <= objects_count_admin)

    def test_artikkel_queryset_with_different_calendar_systems(self):
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous
        objects = Artikkel.objects.daatumitega(self.request)
        self.assertTrue(len(objects) > 0)
        objects_count_anonymous = len(objects)
        # admin user queryset not empty
        self.request.user = self.user_admin
        objects = Artikkel.objects.daatumitega(self.request)
        self.assertTrue(len(objects) > 0)
        objects_count_admin = len(objects)
        # admin queryset bigger than anonymous queryset
        self.assertTrue(objects_count_anonymous <= objects_count_admin)


class CalendarSystemQuerysetTestCase(TestCase):
    def setUp(self) -> None:
        # GIVEN
        self.CALENDAR_SYSTEM_VKJ = 'vkj'
        self.CALENDAR_SYSTEM_UKJ = 'ukj'

        self.user_admin = User.objects.get(id=1)
        self.user_anonymous = AnonymousUser()

    def test_calendar_system_ukj_queryset_not_empty(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)

        for user in [self.user_admin, self.user_anonymous]:
            for calendar_system in [self.CALENDAR_SYSTEM_UKJ, self.CALENDAR_SYSTEM_VKJ]:
                # set user
                self.request.user = user

                # set calendar system
                self.request.session["calendar_system"] = calendar_system
                self.request.session.save()

                # Update session's cookie
                session_cookie_name = django_settings.SESSION_COOKIE_NAME
                self.client.cookies[session_cookie_name] = self.request.session.session_key

                # V2hemalt yks tulemus, mis on Artikkel
                art = Artikkel.objects.daatumitega(self.request).first()
                self.assertIsInstance(art, Artikkel)

    def test_calendar_system_ukj_queryset_order(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)

        Y = 1889 # testaasta
        M = 1 # jaanuar
        artikkel_0 = Artikkel.objects.filter(hist_year=Y).filter(hist_month__isnull=True).filter(
            hist_date__isnull=True).first()
        artikkel_1 = Artikkel.objects.filter(hist_year=Y).filter(hist_month=M).filter(
            hist_date__isnull=True).first()
        artikkel_2 = Artikkel.objects.filter(hist_year=Y).filter(hist_month=M).filter(
            hist_date__isnull=False).first()
        artikkel_3 = Artikkel.objects.filter(hist_year=Y).filter(hist_month=M + 1).filter(
            hist_date__isnull=True).first()
        artikkel_4 = Artikkel.objects.filter(hist_year=Y).filter(hist_month=M + 1).filter(
            hist_date__isnull=False).first()
        ordered_expected = [artikkel_0, artikkel_1, artikkel_2, artikkel_3, artikkel_4]

        for user in [self.user_admin, self.user_anonymous]:
            for calendar_system in [self.CALENDAR_SYSTEM_UKJ, self.CALENDAR_SYSTEM_VKJ]:
                # set user
                self.request.user = user

                # set calendar system
                self.request.session["calendar_system"] = calendar_system
                self.request.session.save()

                # Update session's cookie
                session_cookie_name = django_settings.SESSION_COOKIE_NAME
                self.client.cookies[session_cookie_name] = self.request.session.session_key

                ordered_tested = []
                # testime kas 6iges j2rjekorras
                artiklid = Artikkel.objects.daatumitega(self.request).filter(hist_year=Y)
                for artikkel in artiklid:
                    if artikkel in ordered_expected:
                        ordered_tested.append(artikkel)
                self.assertEqual(len(ordered_tested), 5)
                self.assertEqual(
                    ordered_tested,
                    ordered_expected,
                    msg=f'user:{user} kalender:{calendar_system} expect: test:{[art.id for art in ordered_expected]} test:{[art.id for art in ordered_tested]}'
                )
