from django.urls import reverse
from django.test import TestCase
# from unittest import TestCase

# Create your tests here.
# from .models import Question

class AlgusViewTests(TestCase):
   def test_index_view(self):
       response = self.client.get(reverse('special_j6ul2020'))
       self.assertEqual(response.status_code, 200)
       # self.assertContains(response, "No polls are available.")
       # self.assertQuerysetEqual(response.context['latest_question_list'], [])
