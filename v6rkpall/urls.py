from django.urls import path
from . import views

app_name = 'v6rkpall'
urlpatterns = [
    path("", views.blog_index, name="index"),
]