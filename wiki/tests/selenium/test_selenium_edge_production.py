import time
from datetime import datetime

from django.apps import apps
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


from .base import SeleniumTestsEdgeBase

class SeleniumTestsEdgeProductionDetailViewObject(SeleniumTestsEdgeBase):

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

    def test_view_show_by_name_random(self):
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
            time_start = datetime.now()
            self.selenium.get('%s%s' % ('https://valgalinn.ee', path))
            # Kontrollime kas objecti nimi on avanenud lehel
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            try:
                nimi = obj.perenimi
            except:
                nimi = obj.nimi
            self.assertIn(nimi, el, obj)
            # Kontrollime kas isikuga seotud objectid laeti
            try:
                el = self.selenium.find_element(By.ID, "loaderDiv1")
                WebDriverWait(self.selenium, timeout=3).until(
                    EC.visibility_of(el)
                )
                WebDriverWait(self.selenium, timeout=20).until_not(
                    EC.visibility_of(el)
                )
            except TimeoutException:
                pass
            finally:
                time_stopp = datetime.now() - time_start
            el = self.selenium.find_element(By.ID, "wiki_object_detail_seotud").text
            self.assertIn("Lugusid", el, obj)
            self.assertTrue(time_stopp.seconds < 5, f'{obj} laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_view_HTTP404_for_non_authented_user(self):
        pass


class SeleniumTestsChromeMonthView(SeleniumTestsEdgeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_artikkel_month_archive_otheryears_content(self):
        self.selenium.get('%s%s' % (self.host_tobe_tested, '/wiki/kroonika/1903/11/'))

        el = self.selenium.find_element(By.ID, "artikkel_month_archive_otheryears_content")
        # self.assertTrue(len(el.text) == 0)
        # self.assertIn("Otsimiseks", el)

        try:
            WebDriverWait(self.selenium, timeout=1).until(
                EC.text_to_be_present_in_element((By.ID, "artikkel_month_archive_otheryears_content"), "näita veel")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "artikkel_month_archive_otheryears_content")
        initial_pack_len = len(el.text)
        self.assertTrue(initial_pack_len > 0)
        self.assertIn("näita veel", el.text)

        self.selenium.find_element(By.ID, 'get_artikkel_month_archive_otheryears_content_next').click()
        time.sleep(3)
        el = self.selenium.find_element(By.ID, "artikkel_month_archive_otheryears_content")
        pack_len = len(el.text)
        self.assertTrue(pack_len > initial_pack_len)
        self.assertIn("näita veel", el.text)