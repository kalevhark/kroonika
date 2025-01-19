#
# python manage.py test wiki
#
from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse, resolve

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

from wiki import views

SPECIAL_OBJECTS = {
    'isik': [
        62, # Johann Müllerson
    ],
    'organisatsioon': [
        13, # Säde selts
    ],
    'objekt': [  # TODO: Vajalik p2ring teha andmebaasist
        13,  # Kesk 21, Jaani kirik
        23,  # Kesk 11, raekoda
        24,  # Riia 5
        29,  # Tartu 2, vesiveski
        81,  # J. Kuperjanovi 9, Moreli maja
        102,  # Kesk 22, linnakooli hoone
        187,  # Kesk 19, Klasmanni maja
        # 256,  # Aia 12, Zenckeri villa
        354,  # J. Kuperjanovi 12, lõvidega maja
    ]
}

class ServevErrorViewTestClass(TestCase):
    def test_error_page_500(self):
        self.client.raise_request_exception = False
        response = self.client.get(reverse('raise_500_error'))
        self.assertEqual(response.status_code, 500)
        self.assertTrue(
            'Serveriviga'
            in response.content.decode('utf8')
        )

    def test_error_page_404(self):
        factory = RequestFactory()
        request = factory.get('/')
        response = self.client.get('/polesellist')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            'Lehekülge ei leitud'
            in response.content.decode('utf8')
        )

class WikiBaseUrlTests(TestCase):
    def setUp(self) -> None:
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        # self.user = User.objects.get(id=1)
        self.request.user = AnonymousUser()

    def tearDown(self) -> None:
        pass

    def test_root_url_resolves_to_home_page_view(self):
        found = resolve('/')
        self.assertEqual(found.func, views.algus)

    def test_info_url_resolves_to_info_page_view(self):
        found = resolve('/info/')
        self.assertEqual(found.func, views.info)

    def test_kaart_url_resolves_to_kaart_page_view(self):
        found = resolve('/kaart/')
        self.assertEqual(found.func, views.kaart)

    def test_home_page_returns_correct_html(self):
        # request = HttpRequest()
        response = views.algus(self.request)
        html = response.content.decode('utf8').rstrip()
        self.assertTrue(html.startswith('<!DOCTYPE html>'))
        # self.assertIn('<title>Valga linna kroonika</title>', html)
        self.assertTrue(html.endswith('</html>'), msg=html[-10:])


class WikiBaseViewTests(TestCase):

    def test_algus_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('algus'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_info_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('info'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_otsi_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('wiki:otsi'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('wiki:otsi'), {'q': 'ter'})
        self.assertEqual(response.status_code, 200)

    def test_blog_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('blog:blog_index'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)

    def test_ilm_view(self):
        time_start = datetime.now()
        response = self.client.get(reverse('ilm:index'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)

    def test_kaart_view_default(self):
        time_start = datetime.now()
        response = self.client.get(reverse('kaart'))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

class WikiKaartViewTests(TestCase):

    def test_kaart_view_with_existing_aasta(self):
        time_start = datetime.now()
        kwargs = {
            'aasta': '1683',
        }
        response = self.client.get(reverse('kaart', kwargs=kwargs))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_kaart_view_with_existing_objekt(self):
        time_start = datetime.now()
        response = self.client.get(reverse('kaart'), {'objekt': '13'})
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_kaart_view_with_wrong_aasta(self):
        time_start = datetime.now()
        kwargs = {
            'aasta': '1111',
        }
        response = self.client.get(reverse('kaart', kwargs=kwargs))
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')

    def test_kaart_view_with_wrong_objekt(self):
        time_start = datetime.now()
        response = self.client.get(reverse('kaart'), {'objekt': '-1'})
        time_stopp = datetime.now() - time_start
        self.assertEqual(response.status_code, 200)
        self.assertTrue(time_stopp.seconds < 3, f'Laadimisaeg: {time_stopp.seconds}.{time_stopp.microseconds}')


class UserTypeUnitTest(TestCase):
    def setUp(self) -> None:
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

    def tearDown(self) -> None:
        pass

    def test_info_view_per_user_type(self) -> None:
        # Recall that middleware are not supported. You can simulate a
        # logged-in user by setting request.user manually.
        self.request.user = self.user

        response = views.info(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "session")

        # Or you can simulate an anonymous user by setting request.user to
        # an AnonymousUser instance.
        self.request.user = AnonymousUser()
        response = views.info(self.request)
        # response = MyView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "session")

    def test_v6rdle_view_per_user_type(self) -> None:
        # Recall that middleware are not supported. You can simulate a
        # logged-in user by setting request.user manually.
        self.request.user = self.user

        response = views.v6rdle(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "logi sisse")

        # Or you can simulate an anonymous user by setting request.user to
        # an AnonymousUser instance.
        self.request.user = AnonymousUser()
        response = views.v6rdle(self.request)
        # response = MyView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('account_login') + f'?next=/',
            status_code=302,
            # target_status_code=200,
            # msg_prefix='next',
            fetch_redirect_response=False
        )

    def test_recaptcha(self) -> None:
        # request = self.factory.get('wiki_artikkel_filter')
        self.request.user = self.user
        recaptcha_check = views.check_recaptcha(self.request)
        self.assertFalse(recaptcha_check)

    def test_feedback(self) -> None:
        # request = self.factory.get('wiki_artikkel_filter')
        self.request.user = self.user
        response = views.feedback(self.request)
        self.assertEqual(response.status_code, 302)

        self.request = self.factory.post(reverse('wiki:feedback'), {'kirjeldus': 'testkirjeldus', 'kontakt': 'testuser'})
        response = views.feedback(self.request)
        self.assertEqual(response.status_code, 302)

    def test_object_count_per_user_type(self) -> None:
        # Create an instance of a GET request.
        request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()

        for model in [Artikkel, Isik, Organisatsioon, Objekt]:
            # Recall that middleware are not supported. You can simulate a
            # logged-in user by setting request.user manually.
            request.user = self.user
            count_all = model.objects.daatumitega(request).count()

            # Or you can simulate an anonymous user by setting request.user to
            # an AnonymousUser instance.
            request.user = AnonymousUser()
            count_restricted = model.objects.daatumitega(request).count()
            self.assertTrue(count_all > count_restricted)



class AdminUserTestCase(TestCase):
    """
    This class is going to be inherited by other sub-classes.
    """
    def setUp(self) -> None:
        self.user = User.objects.get(id=1)

    def tearDown(self) -> None:
        pass


class UserLoginTestCase(AdminUserTestCase):
    """
    This class is used to test the login functionality and
    check whether a user is successfully getting logged in to the
    system.
    """

    def setUp(self) -> None:
        super().setUp()

    def test_user_login(self):
        self.client = Client()
        # login = self.client.login(
        #     username=self.user.username,
        #     password=self.user.password
        # )

        response = self.client.post(
            reverse('account_login'),
            {'username': self.user.username, 'password': self.user.password}
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.user)
        response = self.client.get(reverse('info'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Viiteta")
        self.client.logout()
        response = self.client.get(reverse('info'))
        self.assertNotContains(response, "Viiteta")

        response = self.client.post(
            reverse('account_login'),
            {'username': self.user.username, 'password': self.user.password}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user.is_authenticated)

    def tearDown(self) -> None:
        self.client.logout()
        super().tearDown()
