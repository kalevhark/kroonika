from datetime import datetime
import urllib

from django.urls import reverse
from django.test import TestCase

from wiki.models import Artikkel, Isik

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


class ArtikkelViewTests(TestCase):
    def test_object_exists(self):
        self.assertTrue(Artikkel.objects.filter(kroonika__isnull=True).count() > 0)
        obj = Artikkel.objects.filter(kroonika__isnull=True).first()
        url = urllib.parse.unquote(obj.get_absolute_url())
        self.assertEqual(url, f'/wiki/{obj.id}-{obj.slug}/')

    def test_artikkel_view_show_by_url(self):
        obj = Artikkel.objects.filter(kroonika__isnull=True).first()
        url = f'/wiki/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_artikkel_view_show_by_name(self):
        obj = Artikkel.objects.filter(kroonika__isnull=True).first()
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        response = self.client.get(reverse('wiki:wiki_artikkel_detail', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

    def test_artikkel_view_no_show(self):
        obj = Artikkel.objects.filter(kroonika__isnull=False).first()
        url = f'/wiki/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class IsikViewTests(TestCase):
    test_object_id = 19 # Johannes Märtson

    def test_object_exists(self):
        self.assertEqual(Isik.objects.filter(id=self.test_object_id).count(), 1)
        obj = Isik.objects.get(id=7)
        self.assertEqual(obj.get_absolute_url(), f'/wiki/isik/{obj.id}-{obj.slug}/')

    def test_view_url_exists_at_desired_location(self):
        isik = Isik.objects.get(id=self.test_object_id)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_url_response_time(self):
        time_start = datetime.now()
        isik = Isik.objects.get(id=self.test_object_id)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        _ = self.client.get(url)
        time_stopp = datetime.now() - time_start
        self.assertTrue(time_stopp.seconds < 5)

    def test_view_uses_correct_template(self):
        obj = Isik.objects.get(id=self.test_object_id)
        url = f'/wiki/isik/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wiki/isik_detail.html')

    def test_view_show_by_name(self):
        obj = Isik.objects.get(id=self.test_object_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        response = self.client.get(reverse('wiki:wiki_isik_detail', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

class IlmViewTests(TestCase):
    def test_ilm_view(self):
       response = self.client.get(reverse('ilm:index'))
       self.assertEqual(response.status_code, 200)

    def test_ilm_history_view(self):
       response = self.client.get(reverse('ilm:history'))
       self.assertEqual(response.status_code, 200)
