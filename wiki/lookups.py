import ajax_select
from ajax_select import LookupChannel

from django.conf import settings
from django.db.models.functions import Concat
from django.db.models import F, Value, CharField

from .models import (
    Artikkel, Isik, Organisatsioon, Objekt,
    Allikas, Viide,
    Pilt,
    Kaardiobjekt
)

TRANSLATION = settings.TRANSLATION

@ajax_select.register('artiklid')
class ArtikkelLookup(LookupChannel):

    model = Artikkel

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        queryset = self.model.objects.daatumitega(request).annotate(
            full_viide=Concat(
                F('id'),
                Value(' '),
                F('kirjeldus'),
                Value(' '),
                F('dob'),
                Value(' '),
                F('yob'),
                output_field=CharField()
            ),
            # display=Concat(
            #     F('yob'),
            #     Value(':'),
            #     F('id'),
            #     Value(' '),
            #     F('kirjeldus_lyhike'),
            #     output_field=CharField()
            # )
        )
        for split in splits:
            queryset = queryset.filter(full_viide__iregex=split)
        return queryset[:50]

    def format_match(self, item):
        # artikkel = self.model.objects.daatumitega().get(id=item.id)
        return f"({item.hist_year}:{item.id}) {item}"
        # return item.display

    def format_item_display(self, item):
        # artikkel = self.model.objects.daatumitega().get(id=item.id)
        return f"({item.hist_year}:{item.id}) {item}"
        # return item.display


@ajax_select.register('isikud')
class IsikLookup(LookupChannel):

    model = Isik

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        # queryset = self.model.objects.daatumitega(request)
        queryset = self.model.objects.daatumitega(request).annotate(
        # queryset = self.model.objects.annotate(
            nimi=Concat(
                F('eesnimi'),
                Value(' '),
                F('perenimi'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(nimi__iregex=split)
        return queryset[:50]

    def format_match(self, item):
        return f"{item} ({item.id})"

    def format_item_display(self, item):
        return f"{item} ({item.id})"


@ajax_select.register('organisatsioonid')
class OrganisatsioonLookup(LookupChannel):

    model = Organisatsioon

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        queryset = self.model.objects.daatumitega(request)
        for split in splits:
            queryset = queryset.filter(nimi__iregex=split)
        return queryset[:50]


@ajax_select.register('objektid')
class ObjektLookup(LookupChannel):

    model = Objekt

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        # queryset = self.model.objects.daatumitega(request)
        queryset = self.model.objects.daatumitega(request).annotate(
            nimi_asukoht=Concat(
                F('nimi'),
                Value(' '),
                F('asukoht'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(nimi_asukoht__iregex=split)
        return queryset[:50]


@ajax_select.register('kaardiobjektid')
class KaardiobjektLookup(LookupChannel):

    model = Kaardiobjekt

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        queryset = self.model.objects.annotate(
            nimi_asukoht=Concat(
                F('tn'),
                Value(' '),
                F('nr'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(nimi_asukoht__iregex=split)
        return queryset[:50]


@ajax_select.register('viited')
class ViideLookup(LookupChannel):

    model = Viide

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
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
        ).order_by('-id')
        for split in splits:
            queryset = queryset.filter(full_viide__iregex=split)
        return queryset[:20]

    def format_match(self, item):
        return f"{item} ({item.id})"

    def format_item_display(self, item):
        return f"{item} (viide_{item.id})"

@ajax_select.register('allikad')
class AllikasLookup(LookupChannel):

    model = Allikas

    def get_query(self, q, request):
        splits = q.split(' ')
        queryset = self.model.objects.all()
        for split in splits:
            queryset = queryset.filter(nimi__icontains=split)
        return queryset[:20]


# @ajax_select.register('kaardiobjektid')
# class KaardiobjektLookup(LookupChannel):
#
#     model = Kaardiobjekt
#
#     def get_query(self, q, request):
#         splits = q.split(' ')
#         queryset = self.model.objects.annotate(nimi=Concat('tn', Value(' '), 'nr', Value(' '), 'lisainfo'))
#         for split in splits:
#             queryset = queryset.filter(nimi__icontains=split)
#         return queryset[:50]


@ajax_select.register('pildid')
class PiltLookup(LookupChannel):

    model = Pilt

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        queryset = self.model.objects.all()
        for split in splits:
            queryset = queryset.filter(nimi__iregex=split)
        return queryset[:50]

    def format_match(self, item):
        return f"{item} ({item.id})"

    def format_item_display(self, item):
        return f"{item} ({item.id})"
