from datetime import datetime

from django.urls import reverse
from django.test import TestCase

from wiki.models import Isik

class WikiViewTests(TestCase):
    def test_algus_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('algus'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3)

    def test_info_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('wiki:info'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3)

    def test_j6ul2020_view(self):
       response = self.client.get(reverse('special_j6ul2020'))
       self.assertEqual(response.status_code, 200)
       self.assertContains(response, "Rahulikke jõule!")
       # self.assertQuerysetEqual(response.context['latest_question_list'], [])


class IsikViewTests(TestCase):
    def test_isik_exists(self):
        self.assertEqual(Isik.objects.filter(id=7).count(), 1)
        isik = Isik.objects.get(id=7)
        self.assertEqual(isik.get_absolute_url(), f'/wiki/isik/{isik.id}-{isik.slug}/')

    def test_view_url_exists_at_desired_location(self):
        isik = Isik.objects.get(id=7)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_url_response_time(self):
        time_start = datetime.now()
        isik = Isik.objects.get(id=7)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        _ = self.client.get(url)
        time_stopp = datetime.now() - time_start
        self.assertTrue(time_stopp.seconds < 5)

    def test_view_uses_correct_template(self):
        isik = Isik.objects.get(id=7)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wiki/isik_detail.html')


class IlmViewTests(TestCase):
    def test_ilm_view(self):
       response = self.client.get(reverse('ilm:index'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_history_view(self):
       response = self.client.get(reverse('ilm:history'))
       self.assertEqual(response.status_code, 200)
