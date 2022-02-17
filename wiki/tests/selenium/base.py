import configparser

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
config = configparser.SafeConfigParser(allow_no_value=True)
config.read('%s/settings.ini' % (settings.PROJECT_DIR))

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

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
