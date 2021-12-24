"""kroonika URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from ajax_select import urls as ajax_select_urls

# from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from rest_framework.documentation import include_docs_urls
from rest_framework.schemas import get_schema_view

from .sitemaps import StaticViewSitemap, ArtikkelSitemap, IsikSitemap, OrganisatsioonSitemap, ObjektSitemap
from .routers import router
from wiki import views, specials

# sitemaps.xml
sitemaps = {
    'static': StaticViewSitemap,
    'lood': ArtikkelSitemap,
    'isikud': IsikSitemap,
    'asutised': OrganisatsioonSitemap,
    'kohad': ObjektSitemap
}

# API
schema_view = get_schema_view(title='Valga linna kroonika API')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.algus, name='algus'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('ajax_select/', include(ajax_select_urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
	path('api/', include(router.urls)),
    path('blog/', include('blog.urls'), name='blog'),
    path('kiri/', include('kiri.urls'), name='kiri'),
    path('ilm/', include('ilm.urls'), name='ilm'),
    path('docs/', include_docs_urls(title='Valga linna kroonika API')),
    path('markdownx/', include('markdownx.urls')),
    path('schema/', schema_view),
    path('wiki/', include('wiki.urls')),
    path('kaart/', views.kaart, name='kaart'),
    path('kaart/<str:aasta>/', views.kaart, name='kaart'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('valga437/', specials.special_valga437, name='special_valga437'),
    # path('j6ul2020/', specials.special_j6ul2020, name='special_j6ul2020'),
    path('j6ul2021/', specials.special_j6ul2021, name='special_j6ul2021'),
]

# Haldusliidese pealkirjad
admin.site.site_header = 'valgalinn.ee sisuhaldus'
admin.site.site_title = 'valgalinn.ee sisuhaldus'

# Serve static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve user uploaded media
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
