import time

from django.apps import apps
from django.urls import reverse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from wiki.models import Artikkel

from .base import getData, SeleniumTestsEdgeBase

class SeleniumTestsEdgeLogin(SeleniumTestsEdgeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_login(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/'))
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/logout/'))
        self.selenium.implicitly_wait(3)
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))

        # username_input = self.selenium.find_element(By.NAME, "username")
        # username_input.send_keys('fakeuser')
        # password_input = self.selenium.find_element(By.NAME, "password")
        # password_input.send_keys('fakepassword')
        # self.selenium.implicitly_wait(3)
        # bodyText = self.selenium.find_element(By.TAG_NAME, 'body').text
        # self.assertTrue("Palun proovi uuesti" in bodyText)

        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys(self.USERNAME)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(self.PASSWORD)
        self.selenium.find_element(By.XPATH, '//input[@value="login"]').click()
        time.sleep(3)
        # bodyText = self.selenium.find_element(By.TAG_NAME, 'body').text
        # self.assertFalse("Palun proovi uuesti" in bodyText)

        self.assertEqual(
            self.selenium.current_url,
            '%s%s' % (self.live_server_url, '/')
        )

class SeleniumTestsEdgeOtsi(SeleniumTestsEdgeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_otsi(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/wiki/otsi/'))

        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Otsimiseks", el)

        search_input = self.selenium.find_element(By.ID, "question")
        search_input.send_keys('ta')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "vähemalt")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("vähemalt", el)

        search_input.send_keys('mm')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Leidsime", el)

        # search_input.clear()
        search_input.send_keys(4 * Keys.BACK_SPACE)
        time.sleep(1)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "vähemalt")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("vähemalt", el)

        search_input.send_keys('õõõõõ')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Leidsime 0 vastet", el)


class SeleniumTestsEdgeDetailViewObjectArtikkel(SeleniumTestsEdgeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.initial_queryset, cls.model_ids, cls.detail_view_name = getData(Artikkel)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_view_show_by_name_random(self):
        SELECT_COUNT = 10
        # Juhuslikud objectid kontrolliks
        objs = self.initial_queryset.filter(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            path = reverse(self.detail_view_name, kwargs=kwargs)
            self.selenium.get('%s%s' % (self.live_server_url, path))
            # Kontrollime kas sisu esimene sõna on avanenud lehel
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            esimene_s6na = obj.body_text.split(' ')[0]
            self.assertIn(esimene_s6na, el)

    def test_view_show_sarnased_artiklid(self):
        obj = self.initial_queryset.get(id=3133)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        path = reverse(self.detail_view_name, kwargs=kwargs)
        self.selenium.get('%s%s' % (self.live_server_url, path))
        # Kontrollime kas on avanenud lehel on Sarnased lood
        el = self.selenium.find_element(By.ID, f"{obj.id}_sarnased_artiklid")
        self.assertTrue(len(el.text) > 0)
        self.assertIn('Sarnased lood', el.text)