# kroonika URL Configuration

from ajax_select import urls as ajax_select_urls

# from django.contrib.auth import views as auth_views
from django.conf import settings
# from django.conf.urls import handler500
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

# schema_url_patterns = [
#     path('api/', include(router.urls)),
# ]

# API
schema_view = get_schema_view(
    title='Valga linna kroonika API',
    # url='https://valgalinn/api/',
    # patterns=schema_url_patterns
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.algus, name='algus'),
    path('info/', views.info, name='info'),
    # path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('allauth.urls')), # django-allauth
    path('ajax_select/', include(ajax_select_urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
	path('api/', include(router.urls)),
    path('blog/', include('blog.urls'), name='blog'),
    path('kiri/', include('kiri.urls'), name='kiri'),
    path('ilm/', include('ilm.urls'), name='ilm'),
    path('docs/', include_docs_urls(title='Valga linna kroonika API')),
    path('markdownx/', include('markdownx.urls')),
    path('privacy/', views.privacy, name='privacy'),
    path('schema/', schema_view),
    path('wiki/', include('wiki.urls')),
    path('kaart/', views.kaart, name='kaart'),
    path('kaart/get_big_leaflet_map/', views.get_big_leaflet_map, name='get_big_leaflet_map'),
    path('kaart/<int:aasta>/', views.kaart, name='kaart'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    # path('valga438/', specials.special_valga438, name='special_valga438'),
    # path('valga439/', specials.special_valga439, name='special_valga439'),
    # path('valga440/', specials.special_valga440, name='special_valga440'),
    # path('j6ul2020/', specials.special_j6ul2020, name='special_j6ul2020'),
    # path('j6ul2021/', specials.special_j6ul2021, name='special_j6ul2021'),
    # path('j6ul2022/', specials.special_j6ul2022, name='special_j6ul2022'),
    # path('j6ul2023/', specials.special_j6ul2023, name='special_j6ul2023'),
    # path("__debug__/", include("debug_toolbar.urls")), # https://django-debug-toolbar.readthedocs.io
]

#error handling
handler500 = 'wiki.views.custom_500'

# Haldusliidese pealkirjad
admin.site.site_header = 'valgalinn.ee sisuhaldus'
admin.site.site_title = 'valgalinn.ee sisuhaldus'

# Serve static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve user uploaded media
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
