from ast import Is
from datetime import date, datetime
from functools import reduce
from operator import or_
import time
import urllib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.db.models import F
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

    def test_date_transform_vkj(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous
        
        # set calendar system to UKJ
        self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_VKJ
        self.request.session.save()
        # Update session's cookie
        session_cookie_name = django_settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie_name] = self.request.session.session_key
        
        for model in [Artikkel, Isik, Organisatsioon, Objekt]:
            count_with_year = model.objects.daatumitega(self.request).filter(yob__gt=F('hist_year')).count()
            count_with_dob = model.objects.daatumitega(self.request).filter(dob__year__gt=F('hist_year')).count()
            msg=f'model {model.__name__} calendar_system: {self.CALENDAR_SYSTEM_VKJ} count_with_year:{count_with_year} count_with_dob:{count_with_dob}'
            self.assertEqual(count_with_year, 0, msg=msg)
            self.assertEqual(count_with_dob, 0, msg=msg)
            self.assertEqual(count_with_year, count_with_dob, msg=msg)

    def test_date_transform_ukj(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous
        
        # set calendar system to UKJ
        self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_UKJ
        self.request.session.save()
        # Update session's cookie
        session_cookie_name = django_settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie_name] = self.request.session.session_key

        for model in [
            Artikkel, 
            Isik, 
            # Organisatsioon, # ei saa testida, sest sobivaid testitavaid ei ole
            # Objekt, # ei saa testida, sest sobivaid testitavaid ei ole
        ]:
            count_with_year = model.objects.daatumitega(self.request).filter(yob__gt=F('hist_year')).count()
            count_with_dob = model.objects.daatumitega(self.request).filter(dob__year__gt=F('hist_year')).count()
            msg=f'model {model.__name__} calendar_system: {self.CALENDAR_SYSTEM_UKJ} count_with_year:{count_with_year} count_with_dob:{count_with_dob}'
            self.assertTrue(count_with_year > 0, msg=msg)
            self.assertTrue(count_with_dob > 0, msg=msg)
            self.assertEqual(count_with_year, count_with_dob, msg=msg)
    
    def test_calendar_system_transform_artikkel(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        
        art_ids = {
            613: {'vkj': datetime(1918, 1, 31), 'ukj': datetime(1918, 2, 13)},
            3358: {'vkj': datetime(1918, 1, 30), 'ukj': datetime(1918, 2, 12)},
            5693: {'vkj': datetime(1918, 2, 19), 'ukj': datetime(1918, 2, 19)}
        }
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous

        for id in art_ids.keys():
            # set calendar system
            self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_VKJ
            self.request.session.save()
            # Update session's cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie_name] = self.request.session.session_key
            art_vkj_date = Artikkel.objects.daatumitega(self.request).get(id=id).dob

            # set calendar system
            self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_UKJ
            self.request.session.save()
            # Update session's cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie_name] = self.request.session.session_key
            art_ukj_date = Artikkel.objects.daatumitega(self.request).get(id=id).dob

            self.assertEqual(art_vkj_date.day, art_ids[id]['vkj'].day, msg=f'vkj {art_vkj_date} {art_ids[id]["vkj"]}')
            self.assertEqual(art_ukj_date.day, art_ids[id]['ukj'].day, msg=f'ukj {art_ukj_date} {art_ids[id]["ukj"]}')

    def test_calendar_system_transform_isik(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        
        test_ids = {
            715: {'vkj': datetime(1875, 12, 19), 'ukj': datetime(1875, 12, 31)}, # /wiki/isik/715-peeter-pähkel/
            647: {'vkj': datetime(1911, 12, 19), 'ukj': datetime(1912, 1, 1)}, # /wiki/isik/647-nikolai-kuks/
        }
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous

        for id in test_ids.keys():
            # set calendar system
            self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_VKJ
            self.request.session.save()
            # Update session's cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie_name] = self.request.session.session_key
            isik_vkj_date = Isik.objects.daatumitega(self.request).get(id=id).dob

            # set calendar system
            self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_UKJ
            self.request.session.save()
            # Update session's cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie_name] = self.request.session.session_key
            isik_ukj_date = Isik.objects.daatumitega(self.request).get(id=id).dob

            self.assertEqual(isik_vkj_date.day, test_ids[id]['vkj'].day, msg=f'vkj {isik_vkj_date} {test_ids[id]["vkj"]}')
            self.assertEqual(isik_vkj_date.month, test_ids[id]['vkj'].month, msg=f'vkj {isik_vkj_date} {test_ids[id]["vkj"]}')
            self.assertEqual(isik_vkj_date.year, test_ids[id]['vkj'].year, msg=f'vkj {isik_vkj_date} {test_ids[id]["vkj"]}')
            self.assertEqual(isik_ukj_date.day, test_ids[id]['ukj'].day, msg=f'ukj {isik_ukj_date} {test_ids[id]["ukj"]}')
            self.assertEqual(isik_ukj_date.month, test_ids[id]['ukj'].month, msg=f'ukj {isik_ukj_date} {test_ids[id]["ukj"]}')
            self.assertEqual(isik_ukj_date.year, test_ids[id]['ukj'].year, msg=f'ukj {isik_ukj_date} {test_ids[id]["ukj"]}')

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
                # set user anonymous
                self.request.user = self.user_anonymous

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

    def test_daatumitega_manager_sel_kuul(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        
        test_ids = {
            84: {'vkj': datetime(1915, 1, 29), 'ukj': datetime(1915, 2, 11)}, # /wiki/objekt/84-elektrijaam/
        }
        # anonymous user queryset not empty
        self.request.user = self.user_anonymous

        for id in test_ids.keys():
            # set calendar system
            self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_VKJ
            self.request.session.save()
            # Update session's cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie_name] = self.request.session.session_key
            # test dob == vkj
            objekt = Objekt.objects.daatumitega(self.request).get(id=id)
            objekt_vkj_date = objekt.dob
            self.assertEqual(objekt_vkj_date.month, test_ids[id]['vkj'].month, msg=f'vkj {objekt_vkj_date} {test_ids[id]["vkj"]}')
            # test obj in objs sel kuul vkj
            objekts_sel_kuul = Objekt.objects.sel_kuul(
                self.request, 
                test_ids[id]["vkj"].month
            )
            self.assertTrue(objekt in objekts_sel_kuul)

            # set calendar system
            self.request.session["calendar_system"] = self.CALENDAR_SYSTEM_UKJ
            self.request.session.save()
            # Update session's cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie_name] = self.request.session.session_key
            # test dob == ukj
            objekt_ukj_date = Objekt.objects.daatumitega(self.request).get(id=id).dob
            self.assertEqual(objekt_ukj_date.month, test_ids[id]['ukj'].month, msg=f'ukj {objekt_ukj_date} {test_ids[id]["ukj"]}')
            # test obj in objs sel kuul ukj
            objekts_sel_kuul = Objekt.objects.sel_kuul(
                self.request, 
                test_ids[id]["ukj"].month
            )
            self.assertTrue(objekt in objekts_sel_kuul)
