from django.urls import path

from . import views

# Objektivaated
from wiki.views import ArtikkelDetailView, IsikDetailView, OrganisatsioonDetailView, ObjektDetailView, KaardiobjektDetailView
# Filtreerimisvaated
from wiki.views import ArtikkelFilterView, IsikFilterView, OrganisatsioonFilterView, ObjektFilterView, KaardiobjektFilterView
# Loendivaated
from wiki.views import ArtikkelArchiveIndexView, ArtikkelYearArchiveView, ArtikkelMonthArchiveView, ArtikkelDayArchiveView
# Muutmisvaated
from wiki.views import ArtikkelUpdate, IsikUpdate, OrganisatsioonUpdate, ObjektUpdate, KaardiobjektUpdate
# API vaated
# from wiki.views import UserDetail, UserList

app_name = 'wiki'

urlpatterns = [
    path('', ArtikkelFilterView.as_view(), name='wiki_artikkel_filter'),
    path('<int:pk>-<str:slug>/', ArtikkelDetailView.as_view(), name='wiki_artikkel_detail'),
    path('info/', views.info, name='info'),
    path('otsi/', views.otsi, name='otsi'),
    path('feedback/', views.feedback, name='feedback'),
    path('kroonika/', ArtikkelArchiveIndexView.as_view(), name='artikkel_index_archive'),
    path('kroonika/infinite/', views.artikkel_index_archive_infinite, name='artikkel_index_archive_infinite'),
    path('kroonika/<int:year>/', ArtikkelYearArchiveView.as_view(), name='artikkel_year_archive'),
    path('kroonika/<int:year>/<int:month>/', ArtikkelMonthArchiveView.as_view(month_format='%m'), name='artikkel_month_archive'),
    path('kroonika/<int:year>/<int:month>/otheryears/', views.artikkel_month_archive_otheryears, name='artikkel_month_archive_otheryears'),
    path('kroonika/<int:year>/<int:month>/<int:day>/', ArtikkelDayArchiveView.as_view(month_format='%m'), name='artikkel_day_archive'),
    path('kroonika/mine_krono_kp', views.mine_krono_kp, name='mine_krono_kp'),
    path('kroonika/mine_krono_kuu', views.mine_krono_kuu, name='mine_krono_kuu'),
    # path('kroonika/mine_krono_aasta', views.mine_krono_aasta, name='mine_krono_aasta'),
    path('isik/', IsikFilterView.as_view(), name='wiki_isik_filter'),
    path('isik/<int:pk>-<str:slug>/', IsikDetailView.as_view(), name='wiki_isik_detail'),
    path('object_detail_seotud/<str:model>-<int:id>/', views.object_detail_seotud, name='wiki_object_detail_seotud'),
    path('get_object_data4tooltip/', views.get_object_data4tooltip, name='get_object_data4tooltip'),
    path('organisatsioon/', OrganisatsioonFilterView.as_view(), name='wiki_organisatsioon_filter'),
    path('organisatsioon/<int:pk>-<str:slug>/', OrganisatsioonDetailView.as_view(), name='wiki_organisatsioon_detail'),
    path('objekt/', ObjektFilterView.as_view(), name='wiki_objekt_filter'),
    path('objekt/<int:pk>-<str:slug>/', ObjektDetailView.as_view(), name='wiki_objekt_detail'),
    path('objekt/get_objekt_leaflet_combo/<int:objekt_id>/', views.get_objekt_leaflet_combo, name='get_objekt_leaflet_combo'),
    path('kaardiobjekt/', KaardiobjektFilterView.as_view(), name='wiki_kaardiobjekt_filter'),
    path('kaardiobjekt/<int:pk>/', KaardiobjektDetailView.as_view(), name='wiki_kaardiobjekt_detail'),
    path('kaardiobjekt/get_kaardiobjekt_leaflet/<int:kaardiobjekt_id>/', views.get_kaardiobjekt_leaflet, name='get_kaardiobjekt_leaflet'),
    path('kaardiobjekt/join_kaardiobjekt_with_objekt/<int:kaardiobjekt_id>-<int:objekt_id>/', views.join_kaardiobjekt_with_objekt, name='join_kaardiobjekt_with_objekt'),
    path('update/artikkel/<int:pk>', ArtikkelUpdate.as_view(), name='artikkel_update'),
    path('update/isik/<int:pk>', IsikUpdate.as_view(), name='isik_update'),
    path('update/organisatsioon/<int:pk>', OrganisatsioonUpdate.as_view(), name='organisatsioon_update'),
    path('update/objekt/<int:pk>', ObjektUpdate.as_view(), name='objekt_update'),
    path('update/kaardiobjekt/<int:pk>', KaardiobjektUpdate.as_view(), name='kaardiobjekt_update'),
    path('wiki_base_info/', views.wiki_base_info, name='wiki_base_info'),
    path('switch_vkj_ukj/<str:ukj>/', views.switch_vkj_ukj, name='switch_vkj_ukj'),
    # path('users/', UserList.as_view()),
    # path('users/<int:pk>/', UserDetail.as_view()),
    path('calendar_days_with_events_in_month/', views.calendar_days_with_events_in_month, name='calendar_days_with_events_in_month'),
]

