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

