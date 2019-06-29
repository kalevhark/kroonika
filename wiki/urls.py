from django.urls import path

from . import views

# Objektivaated
from wiki.views import ArtikkelDetailView, IsikDetailView, OrganisatsioonDetailView, ObjektDetailView
# Filtreerimisvaated
from wiki.views import ArtikkelFilterView, IsikFilterView, OrganisatsioonFilterView, ObjektFilterView
# Loendivaated
from wiki.views import ArtikkelArchiveIndexView, ArtikkelYearArchiveView, ArtikkelMonthArchiveView, ArtikkelDayArchiveView
# Muutmisvaated
from wiki.views import ArtikkelUpdate, IsikUpdate, OrganisatsioonUpdate, ObjektUpdate

app_name = 'wiki'
urlpatterns = [
    path('', ArtikkelFilterView.as_view(), name='wiki_artikkel_filter'),
    path('<int:pk>', ArtikkelDetailView.as_view(), name='wiki_artikkel_detail'),
    path('info/', views.info, name='info'),
    # path('feedback/', views.feedback, name='feedback'),
    path('krono/', ArtikkelArchiveIndexView.as_view(), name='artikkel_index_archive'),
    path('krono/<int:year>/', ArtikkelYearArchiveView.as_view(), name='artikkel_year_archive'),
    path('krono/<int:year>/<int:month>/', ArtikkelMonthArchiveView.as_view(month_format='%m'), name='artikkel_month_archive'),
    path('krono/<int:year>/<int:month>/<int:day>/', ArtikkelDayArchiveView.as_view(month_format='%m'), name='artikkel_day_archive'),
    path('krono/mine_krono_kp', views.mine_krono_kp, name='mine_krono_kp'),
    path('isik/', IsikFilterView.as_view(), name='wiki_isik_filter'),
    path('isik/<int:pk>', IsikDetailView.as_view(), name='wiki_isik_detail'),
    path('organisatsioon/', OrganisatsioonFilterView.as_view(), name='wiki_organisatsioon_filter'),
    path('organisatsioon/<int:pk>', OrganisatsioonDetailView.as_view(), name='wiki_organisatsioon_detail'),
    path('objekt/', ObjektFilterView.as_view(), name='wiki_objekt_filter'),
    path('objekt/<int:pk>', ObjektDetailView.as_view(), name='wiki_objekt_detail'),
    path('update/krono/<int:pk>', ArtikkelUpdate.as_view(), name='artikkel_update'),
    path('update/isik/<int:pk>', IsikUpdate.as_view(), name='isik_update'),
    path('update/organisatsioon/<int:pk>', OrganisatsioonUpdate.as_view(), name='organisatsioon_update'),
    path('update/objekt/<int:pk>', ObjektUpdate.as_view(), name='objekt_update'),
    ]

