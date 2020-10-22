# app/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

app_name = 'sihtnumber'

urlpatterns = [
    path('', views.otsi_sihtnumber, name='otsi_sihtnumber'),
]

# Serve static files
if settings.DEBUG:
   urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
