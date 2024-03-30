from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

class FilterViewTests(TestCase):
    # def setUp(self):
    #     # Every test needs access to the request factory.
    #     self.test_object_id = 68 # Säde seltsimaja
    #     # Anonymous user filter
    #     artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
    #     self.initial_queryset = Objekt.objects.all()
    #     artikliga = self.initial_queryset. \
    #         filter(artikkel__in=artikkel_qs). \
    #         values_list('id', flat=True)
    #     viitega = self.initial_queryset. \
    #         filter(viited__isnull=False). \
    #         values_list('id', flat=True)
    #     viiteta_artiklita = self.initial_queryset. \
    #         filter(viited__isnull=True, artikkel__isnull=True). \
    #         values_list('id', flat=True)
    #     self.model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])

    def test_filter_artikkel_artikkel_sisaldab_for_non_authented_user(self):
        response = self.client.get('/wiki/', {'artikkel_sisaldab': 'Märtson'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Kas Johannes Märtson on leitav
        response = self.client.get(
            '/wiki/',
            {
                'hist_year': '',
                'artikkel_sisaldab': 'Märtson',
                'nimi_sisaldab': ''
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Mitu Kalev Härki sisaldavat artiklit leitakse
        response = self.client.get(
            '/wiki/',
            {
                'hist_year': '',
                'artikkel_sisaldab': 'Kalev Härk',
                'nimi_sisaldab': ''
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 1)

    def test_filter_artikkel_nimi_sisaldab_for_non_authented_user(self):
        response = self.client.get('/wiki/', {'nimi_sisaldab': 'Märtson'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Kas Johannes Märtson on leitav
        response = self.client.get(
            '/wiki/',
            {
                'hist_year': '',
                'artikkel_sisaldab': '',
                'nimi_sisaldab': 'Märtson'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Mitu Kalev Härki sisaldavat artiklit leitakse
        response = self.client.get(
            '/wiki/',
            {
                'hist_year': '',
                'artikkel_sisaldab': '',
                'nimi_sisaldab': 'Kalev Härk'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)

    def test_filter_artikkel_hist_year_for_non_authented_user(self):
        response = self.client.get('/wiki/', {'hist_year': '1971'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Kas 1971 on leitav
        response = self.client.get(
            '/wiki/',
            {
                'hist_year': '1971',
                'artikkel_sisaldab': '',
                'nimi_sisaldab': ''
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Kas 1000 on leitav
        response = self.client.get(
            '/wiki/',
            {
                'hist_year': '1000',
                'artikkel_sisaldab': '',
                'nimi_sisaldab': ''
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 0)

    def test_filter_isik_for_non_authented_user(self):
        response = self.client.get('/wiki/isik/', {'nimi_sisaldab': 'märtson'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 0)
        # Kas Johannes Märtson on leitav
        response = self.client.get(
            '/wiki/isik/',
            {
                'eesnimi__icontains': 'johannes',
                'perenimi__icontains': 'märtson',
                'nimi_sisaldab': ''
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)
        # Mitu Härki leitakse
        response = self.client.get(
            '/wiki/isik/',
            {
                'eesnimi__icontains': '',
                'perenimi__icontains': '',
                'nimi_sisaldab': 'härk'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['object_list']) > 1)

    def test_filter_organisatsioon_for_non_authented_user(self):
        response = self.client.get('/wiki/organisatsioon/', {'nimi_sisaldab': 'säde selts'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)

    def test_filter_objekt_for_non_authented_user(self):
        response = self.client.get('/wiki/objekt/', {'nimi_sisaldab': 'linnakirik'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 1)
