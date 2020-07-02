import ajax_select
from ajax_select import LookupChannel

from django.db.models.functions import Concat
from django.db.models import F, Value, CharField

from .models import Isik, Organisatsioon, Objekt, Viide

@ajax_select.register('isikud')
class IsikLookup(LookupChannel):

    model = Isik

    def get_query(self, q, request):
        splits = q.split(' ')
        queryset = self.model.objects.annotate(
            nimi=Concat(
                F('eesnimi'),
                Value(' '),
                F('perenimi'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(nimi__icontains=split)
        return queryset[:50]


@ajax_select.register('organisatsioonid')
class OrganisatsioonLookup(LookupChannel):

    model = Organisatsioon

    def get_query(self, q, request):
        splits = q.split(' ')
        queryset = self.model.objects.all()
        for split in splits:
            queryset = queryset.filter(nimi__icontains=split)
        return queryset[:50]


@ajax_select.register('objektid')
class ObjektLookup(LookupChannel):

    model = Objekt

    def get_query(self, q, request):
        splits = q.split(' ')
        queryset = self.model.objects.all()
        for split in splits:
            queryset = queryset.filter(nimi__icontains=split)
        return queryset[:50]


@ajax_select.register('viited')
class ViideLookup(LookupChannel):

    model = Viide

    def get_query(self, q, request):
        splits = q.split(' ')
        queryset = self.model.objects.annotate(
            full_viide=Concat(
                F('allikas__nimi'),
                Value(' '),
                F('peatykk'),
                Value(' '),
                F('hist_date'),
                Value(' '),
                F('kohaviit'),
                Value(' '),
                F('hist_year'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(full_viide__icontains=split)
        return queryset[:50]