import configparser
from functools import reduce
from operator import or_

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# Access configparser to load variable values
config = configparser.ConfigParser(allow_no_value=True)
config.read('%s/settings.ini' % (settings.PROJECT_DIR))

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt
from wiki.tests import test_base
SPECIAL_OBJECTS = test_base.SPECIAL_OBJECTS

# SPECIAL_OBJECTS = {
#     'isik': [
#         62, # Johann Müllerson
#     ],
#     'organisatsioon': [
#         13, # Säde selts
#     ],
#     'objekt': [  # TODO: Vajalik p2ring teha andmebaasist
#         13,  # Kesk 21, Jaani kirik
#         23,  # Kesk 11, raekoda
#         24,  # Riia 5
#         29,  # Tartu 2, vesiveski
#         81,  # J. Kuperjanovi 9, Moreli maja
#         102,  # Kesk 22, linnakooli hoone
#         187,  # Kesk 19, Klasmanni maja
#         # 256,  # Aia 12, Zenckeri villa
#         354,  # J. Kuperjanovi 12, lõvidega maja
#     ]
# }

def getData(model):
    detail_view_name = f'wiki:wiki_{model.__name__.lower()}_detail'
    artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
    if model == Artikkel:
        model_ids = artikkel_qs.values_list('id', flat=True)
    else:
        initial_queryset = model.objects.all()
        viitega = initial_queryset. \
            filter(viited__isnull=False). \
            values_list('id', flat=True)
        artikliga = initial_queryset. \
            filter(artikkel__in=artikkel_qs). \
            values_list('id', flat=True)
        viiteta_artiklita = initial_queryset. \
            filter(viited__isnull=True, artikkel__isnull=True). \
            values_list('id', flat=True)
        model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])
    return initial_queryset, model_ids, detail_view_name

class SeleniumTestsChromeBase(StaticLiveServerTestCase):

    # def test_driver_manager_chrome(self):
    #     service = ChromeService(executable_path=ChromeDriverManager().install())
    #     driver = webdriver.Chrome(service=service)
    #     driver.quit()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        service = ChromeService(executable_path=ChromeDriverManager().install())
        cls.selenium = webdriver.Chrome(service=service)
        cls.selenium.implicitly_wait(10)
        cls.USERNAME = config['superuser']['USERNAME']
        cls.PASSWORD = config['superuser']['PASSWORD']
        cls.host_tobe_tested = cls.live_server_url

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_driver_manager_chrome(self):
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.quit()


class SeleniumTestsEdgeBase(StaticLiveServerTestCase):

    # def test_edge_session(self):
    #     service = EdgeService(executable_path=EdgeChromiumDriverManager().install())
    #     driver = webdriver.Edge(service=service)
    #     driver.quit()

    # fixtures = ['user-data.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        service = EdgeService(executable_path=EdgeChromiumDriverManager().install())
        cls.selenium = webdriver.Edge(service=service)
        cls.selenium.implicitly_wait(10)
        cls.USERNAME = config['superuser']['USERNAME']
        cls.PASSWORD = config['superuser']['PASSWORD']
        cls.host_tobe_tested = cls.live_server_url

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
