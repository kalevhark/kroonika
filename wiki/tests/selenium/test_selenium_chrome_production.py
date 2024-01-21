from datetime import datetime
import time

from django.apps import apps
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

from .base import SeleniumTestsChromeBase
from .test_selenium_chrome import SeleniumTestsChromeOtsi, SeleniumTestsChromeOtsiGetNextResults

from django.http import HttpRequest


class SeleniumTestsChromeProductionOtsi(SeleniumTestsChromeOtsi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host_tobe_tested = 'https://valgalinn.ee'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_otsi(self):
        super().test_otsi()

# class SeleniumTestsChromeProductionOtsi(SeleniumTestsChromeBase):
#
#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#
#     @classmethod
#     def tearDownClass(cls):
#         super().tearDownClass()
#
#     def test_otsi(self):
#         self.selenium.get('https://valgalinn.ee')
#         self.selenium.get('https://valgalinn.ee/wiki/otsi/')
#
#         el = self.selenium.find_element(By.ID, "answer").text
#         self.assertIn("Otsimiseks", el)
#
#         search_input = self.selenium.find_element(By.ID, "question")
#         search_input.send_keys('ta')
#         try:
#             WebDriverWait(self.selenium, timeout=3).until(
#                 EC.text_to_be_present_in_element((By.ID, "answer"), "Vähemalt")
#             )
#         except TimeoutException:
#             pass
#         el = self.selenium.find_element(By.ID, "answer").text
#         self.assertIn("Vähemalt", el)
#
#         search_input.send_keys('mm')
#         try:
#             WebDriverWait(self.selenium, timeout=3).until(
#                 EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
#             )
#         except TimeoutException:
#             pass
#         el = self.selenium.find_element(By.ID, "answer").text
#         self.assertIn("Leidsime", el)
#
#         # search_input.clear()
#         search_input.send_keys(4 * Keys.BACK_SPACE)
#         try:
#             WebDriverWait(self.selenium, timeout=3).until(
#                 EC.text_to_be_present_in_element((By.ID, "answer"), "Vähemalt")
#             )
#         except TimeoutException:
#             pass
#         el = self.selenium.find_element(By.ID, "answer").text
#         self.assertIn("Vähemalt", el)
#
#         search_input.send_keys('õõõõõ')
#         time.sleep(1)
#         try:
#             WebDriverWait(self.selenium, timeout=3).until(
#                 EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
#             )
#         except TimeoutException:
#             pass
#         el = self.selenium.find_element(By.ID, "answer").text
#         self.assertIn("Leidsime 0 vastet", el)


class SeleniumTestsChromeProductionOtsiGetNextResults(SeleniumTestsChromeOtsiGetNextResults):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host_tobe_tested = 'https://valgalinn.ee'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_otsi(self):
        super().test_otsi()


class SeleniumTestsChromeProductionDetailViewObject(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Every test needs access to the request factory.
        cls.factory = RequestFactory()
        # Create an instance of a GET request.
        cls.request = cls.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(cls.request)
        cls.request.session.save()
        # self.user = User.objects.get(id=1)
        cls.request.user = AnonymousUser()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_view_special_objects(self):
        # Juhuslikud objectid kontrolliks
        objectid = [
            ('isik', 19), # Müllerson
            ('organisatsioon', 13), # Säde selts
            ('objekt', 13) # Jaani kirik
        ]
        for object in objectid:
            model = apps.get_model('wiki', object[0])
            obj = model.objects.daatumitega(request=self.request).get(id=object[1])
            detail_view_name = f'wiki:wiki_{model.__name__.lower()}_detail'
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            path = reverse(detail_view_name, kwargs=kwargs)
            self.selenium.get('%s%s' % ('https://valgalinn.ee', path))
            # Kontrollime kas objecti nimi on avanenud lehel
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            try:
                nimi = obj.perenimi
            except:
                nimi = obj.nimi
            self.assertIn(nimi, el, msg=str(obj))
            # Kontrollime kas isikuga seotud objectid laeti
            try:
                el = self.selenium.find_element(By.ID, "loaderDiv1")
                WebDriverWait(self.selenium, timeout=3).until(
                    EC.visibility_of(el)
                )
                WebDriverWait(self.selenium, timeout=10).until_not(
                    EC.visibility_of(el)
                )
            except TimeoutException:
                pass
            el = self.selenium.find_element(By.ID, "wiki_object_detail_seotud").text
            self.assertIn("Lugusid", el, obj)


    def test_view_artikkel(self):
        # Juhuslikud objectid kontrolliks
        artiklid = [10, 100, 1000]
        for artikkel in artiklid:
            obj = Artikkel.objects.daatumitega(request=self.request).get(id=artikkel)
            detail_view_name = f'wiki:wiki_artikkel_detail'
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            path = reverse(detail_view_name, kwargs=kwargs)
            self.selenium.get('%s%s' % ('https://valgalinn.ee', path))
            # Kontrollime et poleks 404
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            self.assertNotIn("Lehekülge ei leitud.", el)

    def test_view_HTTP404_nonexisting_urls(self):
        # Juhuslikud objectid kontrolliks
        urls = [
            '/wiki/isik/10/',
            '/wiki/organisatsioon/10/',
            '/wiki/objekt/10/',
            '/wiki/3274/'
        ]
        for url in urls:
            self.selenium.get('%s%s' % ('https://valgalinn.ee', url))
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            self.assertIn("Lehekülge ei leitud.", el)
            self.assertIn(url, el)
