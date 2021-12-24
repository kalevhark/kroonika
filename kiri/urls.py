from django.urls import path
from .views import KiriView, KiriSuccessView

app_name = 'kiri'

urlpatterns = [
    path('', KiriView.as_view(), name="index"),
    path('success/<str:email_to>|<str:subject>', KiriSuccessView.as_view(), name="success"),
]