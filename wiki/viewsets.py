from django.contrib.auth.models import User
from django.db.models import Q
import django_filters
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import (
    # Kroonika,
    Artikkel,
    Isik,
    Objekt,
    Organisatsioon,
    Pilt,
    Allikas,
    Viide
)
from .serializers import (
    UserSerializer,
    # KroonikaSerializer,
    ArtikkelSerializer,
    IsikSerializer,
    ObjektSerializer,
    OrganisatsioonSerializer,
    PiltSerializer,
    AllikasSerializer,
    ViideSerializer
)

# from .views import artikkel_qs_userfilter

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud


# class KroonikaViewSet(viewsets.ModelViewSet):
#     queryset = Kroonika.objects.all()
#     serializer_class = KroonikaSerializer


class ArtikkelFilter(filters.FilterSet):
    # Võimaldab API päringuid: http://18.196.203.237/api/artikkel/?aasta=1913&kuu=10
    aasta = django_filters.NumberFilter(field_name='hist_searchdate', lookup_expr='year')
    kuu = django_filters.NumberFilter(field_name='hist_searchdate', lookup_expr='month')
    p2ev = django_filters.NumberFilter(field_name='hist_searchdate', lookup_expr='day')
    # body_text = django_filters.CharFilter(field_name='body_text', lookup_expr='icontains')
    sisaldab = django_filters.CharFilter(method='filter_tags')

    def filter_tags(self, queryset, field_name, value):
        # value.replace(' ', '+') # juhuks kui tühikutega eraldatud märksõnad
        tags = value.split(' ')
        if len(tags) > 1:
            for tag in tags:
                queryset = queryset.filter(body_text__icontains=tag)
            return queryset
        else:
            return queryset.filter(body_text__icontains=value)


class ArtikkelViewSet(viewsets.ModelViewSet):
    queryset = Artikkel.objects.all()
    serializer_class = ArtikkelSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ArtikkelFilter

    def get_queryset(self):
        # return artikkel_qs_userfilter(self.request.user)
        return Artikkel.objects.daatumitega(self.request)

class IsikFilter(filters.FilterSet):
    perenimi = django_filters.CharFilter(field_name='perenimi', lookup_expr='icontains')
    eesnimi = django_filters.CharFilter(field_name='eesnimi', lookup_expr='icontains')
    nimi = django_filters.CharFilter(method='filter_nimi')
    sisaldab = django_filters.CharFilter(method='filter_tags')

    def filter_nimi(self, queryset, field_name, value):
        """
        Otsib fraasi ees- või perenimest
        :param queryset:
        :param field_name:
        :param value:
        :return: queryset
        """
        return queryset.filter(
            Q(eesnimi__icontains=value) | Q(perenimi__icontains=value)
        )

    def filter_tags(self, queryset, field_name, value):
        # value.replace(' ', '+') # juhuks kui tühikutega eraldatud märksõnad
        tags = value.split(' ')
        if len(tags) > 1:
            for tag in tags:
                queryset = queryset.filter(
                    Q(eesnimi__icontains=tag) |
                    Q(perenimi__icontains=tag)
                )
            return queryset
        else:
            return queryset.filter(
                    Q(eesnimi__icontains=value) |
                    Q(perenimi__icontains=value)
                )

class IsikViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Isiku kirje

    list:
    Isikute loetelu
    """
    queryset = Isik.objects.all()
    serializer_class = IsikSerializer
    # lookup_field = 'slug'
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = IsikFilter

    def get_queryset(self):
        return Isik.objects.daatumitega(self.request)


class ObjektFilter(filters.FilterSet):
    nimi = django_filters.CharFilter(field_name='nimi', lookup_expr='icontains')
    sisaldab = django_filters.CharFilter(method='filter_tags')

    def filter_tags(self, queryset, field_name, value):
        # value.replace(' ', '+') # juhuks kui tühikutega eraldatud märksõnad
        tags = value.split(' ')
        if len(tags) > 1:
            for tag in tags:
                queryset = queryset.filter(nimi__icontains=tag)
            return queryset
        else:
            return queryset.filter(nimi__icontains=value)


class ObjektViewSet(viewsets.ModelViewSet):
    queryset = Objekt.objects.all()
    serializer_class = ObjektSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ObjektFilter

    def get_queryset(self):
        return Objekt.objects.daatumitega(self.request)


class OrganisatsioonFilter(filters.FilterSet):
    nimi = django_filters.CharFilter(field_name='nimi', lookup_expr='icontains')
    sisaldab = django_filters.CharFilter(method='filter_tags')

    def filter_tags(self, queryset, field_name, value):
        # value.replace(' ', '+') # juhuks kui tühikutega eraldatud märksõnad
        tags = value.split(' ')
        if len(tags) > 1:
            for tag in tags:
                queryset = queryset.filter(nimi__icontains=tag)
            return queryset
        else:
            return queryset.filter(nimi__icontains=value)


class OrganisatsioonViewSet(viewsets.ModelViewSet):
    queryset = Organisatsioon.objects.all()
    serializer_class = OrganisatsioonSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = OrganisatsioonFilter

    def get_queryset(self):
        return Organisatsioon.objects.daatumitega(self.request)


class PiltViewSet(viewsets.ModelViewSet):
    queryset = Pilt.objects.all()
    serializer_class = PiltSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud


class AllikasViewSet(viewsets.ModelViewSet):
    queryset = Allikas.objects.all()
    serializer_class = AllikasSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud


class ViideViewSet(viewsets.ModelViewSet):
    queryset = Viide.objects.all()
    serializer_class = ViideSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
