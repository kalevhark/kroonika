from datetime import datetime
from functools import reduce
from operator import or_
import time

from django.urls import reverse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

from .base import SeleniumTestsChromeBase

class SeleniumTestsChromeLogin(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_login(self):
        self.selenium.get('%s%s' % (self.host_tobe_tested, '/'))
        self.selenium.get('%s%s' % (self.host_tobe_tested, '/accounts/logout/'))
        self.selenium.get('%s%s' % (self.host_tobe_tested, '/accounts/login/'))
        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys(self.USERNAME)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(self.PASSWORD)
        self.selenium.find_element(By.XPATH, '//input[@value="login"]').click()
        time.sleep(3)
        self.assertEqual(
            self.selenium.current_url,
            '%s%s' % (self.host_tobe_tested, '/')
        )


class SeleniumTestsChromeOtsi(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_otsi(self):
        self.selenium.get('%s%s' % (self.host_tobe_tested, '/wiki/otsi/'))

        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Otsimiseks", el)

        search_input = self.selenium.find_element(By.ID, "question")
        search_input.send_keys('ta')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Vähemalt")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Vähemalt", el)

        search_input.send_keys('mm')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Leidsime", el)

        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_isikud"]/details/ul/*')
        self.assertEqual(len(results), 20)

        # self.selenium.find_element(By.ID, 'get_next_results_artiklid').click()
        # time.sleep(3)
        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_artiklid"]/ul/*')
        self.assertEqual(len(results), 20)

        # search_input.clear()
        search_input.send_keys(4 * Keys.BACK_SPACE)
        time.sleep(3)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Vähemalt")
            )
        except TimeoutException:
            pass

        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Vähemalt", el)

        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_isikud"]/details/ul/*')
        self.assertEqual(len(results), 0)

        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_artiklid"]/ul/*')
        self.assertEqual(len(results), 0)

        search_input.send_keys('õõõõõ')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Leidsime 0 vastet", el)

        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_isikud"]/details/ul/*')
        self.assertEqual(len(results), 0)

        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_artiklid"]/ul/*')
        self.assertEqual(len(results), 0)


class SeleniumTestsChromeOtsiGetNextResults(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_otsi(self):
        self.selenium.get('%s%s' % (self.host_tobe_tested, '/wiki/otsi/'))

        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Otsimiseks", el)

        search_input = self.selenium.find_element(By.ID, "question")

        search_input.send_keys('tamm')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Leidsime", el)

        self.selenium.find_element(By.ID, 'get_next_results_isikud').click()
        time.sleep(3)
        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_isikud"]/details/ul/*')
        # self.assertTrue(len(results) > 0)
        self.assertEqual(len(results), 40)

        self.selenium.find_element(By.ID, 'get_next_results_artiklid').click()
        time.sleep(3)
        results = self.selenium.find_elements(By.XPATH, '//*[@id="leitud_artiklid"]/ul/*')
        print(results)
        self.assertEqual(len(results), 40)

        search_input.send_keys(4 * Keys.BACK_SPACE)
        time.sleep(1)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Vähemalt")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Vähemalt", el)

        search_input.send_keys('õõõõõ')
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "answer"), "Leidsime")
            )
        except TimeoutException:
            pass
        el = self.selenium.find_element(By.ID, "answer").text
        self.assertIn("Leidsime 0 vastet", el)


def getData(model):
    detail_view_name = f'wiki:wiki_{model.__name__.lower()}_detail'
    artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
    initial_queryset = model.objects.all()
    artikliga = initial_queryset. \
        filter(artikkel__in=artikkel_qs). \
        values_list('id', flat=True)
    viitega = initial_queryset. \
        filter(viited__isnull=False). \
        values_list('id', flat=True)
    viiteta_artiklita = initial_queryset. \
        filter(viited__isnull=True, artikkel__isnull=True). \
        values_list('id', flat=True)
    model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])
    return initial_queryset, model_ids, detail_view_name


class SeleniumTestsChromeDetailViewObjectIsik(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.initial_queryset, cls.model_ids, cls.detail_view_name = getData(Isik)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_view_show_by_name_random(self):
        SELECT_COUNT = 10
        # Juhuslikud objectid kontrolliks
        objs = self.initial_queryset.filter(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            cnt = obj.artikkel_set.count()
            if cnt == 0:
                continue
            print(obj.id, cnt)
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            path = reverse(self.detail_view_name, kwargs=kwargs)
            self.selenium.get('%s%s' % (self.live_server_url, path))
            # Kontrollime kas isiku nimi on avanenud lehel
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
            # self.assertIn("Lugusid", el)
            self.assertTrue(len(el) > 0)

    def test_view_HTTP404_for_non_authented_user(self):
        SELECT_COUNT = 10
        # Juhuslikud objectid kontrolliks
        objs = self.initial_queryset.exclude(id__in=self.model_ids).order_by('?')[:SELECT_COUNT]
        for obj in objs:
            kwargs = {
                'pk': obj.id,
                'slug': obj.slug
            }
            path = reverse(self.detail_view_name, kwargs=kwargs)
            self.selenium.get('%s%s' % (self.live_server_url, path))
            el = self.selenium.find_element(By.TAG_NAME, "body").text
            try:
                nimi = obj.perenimi
            except:
                nimi = obj.nimi
            self.assertIn("ei leitud", el)


class SeleniumTestsChromeDetailViewObjectObjekt(SeleniumTestsChromeDetailViewObjectIsik):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.initial_queryset, cls.model_ids, cls.detail_view_name = getData(Objekt)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_view_show_by_name_random(self):
        super().test_view_show_by_name_random()

    def test_view_HTTP404_for_non_authented_user(self):
        super().test_view_HTTP404_for_non_authented_user()


class SeleniumTestsChromeDetailViewObjectOrganisatsioon(SeleniumTestsChromeDetailViewObjectIsik):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.initial_queryset, cls.model_ids, cls.detail_view_name = getData(Organisatsioon)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_view_show_by_name_random(self):
        super().test_view_show_by_name_random()

    def test_view_HTTP404_for_non_authented_user(self):
        super().test_view_HTTP404_for_non_authented_user()


class SeleniumTestsChromeV6rdleIsik(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_v6rdle(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/'))
        self.selenium.get('%s%s' % (self.live_server_url, '/info/'))
        self.selenium.get('%s%s' % (self.live_server_url, '/wiki/v6rdle/isik/'))

        # kontrollime kas n6utakse sisselogimist
        self.assertEqual(self.selenium.current_url, '%s%s' % (self.live_server_url, '/accounts/login/?next=/wiki/v6rdle/isik/'))
        el = self.selenium.find_element(By.TAG_NAME, "body").text
        self.assertIn("logi sisse", el)

        # logime sisse
        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys(self.USERNAME)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(self.PASSWORD)
        self.selenium.find_element(By.XPATH, '//input[@value="login"]').click()

        # kontrollime kas sisselogimine 6nnestus
        button_vasak = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertTrue(button_vasak)
        button_parem = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertTrue(button_parem)

        # kontrollime kas sidumise nupud on disabled olekus
        self.assertFalse(button_vasak.is_enabled())
        self.assertFalse(button_parem.is_enabled())

        # sisestame esimese objekti otsingusse
        search_input = self.selenium.find_element(By.ID, "id_vasak_object_text")
        search_input.send_keys('tamm')
        time.sleep(2)
        search_input.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "v6rdle_vasak_object"), "Tamm")
            )
        except TimeoutException:
            pass

        # kontrollime kas sidumise nupud on endiselt disabled olekus
        button_vasak = self.selenium.find_element(By.ID, "button-join-vasak")
        button_parem = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertFalse(button_vasak.is_enabled())
        self.assertFalse(button_parem.is_enabled())

        search_input = self.selenium.find_element(By.ID, "id_parem_object_text")
        search_input.send_keys('teen')
        time.sleep(2)
        search_input.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "v6rdle_parem_object"), "Teen")
            )
        except TimeoutException:
            pass

        # kontrollime kas sidumise nupud on enabled olekus
        button_vasak = self.selenium.find_element(By.ID, "button-join-vasak")
        button_parem = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertTrue(button_vasak.is_enabled())
        self.assertTrue(button_parem.is_enabled())


class SeleniumTestsChromeV6rdleObjekt(SeleniumTestsChromeBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_v6rdle(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/'))
        self.selenium.get('%s%s' % (self.live_server_url, '/info/'))
        self.selenium.get('%s%s' % (self.live_server_url, '/wiki/v6rdle/objekt/'))

        # kontrollime kas n6utakse sisselogimist
        self.assertEqual(self.selenium.current_url, '%s%s' % (self.live_server_url, '/accounts/login/?next=/wiki/v6rdle/objekt/'))
        el = self.selenium.find_element(By.TAG_NAME, "body").text
        self.assertIn("logi sisse", el)

        # logime sisse
        username_input = self.selenium.find_element(By.NAME, "username")
        username_input.send_keys(self.USERNAME)
        password_input = self.selenium.find_element(By.NAME, "password")
        password_input.send_keys(self.PASSWORD)
        self.selenium.find_element(By.XPATH, '//input[@value="login"]').click()

        # kontrollime kas sisselogimine 6nnestus
        button_vasak = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertTrue(button_vasak)
        button_parem = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertTrue(button_parem)

        # kontrollime kas sidumise nupud on disabled olekus
        self.assertFalse(button_vasak.is_enabled())
        self.assertFalse(button_parem.is_enabled())

        # sisestame esimese objekti otsingusse
        search_input = self.selenium.find_element(By.ID, "id_vasak_object_text")
        search_input.send_keys('Uus')
        time.sleep(2)
        search_input.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "v6rdle_vasak_object"), "Uus")
            )
        except TimeoutException:
            pass

        # kontrollime kas sidumise nupud on endiselt disabled olekus
        button_vasak = self.selenium.find_element(By.ID, "button-join-vasak")
        button_parem = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertFalse(button_vasak.is_enabled())
        self.assertFalse(button_parem.is_enabled())

        search_input = self.selenium.find_element(By.ID, "id_parem_object_text")
        search_input.send_keys('vabaduse')
        time.sleep(2)
        search_input.send_keys(Keys.ARROW_DOWN + Keys.ENTER)
        try:
            WebDriverWait(self.selenium, timeout=3).until(
                EC.text_to_be_present_in_element((By.ID, "v6rdle_parem_object"), "Vabaduse")
            )
        except TimeoutException:
            pass

        # kontrollime kas sidumise nupud on enabled olekus
        button_vasak = self.selenium.find_element(By.ID, "button-join-vasak")
        button_parem = self.selenium.find_element(By.ID, "button-join-vasak")
        self.assertTrue(button_vasak.is_enabled())
        self.assertTrue(button_parem.is_enabled())
