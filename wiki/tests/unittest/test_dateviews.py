"""
Testid kuupäevavaadete jaoks.
"""
from datetime import datetime
import time
import urllib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

class WikiDateViewTests(TestCase):
    """
    Testid kuupäevavaadete jaoks.
    """

    def test__views__all_view_1st_page(self):
        """
        Testime, et kronoloogiline vaade avaneb alla 3 sekundi.
        
        :param self: TestCase objekt
        """
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_index_archive'
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__all_view_other_page(self):
        """
        Testime, et kronoloogilise vaate valitud lehekülg avaneb alla 3 sekundi.
        
        :param self: TestCase objekt
        """
        time_start = datetime.now()
        response = self.client.get(
            '/wiki/kroonika/',
            {'page': '5'}
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__all_view_wrong_page(self):
        """
        Testime, et kronoloogilise vaate valesti valitud lehekülg suunatakse ümber ja avaneb alla 3 sekundi.
        
        :param self: TestCase objekt
        """
        time_start = datetime.now()
        response = self.client.get(
            '/wiki/kroonika',
            {'page': '5000'}
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 301)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__year_view_without_key_redirect(self):
        """
        Testime, et aasta vaate valitud lehekülg ilma v6ti parameetrita suunatakse ümber.
        
        :param self: TestCase objekt
        """
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_year_archive',
                kwargs={'year': 1920}
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 302)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__session_persistence(self):
        """
        Testime, et sessiooni v6ti püsib aasta vaate vahel samana.

        :param self: TestCase objekt
        """
        self.client.get(reverse('algus'))
        key_one = self.client.session.session_key
        
        self.client.get(reverse(
                'wiki:artikkel_year_archive',
                kwargs={'year': 1920}
            ))
        key_two = self.client.session.session_key

        self.assertEqual(key_one, key_two)


    def test__views__year_view(self):
        """
        Testime, et aasta vaate valitud lehekülg koos v6ti parameetriga avatakse vähem kui 3 sekundiga.
        
        :param self: TestCase objekt
        """
        # Trigger the view
        response = self.client.get(reverse('algus'))
        # 1. Access session via a variable
        session = self.client.session
        session_key = session.session_key
        # 2. Now trigger the year view with the session key
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_year_archive',
                kwargs={
                    'year': 1920,
                }
            ) + f'?v6ti={session_key}'
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__month_view_without_key_redirect(self):
        """
        Testime, et kuu vaate valitud lehekülg ilma v6ti parameetrita suunatakse ümber.
        
        :param self: TestCase objekt
        """
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 2}
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 302)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__month_view_without_cache(self):
        """
        Testime, et kuu vaate valitud lehekülg koos v6ti parameetriga avatakse vahemäluta vähem kui 3 sekundiga.
        
        :param self: TestCase objekt
        """
        # Trigger the view
        response = self.client.get(reverse('algus'))
        # 1. Access session via a variable
        session = self.client.session
        session_key = session.session_key
        # 2. Now trigger the year view with the session key
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 10}
            ) + f'?v6ti={session_key}'
        )
        time_stopp_initial = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp_initial.seconds < 3, f'Laadimisaeg (initial): {time_stopp_initial.seconds}.{time_stopp_initial.microseconds}')


    def test__views__month_view_with_cache(self):
        """
        Testime, et kuu vaate valitud lehekülg koos v6ti parameetriga avatakse vahemälust vähem kui 3 sekundiga.
        
        :param self: TestCase objekt
        """
        # Trigger the view
        response = self.client.get(reverse('algus'))
        # 1. Access session via a variable
        session = self.client.session
        session_key = session.session_key
        # 2. Now trigger the year view with the session key
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 10}
            ) + f'?v6ti={session_key}'
        )
        time_stopp_initial = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        
        # request from cache
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 10}
            ) + f'?v6ti={session_key}'
        )
        time_stopp_from_cache = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp_from_cache < time_stopp_initial, f'initial {time_stopp_from_cache} < from cache {time_stopp_initial}')
        self.assertTrue(time_stopp_from_cache.seconds < 3, f'Laadimisaeg: {time_stopp_from_cache.seconds}.{time_stopp_from_cache.microseconds}')


    def test__views__day_view_without_key_redirect(self):
        """
        Testime, et p2ev vaate valitud lehekülg ilma v6ti parameetrita suunatakse ümber.
        
        :param self: TestCase objekt
        """
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_day_archive',
                kwargs={'year': 1920, 'month': 2, 'day': 24}
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 302)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


    def test__views__day_view_with_key(self):
        # Trigger the view
        response = self.client.get(reverse('algus'))
        # 1. Access session via a variable
        session = self.client.session
        session_key = session.session_key
        # 2. Now trigger the year view with the session key
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_day_archive',
                kwargs={'year': 1920, 'month': 2, 'day': 24}
            ) + f'?v6ti={session_key}'
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')
