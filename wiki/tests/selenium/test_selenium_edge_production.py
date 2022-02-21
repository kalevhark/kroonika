import time

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
            self.selenium.get('%s%s' % ('https://valgalinn.ee', path))
            # Kontrollime kas objecti nimi on avanenud lehel
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            try:
                nimi = obj.perenimi
            except:
                nimi = obj.nimi
            self.assertIn(nimi, el)
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
            self.assertIn("Lugusid", el)

    def test_view_HTTP404_for_non_authented_user(self):
        pass