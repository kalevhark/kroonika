import ajax_select
from ajax_select import LookupChannel

from django.conf import settings
from django.db.models.functions import Concat
from django.db.models import F, Value, CharField

from .models import (
    Aadress, Artikkel, Isik, Kaart, Organisatsioon, Objekt,
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
        return f"({item.hist_year}:{item.id}) {item}"

    def format_item_display(self, item):
        # return f"({item.hist_year}:{item.id}) {item}"
        copy_icon = f'<span class="ui-icon ui-icon-copy" id="copy_artikkel_{item.id}">X</span>'
        return f'({item.hist_year}:{item.id}) {item} (artikkel_{item.id}) {copy_icon}'


@ajax_select.register('isikud')
class IsikLookup(LookupChannel):

    model = Isik

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        queryset = self.model.objects.daatumitega(request).annotate(
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
        copy_icon = f'<span class="ui-icon ui-icon-copy" id="copy_isik_{item.id}">X</span>'
        return f'{item} (isik_{item.id}) {copy_icon}'


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
    
    def format_match(self, item):
        return f"{item} ({item.id})"

    def format_item_display(self, item):
        copy_icon = f'<span class="ui-icon ui-icon-copy" id="copy_organisatsioon_{item.id}">X</span>'
        return f'{item} (organisatsioon_{item.id}) {copy_icon}'


@ajax_select.register('objektid')
class ObjektLookup(LookupChannel):

    model = Objekt

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.latest_map = Kaart.objects.order_by('-aasta').first()

    def _exists_on_latest_map(self, item):
        if item.kaardiobjektid.filter(kaart=self.latest_map).exists():
            return True
        return False
    
    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
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
    
    def format_match(self, item):
        if self._exists_on_latest_map(item):
            color = settings.OBJEKT_COLOR
            exists_on_latest_map = f'<span style="color: {color};">&checkmark;</span>'
        else:
            exists_on_latest_map = ''
        if item.gone or item.hist_enddate or item.hist_endyear:
            color = settings.GONE_COLOR
            objekt_gone = f'<span style="color: {color};">&chi;</span>'
        else:
            objekt_gone = ''
        return f"{item} ({item.id}) {exists_on_latest_map}{objekt_gone}"

    def format_item_display(self, item):
        if self._exists_on_latest_map(item):
            color = settings.OBJEKT_COLOR
            exists_on_latest_map = f'<span style="color: {color};">&checkmark;</span>'
        else:
            exists_on_latest_map = ''
        if item.gone or item.hist_enddate or item.hist_endyear:
            color = settings.GONE_COLOR
            objekt_gone = f'<span style="color: {color};">&chi;</span>'
        else:
            objekt_gone = ''
        copy_icon = f'<span class="ui-icon ui-icon-copy" id="copy_objekt_{item.id}"></span>'
        return f"{item} (objekt_{item.id}) {exists_on_latest_map}{objekt_gone} {copy_icon}"


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
                Value(' '),
                F('lisainfo'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(nimi_asukoht__iregex=split)
        return queryset[:50]

    def format_match(self, item):
        return f"{item} ({item.id})"

    def format_item_display(self, item):
        return f'<p>{item}</p>{item.get_leaflet()}'
    

@ajax_select.register('aadressid')
class AadressLookup(LookupChannel):

    model = Aadress

    def get_query(self, q, request):
        q = q.translate(str.maketrans(TRANSLATION))
        splits = q.split(' ')
        queryset = self.model.objects.annotate(
            nimi_asukoht=Concat(
                F('nimi'),
                Value(' '),
                F('korter'),
                output_field=CharField()
            )
        )
        for split in splits:
            queryset = queryset.filter(nimi_asukoht__iregex=split)
        return queryset[:50]

    def format_match(self, item):
        return f"{item} ({item.id})"

    def format_item_display(self, item):
        return f'{item} ({item.id})'
    

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
        copy_icon = f'<span class="ui-icon ui-icon-copy" id="copy_viide_{item.id}">X</span>'
        return f'{item} (viide_{item.id}) {copy_icon}'

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
        copy_icon = f'<span class="ui-icon ui-icon-copy" id="copy_pilt_{item.id}">X</span>'
        return f'{item} (pilt_{item.id}) {copy_icon}'
