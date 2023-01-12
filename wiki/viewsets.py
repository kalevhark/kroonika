from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
from django.utils.safestring import mark_safe

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

TRANSLATION = settings.TRANSLATION

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

    # def filter_tags(self, queryset, field_name, value):
    #     value = value.translate(str.maketrans(TRANSLATION))
    #     tags = value.split(' ')
    #     if len(tags) > 1:
    #         for tag in tags:
    #             queryset = queryset.filter(body_text__iregex=tag)
    #         return queryset
    #     else:
    #         return queryset.filter(body_text__iregex=value)

    def filter_tags(self, queryset, field_name, value):
        value = value.translate(str.maketrans(TRANSLATION))
        tags = value.split(' ')
        for tag in tags:
            queryset = queryset.filter(kirjeldus__iregex=rf'{tag}')
        return queryset

class ArtikkelViewSet(viewsets.ModelViewSet):
    queryset = Artikkel.objects.all()
    serializer_class = ArtikkelSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ArtikkelFilter

    def get_queryset(self):
        queryset = Artikkel.objects.daatumitega(self.request). \
            annotate(
                kirjeldus=Concat(
                    F('hist_year'), Value(' '), F('body_text'), output_field=CharField()
                )
        )
        return queryset

    def get_view_name(self) -> str:
        return "Lood"

    def get_view_description(self, html=False) -> str:
        text = "Valga linna kroonika"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


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
        value = value.translate(str.maketrans(TRANSLATION))
        tags = value.split(' ')
        for tag in tags:
            queryset = queryset.filter(
                Q(eesnimi__iregex=rf'{tag}') |
                Q(perenimi__iregex=rf'{tag}')
            )
        return queryset


class IsikViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Isiku kirje

    list:
    Isikute loetelu
    """
    queryset = Isik.objects.all()
    serializer_class = IsikSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IsikFilter

    def get_queryset(self):
        return Isik.objects.daatumitega(self.request)

    def get_view_name(self) -> str:
        return "Isikud"

    def get_view_description(self, html=False) -> str:
        text = "Inimesed"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class ObjektFilter(filters.FilterSet):
    nimi = django_filters.CharFilter(field_name='nimi', lookup_expr='icontains')
    sisaldab = django_filters.CharFilter(method='filter_tags')

    def filter_tags(self, queryset, field_name, value):
        value = value.translate(str.maketrans(TRANSLATION))
        tags = value.split(' ')
        for tag in tags:
            queryset = queryset.filter(
                Q(nimi__iregex=rf'{tag}') |
                Q(asukoht__iregex=rf'{tag}')
            )
        return queryset

class ObjektViewSet(viewsets.ModelViewSet):
    queryset = Objekt.objects.all()
    serializer_class = ObjektSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ObjektFilter

    def get_queryset(self):
        return Objekt.objects.daatumitega(self.request)

    def get_view_name(self) -> str:
        return "Kohad"

    def get_view_description(self, html=False) -> str:
        text = "Hooned, rajatised jms."
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class OrganisatsioonFilter(filters.FilterSet):
    nimi = django_filters.CharFilter(field_name='nimi', lookup_expr='icontains')
    sisaldab = django_filters.CharFilter(method='filter_tags')

    def filter_tags(self, queryset, field_name, value):
        value = value.translate(str.maketrans(TRANSLATION))
        tags = value.split(' ')
        for tag in tags:
            queryset = queryset.filter(nimi__iregex=rf'{tag}')
        return queryset


class OrganisatsioonViewSet(viewsets.ModelViewSet):
    queryset = Organisatsioon.objects.all()
    serializer_class = OrganisatsioonSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud
    # Järgnev vajalik, et saaks teha filtreeritud API päringuid
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = OrganisatsioonFilter

    def get_queryset(self):
        return Organisatsioon.objects.daatumitega(self.request)

    def get_view_name(self) -> str:
        return "Asutised"

    def get_view_description(self, html=False) -> str:
        text = "Asutused, organisatsioonid, seltsid jms"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class PiltViewSet(viewsets.ModelViewSet):
    queryset = Pilt.objects.all()
    serializer_class = PiltSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud

    def get_view_name(self) -> str:
        return "Pildid"

    def get_view_description(self, html=False) -> str:
        text = "Kasutatud pildid"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text

class AllikasViewSet(viewsets.ModelViewSet):
    queryset = Allikas.objects.all()
    serializer_class = AllikasSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud

    def get_view_name(self) -> str:
        return "Allikad"

    def get_view_description(self, html=False) -> str:
        text = "Kasutatud allikad"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text


class ViideViewSet(viewsets.ModelViewSet):
    queryset = Viide.objects.all()
    serializer_class = ViideSerializer
    http_method_names = ['get', 'head']  # post, put, delete, patch pole lubatud

    def get_view_name(self) -> str:
        return "Viited"

    def get_view_description(self, html=False) -> str:
        text = "Kasutatud viited"
        if html:
            return mark_safe(f"<p>{text}</p>")
        else:
            return text