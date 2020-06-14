from django.contrib import sitemaps
from django.contrib.sitemaps import Sitemap

from django.urls import reverse

from wiki.models import Artikkel

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.8
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return ['algus', 'wiki:otsi', 'blog:blog_index', 'ilm:index']

    def location(self, item):
        return reverse(item)


class ArtikkelSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = 'https'

    def items(self):
        return Artikkel.objects.filter(kroonika__isnull=True)

    def lastmod(self, obj):
        return obj.mod_date