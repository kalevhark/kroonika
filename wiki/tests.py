from django.urls import reverse
from django.test import TestCase

class WikiViewTests(TestCase):
    def test_j6ul2020_view(self):
       response = self.client.get(reverse('special_j6ul2020'))
       self.assertEqual(response.status_code, 200)
       self.assertContains(response, "Rahulikke jõule!")
       # self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_algus_view(self):
        response = self.client.get(reverse('algus'))
        self.assertEqual(response.status_code, 200)

class IlmViewTests(TestCase):
    def test_ilm_view(self):
       response = self.client.get(reverse('ilm:index'))
       self.assertEqual(response.status_code, 200)

