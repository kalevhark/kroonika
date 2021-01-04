from datetime import datetime
from functools import reduce
from operator import or_
import urllib

from django.test import TestCase
from django.urls import reverse

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

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
       self.assertContains(response, "Head uut aastat!")
       # self.assertQuerysetEqual(response.context['latest_question_list'], [])

    # def test_login(self):
    #     response = self.client.login(username='', password='')
    #     self.assertEqual(response, True)
    #     _ = self.client.logout()

class WikiDateViewTests(TestCase):
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
        self.assertTrue(time_stopp.seconds < 3)

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
        self.assertTrue(time_stopp.seconds < 3)

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
        self.assertTrue(time_stopp.seconds < 3)

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

    def test_artikkel_view_show_by_name_random(self):
        SELECT_COUNT = 10
        # Juhuslikud artiklid kontrolliks
        objs = Artikkel.objects.filter(kroonika__isnull=True).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_artikkel_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)

    def test_artikkel_HTTP404_for_non_authented_user(self):
        SELECT_COUNT = 10
        # Juhuslikud artiklid kontrolliks
        objs = Artikkel.objects.filter(kroonika__isnull=False).order_by('?')[:SELECT_COUNT]
        # obj = Artikkel.objects.filter(kroonika__isnull=False).first()
        for obj in objs:
            url = f'/wiki/{obj.id}-{obj.slug}/'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

    def test_artikkel_HTTP404_for_wrong_dateformat(self):
        # Valel kujul kuupäevaotsingud
        urls = [
            '/wiki/kroonika/922/',
            '/wiki/kroonika/11922/',
            '/wiki/kroonika/1922/13/',
            '/wiki/kroonika/1922/4/50/',
            '/wiki/kroonika/1933/2/29/'
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)


class IsikViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.test_object_id = 19 # Johannes Märtson
        # Anonymous user filter
        artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
        self.initial_queryset = Isik.objects.all()
        artikliga = self.initial_queryset. \
            filter(artikkel__in=artikkel_qs). \
            values_list('id', flat=True)
        viitega = self.initial_queryset. \
            filter(viited__isnull=False). \
            values_list('id', flat=True)
        viiteta_artiklita = self.initial_queryset. \
            filter(viited__isnull=True, artikkel__isnull=True). \
            values_list('id', flat=True)
        self.model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])

    def test_object_exists(self):
        self.assertEqual(Isik.objects.filter(id=self.test_object_id).count(), 1)
        obj = Isik.objects.get(id=self.test_object_id)
        url = urllib.parse.unquote(obj.get_absolute_url())
        self.assertEqual(url, f'/wiki/isik/{obj.id}-{obj.slug}/')

    def test_view_url_exists_at_desired_location(self):
        isik = Isik.objects.get(id=self.test_object_id)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        url = '/wiki/isik/19-johannes-märtson/'
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

    def test_view_show_by_name_random(self):
        SELECT_COUNT = 10
        # Juhuslikud isikud kontrolliks
        objs = self.initial_queryset.filter(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_isik_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)

    def test_view_HTTP404_for_non_authented_user(self):
        SELECT_COUNT = 10
        # Juhuslikud isikud kontrolliks
        objs = self.initial_queryset.exclude(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_isik_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 404)

    def test_view_HTTP404_for_wrong_query(self):
        # Valel kujul otsingud
        urls = [
            f'/wiki/isik/{self.test_object_id}/',
            '/wiki/isik/{self.test_object_id}-mingi-suvanimi',
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)


class OrganisatsioonViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.test_object_id = 13 # Säde selts
        # Anonymous user filter
        artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
        self.initial_queryset = Organisatsioon.objects.all()
        artikliga = self.initial_queryset. \
            filter(artikkel__in=artikkel_qs). \
            values_list('id', flat=True)
        viitega = self.initial_queryset. \
            filter(viited__isnull=False). \
            values_list('id', flat=True)
        viiteta_artiklita = self.initial_queryset. \
            filter(viited__isnull=True, artikkel__isnull=True). \
            values_list('id', flat=True)
        self.model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])

    def test_object_exists(self):
        self.assertEqual(Organisatsioon.objects.filter(id=self.test_object_id).count(), 1)
        obj = Organisatsioon.objects.get(id=self.test_object_id)
        url = urllib.parse.unquote(obj.get_absolute_url())
        self.assertEqual(url, f'/wiki/organisatsioon/{obj.id}-{obj.slug}/')

    def test_view_url_exists_at_desired_location(self):
        obj = Organisatsioon.objects.get(id=self.test_object_id)
        url = f'/wiki/organisatsioon/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_url_response_time(self):
        time_start = datetime.now()
        obj = Organisatsioon.objects.get(id=self.test_object_id)
        url = f'/wiki/organisatsioon/{obj.id}-{obj.slug}/'
        _ = self.client.get(url)
        time_stopp = datetime.now() - time_start
        self.assertTrue(time_stopp.seconds < 5)

    def test_view_uses_correct_template(self):
        obj = Organisatsioon.objects.get(id=self.test_object_id)
        url = f'/wiki/organisatsioon/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wiki/organisatsioon_detail.html')

    def test_view_show_by_name(self):
        obj = Organisatsioon.objects.get(id=self.test_object_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        response = self.client.get(reverse('wiki:wiki_organisatsioon_detail', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

    def test_view_show_by_name_random(self):
        SELECT_COUNT = 10
        # Juhuslikud objektid kontrolliks
        objs = self.initial_queryset.filter(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_organisatsioon_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)

    def test_view_HTTP404_for_non_authented_user(self):
        SELECT_COUNT = 10
        # Juhuslikud objektid kontrolliks
        objs = self.initial_queryset.exclude(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_organisatsioon_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 404)

    def test_view_HTTP404_for_wrong_query(self):
        # Valel kujul otsingud
        urls = [
            f'/wiki/organisatsioon/{self.test_object_id}/',
            '/wiki/organisatsioon/{self.test_object_id}-mingi-suvanimi',
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)


class ObjektViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.test_object_id = 68 # Säde seltsimaja
        # Anonymous user filter
        artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
        self.initial_queryset = Objekt.objects.all()
        artikliga = self.initial_queryset. \
            filter(artikkel__in=artikkel_qs). \
            values_list('id', flat=True)
        viitega = self.initial_queryset. \
            filter(viited__isnull=False). \
            values_list('id', flat=True)
        viiteta_artiklita = self.initial_queryset. \
            filter(viited__isnull=True, artikkel__isnull=True). \
            values_list('id', flat=True)
        self.model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])

    def test_object_exists(self):
        self.assertEqual(Objekt.objects.filter(id=self.test_object_id).count(), 1)
        obj = Objekt.objects.get(id=self.test_object_id)
        url = urllib.parse.unquote(obj.get_absolute_url())
        self.assertEqual(url, f'/wiki/objekt/{obj.id}-{obj.slug}/')

    def test_view_url_exists_at_desired_location(self):
        obj = Objekt.objects.get(id=self.test_object_id)
        url = f'/wiki/objekt/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_view_url_response_time(self):
        time_start = datetime.now()
        obj = Objekt.objects.get(id=self.test_object_id)
        url = f'/wiki/objekt/{obj.id}-{obj.slug}/'
        _ = self.client.get(url)
        time_stopp = datetime.now() - time_start
        self.assertTrue(time_stopp.seconds < 5)

    def test_view_uses_correct_template(self):
        obj = Objekt.objects.get(id=self.test_object_id)
        url = f'/wiki/objekt/{obj.id}-{obj.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'wiki/objekt_detail.html')

    def test_view_show_by_name(self):
        obj = Objekt.objects.get(id=self.test_object_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        response = self.client.get(reverse('wiki:wiki_objekt_detail', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)

    def test_view_show_by_name_random(self):
        SELECT_COUNT = 10
        # Juhuslikud objektid kontrolliks
        objs = self.initial_queryset.filter(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_objekt_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)

    def test_view_HTTP404_for_non_authented_user(self):
        SELECT_COUNT = 10
        # Juhuslikud objektid kontrolliks
        objs = self.initial_queryset.exclude(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            response = self.client.get(reverse('wiki:wiki_objekt_detail', kwargs=kwargs))
            self.assertEqual(response.status_code, 404)

    def test_view_HTTP404_for_wrong_query(self):
        # Valel kujul otsingud
        urls = [
            f'/wiki/objekt/{self.test_object_id}/',
            '/wiki/objekt/{self.test_object_id}-mingi-suvanimi',
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)


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

    def test_filter_objekt_for_non_authented_user(self):
        response = self.client.get('/wiki/objekt/', {'nimi__icontains': 'säde', 't2nav_sisaldab': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['object_list']), 2)


from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.chrome.webdriver import WebDriver

class MySeleniumTests(StaticLiveServerTestCase):
    # fixtures = ['user-data.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_login(self):
        from selenium.webdriver.support.wait import WebDriverWait
        timeout = 2
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.selenium.find_element_by_name("username")
        username_input.send_keys('admin')
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys('kr00nika')
        self.selenium.find_element_by_xpath('//input[@value="login"]').click()
        # Wait until the response is received
        WebDriverWait(self.selenium, timeout).until(
            lambda driver: driver.find_element_by_tag_name('body'))