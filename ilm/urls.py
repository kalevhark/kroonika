from django.urls import path, include
from . import views

app_name = 'ilm'
urlpatterns = [
    path('', views.index, name='index'),
    path('history/', views.history, name='history'),
    path('mixed_ilmateade/', views.mixed_ilmateade, name='mixed_ilmateade'),
    path('container_history_andmed/', views.container_history_andmed, name='container_history_andmed'),
    path('container_history_aasta/', views.container_history_aasta, name='container_history_aasta'),
    path('container_history_kuud/', views.container_history_kuud, name='container_history_kuud'),
    path('container_history_kuu/', views.container_history_kuu, name='container_history_kuu'),
    path('container_history_p2ev/', views.container_history_p2ev, name='container_history_p2ev'),
    path('container_history_p2evad/', views.container_history_p2evad, name='container_history_p2evad'),
    path('container_history_aastad/', views.container_history_aastad, name='container_history_aastad'),
    # path('pyimage/', PyImageView.as_view(), name='pyimage_view'),
]