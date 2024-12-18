from datetime import datetime
from functools import reduce
from operator import or_
import time
import urllib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import QueryDict
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from wiki import views
from wiki.models import Artikkel, Isik, Organisatsioon, Objekt
from wiki.tests import test_base


class DetailViewUnitTest(TestCase):
    def setUp(self) -> None:
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

    def test_artikkel_context(self):
        self.request.user = AnonymousUser()
        art = Artikkel.objects.daatumitega(self.request).order_by("?")[0]
        # view = views.ArtikkelDetailView()
        # view.setup(self.request, pk=art.pk, slug=art.slug)
        # context = view.get_context_data()
        # self.assertIn('n', context)
        response = views.ArtikkelDetailView.as_view()(self.request, pk=art.pk, slug=art.slug)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn('n', response.context_data)
        self.assertIn('profiilipilt', response.context_data)
        self.assertIn('seotud_isikud', response.context_data)
        self.assertIn('seotud_organisatsioonid', response.context_data)
        self.assertIn('seotud_objektid', response.context_data)
        self.assertIn('seotud_pildid', response.context_data)
        self.assertIn('sarnased_artiklid', response.context_data)

    def test_artikkel_context_seotud_isikud(self):
        self.request.user = AnonymousUser()
        art = Artikkel.objects.daatumitega(self.request).order_by("?")[0]
        isikuid = art.isikud.count()
        response = views.ArtikkelDetailView.as_view()(self.request, pk=art.pk, slug=art.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['seotud_isikud']), isikuid)

    def test_artikkel_context_seotud_organisatsioonid(self):
        self.request.user = AnonymousUser()
        art = Artikkel.objects.daatumitega(self.request).order_by("?")[0]
        organisatsioone = art.organisatsioonid.count()
        response = views.ArtikkelDetailView.as_view()(self.request, pk=art.pk, slug=art.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['seotud_organisatsioonid']), organisatsioone)

    def test_artikkel_context_seotud_objektid(self):
        self.request.user = AnonymousUser()
        art = Artikkel.objects.daatumitega(self.request).order_by("?")[0]
        objekte = art.objektid.count()
        response = views.ArtikkelDetailView.as_view()(self.request, pk=art.pk, slug=art.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context_data['seotud_objektid']), objekte)

    def test_artikkel_context_sarnased_artiklid(self):
        self.request.user = AnonymousUser()
        obj = Artikkel.objects.daatumitega(self.request).get(id=3133)
        response = views.ArtikkelDetailView.as_view()(self.request, pk=obj.pk, slug=obj.slug)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context_data['sarnased_artiklid']) > 0)

    def test_isik_context(self):
        self.request.user = AnonymousUser()
        obj = Isik.objects.daatumitega(self.request).order_by("?")[0]
        response = views.IsikDetailView.as_view()(self.request, pk=obj.pk, slug=obj.slug)
        self.assertEqual(response.status_code, 200)
        self.assertIn('profiilipilt', response.context_data)
        self.assertIn('seotud_organisatsioonid', response.context_data)
        self.assertIn('seotud_objektid', response.context_data)
        self.assertIn('seotud_pildid', response.context_data)

    def test_organisatsioon_context(self):
        self.request.user = AnonymousUser()
        obj = Organisatsioon.objects.daatumitega(self.request).order_by("?")[0]
        response = views.OrganisatsioonDetailView.as_view()(self.request, pk=obj.pk, slug=obj.slug)
        self.assertEqual(response.status_code, 200)
        self.assertIn('profiilipilt', response.context_data)
        self.assertIn('seotud_objektid', response.context_data)
        self.assertIn('seotud_pildid', response.context_data)

    def test_objekt_context(self):
        self.request.user = AnonymousUser()
        obj = Objekt.objects.daatumitega(self.request).order_by("?")[0]
        response = views.ObjektDetailView.as_view()(self.request, pk=obj.pk, slug=obj.slug)
        self.assertEqual(response.status_code, 200)
        self.assertIn('profiilipilt', response.context_data)
        self.assertIn('seotud_isikud', response.context_data)
        self.assertIn('seotud_objektid', response.context_data)
        self.assertIn('seotud_pildid', response.context_data)


class ArtikkelViewTests(TestCase):

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

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

    def test_artikkel_with_filter_objects_exists_isik_and_related(self):
        isik_id = 7 # H. Einer
        # organisatsioon_id = 2 # karskusselts
        # objekt_id = 311 # Kesk 33
        artikkel_id = 4503 # k6ik objectid olemas
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                # 'organisatsioon': organisatsioon_id,
                # 'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('queryparams', response.context_data)
        self.assertEqual(response.context_data['queryparams'][1:], queryparams.urlencode())

    def test_artikkel_with_filter_objects_exists_organisatsioon_and_related(self):
        # isik_id = 7 # H. Einer
        organisatsioon_id = 2 # karskusselts
        # objekt_id = 311 # Kesk 33
        artikkel_id = 4503 # k6ik objectid olemas
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                # 'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                # 'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('queryparams', response.context_data)
        self.assertEqual(response.context_data['queryparams'][1:], queryparams.urlencode())

    def test_artikkel_with_filter_objects_exists_objekt_and_related(self):
        # isik_id = 7 # H. Einer
        # organisatsioon_id = 2 # karskusselts
        objekt_id = 311 # Kesk 33
        artikkel_id = 4503 # k6ik objectid olemas
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                # 'isik': isik_id,
                # 'organisatsioon': organisatsioon_id,
                'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('queryparams', response.context_data)
        self.assertEqual(response.context_data['queryparams'][1:], queryparams.urlencode())

    def test_artikkel_with_filter_objects_all_exist_and_related(self):
        isik_id = 7 # H. Einer
        organisatsioon_id = 2 # karskusselts
        objekt_id = 311 # Kesk 33
        artikkel_id = 4503 # k6ik objectid olemas
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('queryparams', response.context_data)
        self.assertEqual(response.context_data['queryparams'][1:], queryparams.urlencode())

    def test_artikkel_with_filter_objects_some_wrong_and_related(self):
        isik_id = 7 # H. Einer
        organisatsioon_id = 2 # karskusselts
        objekt_id = 311 # Kesk 33
        artikkel_id = 4503 # k6ik objectid olemas
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                'xxx': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('queryparams', response.context_data)
        self.assertNotEquals(response.context_data['queryparams'][1:], queryparams.urlencode())
        self.assertIn(response.context_data['queryparams'][1:], queryparams.urlencode())

    def test_artikkel_with_filter_objects_all_exist_not_related(self):
        isik_id = 77 # J. Tamm
        organisatsioon_id = 22 # Valga linna tytarlastekool
        objekt_id = 309 # Grynbergi maja
        artikkel_id = 4503 # ykski object pole seotud
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('queryparams', response.context_data)

    def test_artikkel_with_filter_objects_not_exist_nor_related(self):
        isik_id = 17 # none
        organisatsioon_id = 8 # none
        objekt_id = 310 # none
        artikkel_id = 4503 # ykski object pole seotud
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('queryparams', response.context_data)

    def test_artikkel_with_filter_objects_none_nor_related(self):
        isik_id = None # none
        organisatsioon_id = None # none
        objekt_id = None # none
        artikkel_id = 4503 # ykski object pole seotud
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('queryparams', response.context_data)

    def test_artikkel_with_filter_objects_empty_nor_related(self):
        isik_id = '' # none
        organisatsioon_id = '' # none
        objekt_id = '' # none
        artikkel_id = 4503 # ykski object pole seotud
        obj = Artikkel.objects.get(id=artikkel_id)
        kwargs = {
            'pk': obj.id,
            'slug': obj.slug
        }
        queryparams = QueryDict(mutable=True)
        queryparams.update(
            {
                'isik': isik_id,
                'organisatsioon': organisatsioon_id,
                'objekt': objekt_id
            }
        )
        base_url = reverse(
            'wiki:wiki_artikkel_detail',
            kwargs=kwargs
        )
        url = '{}?{}'.format(base_url, queryparams.urlencode())
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('queryparams', response.context_data)

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

    def test_inline_edit_not_allowed_anonymous(self):
        self.request.user = AnonymousUser()
        pk = 2504
        artikkel = Artikkel.objects.get(pk=pk)
        response = views.ArtikkelDetailView.as_view()(self.request, pk=artikkel.pk, slug=artikkel.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dockmann')
        self.assertNotContains(response, 'inlineedit-toggle-area')

    def test_inline_edit_allowed_superuser(self):
        self.request.user = self.user
        pk = 2504
        artikkel = Artikkel.objects.get(pk=pk)
        response = views.ArtikkelDetailView.as_view()(self.request, pk=pk, slug=artikkel.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dockmann')
        self.assertContains(response, 'inlineedit-toggle-area')

class IsikViewTests(TestCase):

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

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

    def test_view_special_url_exists_at_desired_location(self):
        pk = 62 # Johann Müllerson
        isik = Isik.objects.get(pk=pk)
        url = f'/wiki/isik/{isik.id}-{isik.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        url = '/wiki/isik/62-johann-müllerson/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        url = '/wiki/isik/62-suva/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        url = '/wiki/isik/62/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

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

    def test_inline_edit_not_allowed_anonymous(self):
        self.request.user = AnonymousUser()
        pk = 62  # Johann Müllerson
        isik = Isik.objects.get(pk=pk)
        response = views.IsikDetailView.as_view()(self.request, pk=pk, slug=isik.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Müllerson')
        self.assertNotContains(response, 'inlineedit-toggle-area')

    def test_inline_edit_allowed_superuser(self):
        self.request.user = self.user
        pk = 62  # Johann Müllerson
        isik = Isik.objects.get(pk=pk)
        response = views.IsikDetailView.as_view()(self.request, pk=pk, slug=isik.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Müllerson')
        self.assertContains(response, 'inlineedit-toggle-area')


class OrganisatsioonViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

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
        self.assertTrue(time_stopp.seconds < 5, f'Laadimisaeg: {obj} {time_stopp.seconds}.{time_stopp.microseconds}')

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

    def test_inline_edit_not_allowed_anonymous(self):
        self.request.user = AnonymousUser()
        pk = 3058
        organisatsioon = Organisatsioon.objects.get(pk=pk)
        response = views.OrganisatsioonDetailView.as_view()(self.request, pk=pk, slug=organisatsioon.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rex')
        self.assertNotContains(response, 'inlineedit-toggle-area')

    def test_inline_edit_allowed_superuser(self):
        self.request.user = self.user
        pk = 3058
        organisatsioon = Organisatsioon.objects.get(pk=pk)
        response = views.OrganisatsioonDetailView.as_view()(self.request, pk=pk, slug=organisatsioon.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rex')
        self.assertContains(response, 'inlineedit-toggle-area')


class ObjektViewTests(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # Create an instance of a GET request.
        self.request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(self.request)
        self.request.session.save()
        self.user = User.objects.get(id=1)

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

    def test_view_special_url_exists_at_desired_location(self):
        pks = test_base.SPECIAL_OBJECTS['objekt']
        # pk = 13 # Jaani kirik
        for pk in pks:
            obj = Objekt.objects.get(pk=pk)
            url = f'/wiki/objekt/{obj.id}-{obj.slug}/'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            # url = f'/wiki/objekt/{pk}-kesk-21/'
            # response = self.client.get(url)
            # self.assertEqual(response.status_code, 200)
            url = f'/wiki/objekt/{pk}-suva/'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            url = f'/wiki/objekt/{pk}/'
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

    def test_view_url_response_time(self):
        time_start = datetime.now()
        obj = Objekt.objects.get(id=self.test_object_id)
        url = f'/wiki/objekt/{obj.id}-{obj.slug}/'
        _ = self.client.get(url)
        time_stopp = datetime.now() - time_start
        self.assertTrue(time_stopp.seconds < 5, f'Laadimisaeg: {obj} {time_stopp.seconds}.{time_stopp.microseconds}')

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

    def test_inline_edit_not_allowed_anonymous(self):
        self.request.user = AnonymousUser()
        pk = 31
        objekt = Objekt.objects.get(pk=pk)
        response = views.ObjektDetailView.as_view()(self.request, pk=pk, slug=objekt.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'linnapark')
        self.assertNotContains(response, 'inlineedit-toggle-area')

    def test_inline_edit_allowed_superuser(self):
        self.request.user = self.user
        pk = 31
        objekt = Objekt.objects.get(pk=pk)
        response = views.ObjektDetailView.as_view()(self.request, pk=pk, slug=objekt.slug)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'linnapark')
        self.assertContains(response, 'inlineedit-toggle-area')
