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
    def test_all_view_1st_page(self):
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_index_archive'
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_all_view_other_page(self):
        time_start = datetime.now()
        response = self.client.get(
            '/wiki/kroonika/',
            {'page': '5'}
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_all_view_wrong_page(self):
        time_start = datetime.now()
        response = self.client.get(
            '/wiki/kroonika',
            {'page': '5000'}
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 301)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_year_view(self):
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_year_archive',
                kwargs={'year': 1920}
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_month_view(self):
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 2}
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_month_view(self):
        # initial request
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 10}
            )
        )
        time_stopp_initial = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp_initial.seconds < 3, f'Laadimisaeg (initial): {time_stopp_initial.seconds}.{time_stopp_initial.microseconds}')
        # request from cache
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_month_archive',
                kwargs={'year': 1920, 'month': 10}
            )
        )
        time_stopp_from_cache = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp_from_cache < time_stopp_initial, f'initial {time_stopp_from_cache} < from cache {time_stopp_initial}')
        self.assertTrue(time_stopp_from_cache.seconds < 3, f'Laadimisaeg: {time_stopp_from_cache.seconds}.{time_stopp_from_cache.microseconds}')


    def test_day_view(self):
        time_start = datetime.now()
        response = self.client.get(
            reverse(
                'wiki:artikkel_day_archive',
                kwargs={'year': 1920, 'month': 2, 'day': 24}
            )
        )
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')
