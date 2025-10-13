from django.test import TestCase
from django.urls import reverse, resolve

from . import views
from ilm.utils import utils

class WikiBaseUrlTests(TestCase):

    def test_root_url_resolves_to_home_page_view(self):
        found = resolve('/ilm/')
        self.assertEqual(found.func, views.index)

    def test_root_url_resolves_to_history_view(self):
        found = resolve('/ilm/history/')
        self.assertEqual(found.func, views.history)

    def test_root_url_resolves_to_forecasts_view(self):
        found = resolve('/ilm/forecasts/')
        self.assertEqual(found.func, views.forecasts)

    def test_root_url_resolves_to_maxmin_view(self):
        found = resolve('/ilm/maxmin/')
        self.assertEqual(found.func, views.maxmin)


class IlmGetForecastTests(TestCase):

    def test_get_ilmateenistus_forecast(self):
        forecast = utils.get_ilmateenistus_forecast()
        self.assertEqual(type(forecast), dict)

    def test_get_yrno_forecast(self):
        forecast = utils.yrno_forecast()
        self.assertEqual(type(forecast), dict)


class IlmViewTests(TestCase):
    def test_ilm_view(self):
       response = self.client.get(reverse('ilm:index'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_history_view(self):
       response = self.client.get(reverse('ilm:history'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_maxmin_view(self):
       response = self.client.get(reverse('ilm:maxmin'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_forecasts_view(self):
       response = self.client.get(reverse('ilm:forecasts'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_forecasts_with_asukoht_view(self):
        for asukoht in utils.ASUKOHAD.keys():
            response = self.client.get(reverse('ilm:forecasts_with_asukoht', kwargs={'asukoht': asukoht}))
            self.assertEqual(response.status_code, 200)

    def test_ilm_mixed_ilmateade_response(self):
       response = self.client.get(reverse('ilm:mixed_ilmateade'))
       self.assertEqual(response.status_code, 200)


class APITestIlmListingCase(TestCase):
    """
    ilm API Test Case
    """

    def test_ilm_listing_api(self):
        self.list_api_result = self.client.get('/api/i/', format='json')
        self.assertTrue(self.list_api_result.json()["count"] > 0)
        self.assertEqual(self.list_api_result.status_code, 200)

    def test_ilm_now_api(self):
        self.list_api_result = self.client.get('/api/i/now/', format='json')
        self.assertEqual(self.list_api_result.status_code, 200)
        self.assertTrue("airtemperature" in self.list_api_result.json().keys())

    def test_ilm_forecasts_api(self):
        self.list_api_result = self.client.get('/api/i/forecasts/', format='json')
        self.assertEqual(self.list_api_result.status_code, 200)
        self.assertIsInstance(self.list_api_result.json(), dict, msg=self.list_api_result)

    def test_ilm_year_api(self):
        year = 2015
        self.list_api_result = self.client.get('/api/i/', {'y': year}, format='json')
        self.assertEqual(self.list_api_result.status_code, 200)
        count = self.list_api_result.json()["count"]
        self.assertTrue(count == 8759, msg=count)

    def test_ilm_month_api(self):
        year = 2012
        month = 2
        self.list_api_result = self.client.get('/api/i/', {'y': year, 'm': month}, format='json')
        self.assertEqual(self.list_api_result.status_code, 200)
        count = self.list_api_result.json()["count"]
        self.assertTrue(count == 696, msg=count)

    def test_ilm_day_api(self):
        year = 2011
        month = 3
        day = 11
        self.list_api_result = self.client.get('/api/i/', {'y': year, 'm': month, 'd': day}, format='json')
        self.assertEqual(self.list_api_result.status_code, 200)
        count = self.list_api_result.json()["count"]
        self.assertTrue(count == 24, msg=count)


