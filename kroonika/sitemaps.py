from functools import reduce
from operator import or_

from django.contrib import sitemaps
from django.contrib.sitemaps import Sitemap

from django.urls import reverse

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

def filter_model(model):
    artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
    initial_queryset = model.objects
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
    filtered_queryset = initial_queryset.filter(id__in=model_ids)
    return filtered_queryset

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


class IsikSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = 'https'

    def items(self):
        return filter_model(Isik)

    def lastmod(self, obj):
        return obj.mod_date


class OrganisatsioonSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = 'https'

    def items(self):
        return filter_model(Organisatsioon)

    def lastmod(self, obj):
        return obj.mod_date


class ObjektSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"
    protocol = 'https'

    def items(self):
        return filter_model(Objekt)

    def lastmod(self, obj):
        return obj.mod_date