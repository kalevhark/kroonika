from datetime import datetime
from functools import reduce
from operator import or_
import time
import urllib

import ajax_select
from ajax_select import fields

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki import lookups
from wiki.models import Artikkel, Isik, Organisatsioon, Objekt
from wiki.tests import test_base

CHANNELS = [
    'artiklid',
    'isikud',
    'organisatsioonid',
    'objektid',
    'kaardiobjektid',
    'viited',
    'allikad',
    'pildid'
]
class LookupsUnitTest(TestCase):
    def setUp(self) -> None:
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

    def test_lookup_py_is_autoloaded(self):
        """Django >= 1.7 autoloads tests/lookups.py"""

        for channel in CHANNELS:
            is_registered = ajax_select.registry.is_registered(channel)
            self.assertTrue(is_registered)

    def test_render(self):
        for channel in CHANNELS:
            widget = fields.AutoCompleteSelectMultipleWidget(channel)
            out = widget.render('channel', None)
            print(out)
            self.assertTrue('autocompleteselectmultiple' in out)
            self.assertTrue(channel in out)

    def test_artikkel_lookups(self):
        self.request.user = AnonymousUser()
        lookup = lookups.ArtikkelLookup()
        searches = [
            ('Valga', 50), # max
            ('Müllerson', 50), # max
            ('õõõõõ', 0),
            ('Val linn', 50),  # max
        ]
        for search in searches:
            pattern = search[0]
            expected_count = search[1]
            lookup_query = lookup.get_query(pattern, self.request).count()
            self.assertEqual(lookup_query, expected_count)

    def test_isik_lookups(self):
        self.request.user = AnonymousUser()
        lookup = lookups.IsikLookup()

        searches = [
            ('Jaan', 50), # max
            ('õõõõõ', 0), # None
        ]
        for search in searches:
            pattern = search[0]
            expected_count = search[1]
            lookup_query = lookup.get_query(pattern, self.request).count()
            self.assertEqual(lookup_query, expected_count)

        searches = [
            ('Müllerson', 62),
            ('Kal Här', 1),
            ('märtson', 19),
            ('pär mar', 124),
            ('grün tõn', 31)
        ]
        for search in searches:
            pattern = search[0]
            expected_object = Isik.objects.get(id=search[1])
            lookup_query = lookup.get_query(pattern, self.request)
            self.assertTrue(expected_object in lookup_query)
            self.assertGreater(lookup_query.count(), 0)

    def test_organisatsioon_lookups(self):
        self.request.user = AnonymousUser()
        lookup = lookups.OrganisatsioonLookup()

        searches = [
            ('kool', 50), # max
            ('õõõõõ', 0), # None
        ]
        for search in searches:
            pattern = search[0]
            expected_count = search[1]
            lookup_query = lookup.get_query(pattern, self.request).count()
            self.assertEqual(lookup_query, expected_count)

        searches = [
            ('Säde', 13),
            ('algkool', 44),
            ('gümnaasium', 2777),
            ('alg 3', 97),
            ('tüt güm', 33)
        ]
        for search in searches:
            pattern = search[0]
            expected_object = Organisatsioon.objects.get(id=search[1])
            lookup_query = lookup.get_query(pattern, self.request)
            self.assertTrue(expected_object in lookup_query)
            self.assertGreater(lookup_query.count(), 0)

    def test_objekt_lookups(self):
        self.request.user = AnonymousUser()
        lookup = lookups.ObjektLookup()

        searches = [
            ('tänav', 50), # max
            ('moskva', 50), # max
            ('õõõõõ', 0), # None
        ]
        for search in searches:
            pattern = search[0]
            expected_count = search[1]
            lookup_query = lookup.get_query(pattern, self.request).count()
            self.assertEqual(lookup_query, expected_count)

        searches = [
            ('linnakirik', 13),
            ('raekoda', 23),
            ('poeg güm', 92),
            ('Riia 5', 24),
            ('vas maj',78)
        ]
        for search in searches:
            pattern = search[0]
            expected_object = Objekt.objects.get(id=search[1])
            lookup_query = lookup.get_query(pattern, self.request)
            self.assertTrue(expected_object in lookup_query)
            self.assertGreater(lookup_query.count(), 0)
