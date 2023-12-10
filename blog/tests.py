from django.test import TestCase
from django.urls import reverse, resolve

from . import views
from blog.models import Post

class WikiBaseUrlTests(TestCase):

    def test_root_url_resolves_to_home_page_view(self):
        found = resolve('/blog/')
        self.assertEqual(found.func, views.blog_index)


class BlogViewTests(TestCase):
    def test_blog_index_view(self):
        response = self.client.get(reverse('blog:blog_index'))
        self.assertEqual(response.status_code, 200)

    def test_blog_detail_view_slug(self):
        obj = Post.objects.all().order_by('?')[0]
        slug = obj.slug
        response = self.client.get(reverse('blog:blog_detail', kwargs={'slug': slug}))
        # response = views.ArtikkelDetailView.as_view()(self.request, pk=art.pk, slug=art.slug)
        self.assertEqual(response.status_code, 200)

    def test_blog_detail_view_wrongslug(self):
        response = self.client.get(reverse('blog:blog_detail', kwargs={'slug': 'slug'}))
        # response = views.ArtikkelDetailView.as_view()(self.request, pk=art.pk, slug=art.slug)
        self.assertEqual(response.status_code, 200)
