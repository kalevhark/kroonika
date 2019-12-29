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
# from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.documentation import include_docs_urls
from rest_framework.schemas import get_schema_view

from .routers import router
from wiki import views

schema_view = get_schema_view(title='Valga linna kroonika API')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.algus, name='algus'),
    # path('accounts/login/', auth_views.LoginView.as_view()),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
	path('api/', include(router.urls)),
    path('blog/', include('blog.urls')),
    path('ilm/', include('ilm.urls')),
    path('docs/', include_docs_urls(title='Valga linna kroonika API')),
    path('markdownx/', include('markdownx.urls')),
    path('schema/', schema_view),
    path('test/', views.test, name='test'), # linkide testimiseks
    path('wiki/', include('wiki.urls')),
    ]

# Serve static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve user uploaded media
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
