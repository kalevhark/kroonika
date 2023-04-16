from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from . import views

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

    def test_kiri_view_per_user_type(self) -> None:
        # Recall that middleware are not supported. You can simulate a
        # logged-in user by setting request.user manually.
        self.request.user = self.user

        response = views.KiriView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "logi sisse")

        # Or you can simulate an anonymous user by setting request.user to
        # an AnonymousUser instance.
        self.request.user = AnonymousUser()
        response = views.KiriView.as_view()(self.request)
        response.client = Client()
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('account_login') + f'?next=/',
            status_code=302,
            # target_status_code=200,
            # msg_prefix='next',
            fetch_redirect_response=False
        )

    def tearDown(self) -> None:
        pass
