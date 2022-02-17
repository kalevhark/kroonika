from django.test import TestCase
from django.urls import reverse

class IlmViewTests(TestCase):
    def test_ilm_view(self):
       response = self.client.get(reverse('ilm:index'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_history_view(self):
       response = self.client.get(reverse('ilm:history'))
       self.assertEqual(response.status_code, 200)

    # def test_ilm_mixed_ilmateade_response(self):
    #    response = self.client.get(reverse('ilm:mixed_ilmateade'))
    #    self.assertEqual(response.status_code, 200)


class APITestIlmListingCase(TestCase):
    """
    ilm API Test Case
    """

    def test_ilm_listing_api(self):
        self.list_api_result = self.client.get('/api/i/', format='json')
        self.assertTrue(self.list_api_result.json()["count"] > 0)
        self.assertEquals(self.list_api_result.status_code, 200)

    def test_ilm_now_api(self):
        self.list_api_result = self.client.get('/api/i/now/', format='json')
        self.assertEquals(self.list_api_result.status_code, 200)
        self.assertTrue("airtemperature" in self.list_api_result.json().keys())

    def test_ilm_forecasts_api(self):
        self.list_api_result = self.client.get('/api/i/forecasts/', format='json')
        self.assertEquals(self.list_api_result.status_code, 200)
        self.assertTrue(len(self.list_api_result.json().keys()) > 0)

    def test_ilm_year_api(self):
        year = 2015
        self.list_api_result = self.client.get('/api/i/', {'y': year}, format='json')
        self.assertEquals(self.list_api_result.status_code, 200)
        self.assertTrue(self.list_api_result.json()["count"] == 8759)

    def test_ilm_month_api(self):
        year = 2012
        month = 2
        self.list_api_result = self.client.get('/api/i/', {'y': year, 'm': month}, format='json')
        self.assertEquals(self.list_api_result.status_code, 200)
        self.assertTrue(self.list_api_result.json()["count"] == 696)

    def test_ilm_day_api(self):
        year = 2011
        month = 3
        day = 11
        self.list_api_result = self.client.get('/api/i/', {'y': year, 'm': month, 'd': day}, format='json')
        self.assertEquals(self.list_api_result.status_code, 200)
        self.assertTrue(self.list_api_result.json()["count"] == 24)


