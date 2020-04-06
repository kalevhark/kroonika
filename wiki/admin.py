# import datetime

from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
# from django.db.models import Count
from markdownx.admin import MarkdownxModelAdmin

from .models import Allikas, Viide, Kroonika, Artikkel, Isik, Organisatsioon, Objekt, Pilt, Vihje
from .forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm


#
# Piltide lisamiseks artiklite halduris
#
class PiltArtikkelInline(admin.TabularInline):
    model = Pilt.artiklid.through
    extra = 1


#
# Piltide lisamiseks isikute halduris
#
class PiltIsikInline(admin.TabularInline):
    model = Pilt.isikud.through
    extra = 1


#
# Piltide lisamiseks organisatsioonide halduris
#
class PiltOrganisatsioonInline(admin.TabularInline):
    model = Pilt.organisatsioonid.through
    extra = 1


#
# Piltide lisamiseks objektide halduris
#
class PiltObjektInline(admin.TabularInline):
    model = Pilt.objektid.through
    extra = 1


class AllikasAdmin(admin.ModelAdmin):
    search_fields = ['nimi']
    readonly_fields = ['inp_date', 'mod_date', 'created_by', 'updated_by']
    list_display = (
        'id',
        'nimi',
        'hist_year'
    )
    filter_horizontal = [
        'autorid',
    ]
    fieldsets = [
        (None, {
            'fields': ['nimi', 'autorid', 'hist_year', 'kirjeldus', 'url']}),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]}),
    ]

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        objekt.save()
        form.save_m2m()
        return objekt


class ViideAdmin(admin.ModelAdmin):
    readonly_fields = [
        'mod_date',
        'seotud_artiklid',
        'seotud_isikud',
        'seotud_organisatsioonid',
        'seotud_objektid',
        'seotud_pildid',
    ]
    list_display = [
        'id',
        'seotud_allikas',
        'peatykk',
        'hist_date',
        'kohaviit',
        'short_url',
        'seotud_objects',
        # 'seotud_artikleid',
        # 'seotud_isikuid',
        # 'seotud_organisatsioone',
        # 'seotud_objekte',
        # 'seotud_pilte',
    ]
    ordering = ['-id']
    search_fields = [
        'id',
        'allikas__nimi',
        'hist_date',
        'kohaviit',
        'url'
    ]
    fieldsets = [
        (None, {
            'fields': [
                'allikas',
                'kohaviit',
                'hist_date',
                'hist_year',
                'peatykk',
                'marker',
                'url'
            ]
        }),
        (None, {
            'fields': [
                'mod_date',
                'seotud_artiklid',
                'seotud_isikud',
                'seotud_organisatsioonid',
                'seotud_objektid',
                'seotud_pildid',
            ]
        }),
    ]

    # Seotud allika nimi
    def seotud_allikas(self, obj):
        return obj.allikas.nimi

    seotud_allikas.short_description = 'Allikas'

    # Kui palju on viitega seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()

    seotud_artikleid.short_description = 'Lugusid'

    # Seotud artiklid
    def seotud_artiklid(self, obj):
        id_list = list(obj.artikkel_set.values_list('id', flat=True))
        return ', '.join([str(el) for el in id_list])

    # Kui palju on viitega seotud isikuid
    def seotud_isikuid(self, obj):
        return obj.isik_set.count()

    seotud_isikuid.short_description = 'Isikuid'

    # Seotud isikud
    def seotud_isikud(self, obj):
        id_list = list(obj.isik_set.values_list('id', flat=True))
        return ', '.join([str(el) for el in id_list])

    # Kui palju on viitega seotud organisatsioone
    def seotud_organisatsioone(self, obj):
        return obj.organisatsioon_set.count()

    seotud_organisatsioone.short_description = 'Asutisi'

    # Seotud organisatsioonid
    def seotud_organisatsioonid(self, obj):
        id_list = list(obj.organisatsioon_set.values_list('id', flat=True))
        return ', '.join([str(el) for el in id_list])

    # Kui palju on viitega seotud objekte
    def seotud_objekte(self, obj):
        return obj.objekt_set.count()

    seotud_objekte.short_description = 'Kohti'

    # Seotud objektid
    def seotud_objektid(self, obj):
        id_list = list(obj.objekt_set.values_list('id', flat=True))
        return ', '.join([str(el) for el in id_list])

    # Kui palju on viitega seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()

    seotud_pilte.short_description = 'Pilte'

    # Seotud pildid
    def seotud_pildid(self, obj):
        id_list = list(obj.pilt_set.values_list('id', flat=True))
        return ', '.join([str(el) for el in id_list])

    # Seotud andmebaasikirjeid kokku
    def seotud_objects(self, obj):
        return (
                self.seotud_artikleid(obj) +
                self.seotud_isikuid(obj) +
                self.seotud_organisatsioone(obj) +
                self.seotud_objekte(obj) +
                self.seotud_pilte(obj)
        )
    def short_url(self, obj):
        if obj.url:
            if len(obj.url) < 33:
                tekst = obj.url
            else:
                tekst = obj.url[:30] + '...'
        else:
            tekst = ''
        return tekst

    short_url.short_description = 'Link'

class ArtikkelAdmin(MarkdownxModelAdmin):
    form = ArtikkelForm
    readonly_fields = [
        'hist_searchdate',
        'inp_date', 'created_by',
        'mod_date', 'updated_by',
        'last_accessed', 'total_accessed'
    ]
    list_display = (
        'id',
        'headline',
        'hist_year',
        'hist_month',
        'format_hist_date',
        'format_mod_date',
        'seotud_isikuid',
        'seotud_organeid',
        'seotud_objekte',
        'seotud_pilte',
        'seotud_viiteid',
        'revised' # TODO: Ajutine ümberkorraldamiseks
    )
    list_filter = ['hist_year']
    search_fields = [
        'body_text',
        'id'
    ]
    filter_horizontal = [
        'viited',
        'isikud',
        'organisatsioonid',
        'objektid',
    ]
    fieldsets = [
        (None, {
            'fields': [('body_text')]
            }
         ),
        ('Toimus', {
            'fields': [('hist_date', 'hist_year', 'hist_month', 'hist_enddate')]
            }
         ),
        ('Viited', {
            'fields': [('viited')]
        }
         ),
        ('Seotud', {
            'fields': [('isikud', 'organisatsioonid', 'objektid')]
            }
         ),
        ('Kroonika', {
            'fields': [('kroonika', 'lehekylg')]
            }
         ),
        (None, {
            'fields': ['hist_searchdate']
            }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
        (None, {
            'fields': [('last_accessed', 'total_accessed')]
            }
         ),
    ]
    inlines = [
        PiltArtikkelInline,
    ]

    # Kuupäevavälja vormindamiseks
    def format_hist_date(self, obj):
        if obj.hist_date:
            return obj.hist_date.strftime("%d.%m.%Y")
        else:
            return obj.hist_date

    format_hist_date.short_description = 'Kuupäev'

    # Kuupäevavälja vormindamiseks
    def format_mod_date(self, obj):
        if obj.mod_date:
            return obj.mod_date.strftime("%d.%m.%Y %H:%M")
        else:
            return obj.mod_date

    format_mod_date.short_description = 'Muudetud'

    # Kui palju on artikliga seotud organisatsioone
    def seotud_organeid(self, obj):
        return obj.organisatsioonid.count()
    seotud_organeid.short_description = 'Ühendusi'

    # Kui palju on artikliga seotud isikuid
    def seotud_isikuid(self, obj):
        return obj.isikud.count()
    seotud_isikuid.short_description = 'Isikuid'

    # Kui palju on artikliga seotud objekte
    def seotud_objekte(self, obj):
        return obj.objektid.count()
    seotud_objekte.short_description = 'Objekte'

    # Kui palju on objektiga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on objektiga seotud viiteid
    def seotud_viiteid(self, obj):
        return obj.viited.count()
    seotud_viiteid.short_description = 'Viiteid'

    # TODO: Ajutine func ümberkorraldamiseks
    def revised(self, obj):
        return _boolean_icon(
            obj.kroonika == None and
            obj.viited.count() > 0
        )

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        # if objekt.hist_date:
        #     objekt.hist_year = objekt.hist_date.year
        #     objekt.hist_month = objekt.hist_date.month
        #     objekt.hist_searchdate = objekt.hist_date
        # else:
        #     if objekt.hist_year:
        #         y = objekt.hist_year
        #         if objekt.hist_month:
        #             m = objekt.hist_month
        #         else:
        #             m = 1
        #         objekt.hist_searchdate = datetime.datetime(y, m, 1)
        #     else:
        #         objekt.hist_searchdate = None
        objekt.save()
        form.save_m2m()
        return objekt

    
class IsikAdmin(MarkdownxModelAdmin):
    form = IsikForm
    list_display = (
        'id',
        'perenimi',
        'eesnimi',
        'eluaeg',
        'seotud_artikleid',
        'seotud_pilte',
        'seotud_viiteid',
    )
    search_fields = [
        'id',
        'perenimi'
    ]
    readonly_fields = [
        'inp_date',
        'mod_date',
        'created_by',
        'updated_by'
    ]
    fieldsets = [
        (None, {
            'fields': ['eesnimi', 'perenimi']
            }
         ),
        ('Elas', {
            'fields': [
                ('hist_date',
                 'synd_koht',
                 'hist_year',
                 'hist_enddate',
                 'surm_koht',
                 'hist_endyear',
                 'gone',
                 'maetud'
                 )]
            }
         ),
        ('Lisainfo', {
            'fields': [('kirjeldus')]
            }
         ),
        ('Viited', {
            'fields': [('viited')]
        }
         ),
        ('Seotud', {
            'fields': [('organisatsioonid', 'objektid')]
            }
         ),

        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]
    filter_horizontal = [
        'viited',
        'organisatsioonid',
        'objektid',
    ]
    inlines = [
        PiltIsikInline,
    ]

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # Lisame sünnikuupäeva põhjal sünniaasta
        # if objekt.hist_date:
        #     objekt.hist_year = objekt.hist_date.year
        objekt.save()
        form.save_m2m()
        return objekt

    def eluaeg(self, obj):
        if obj.hist_date:
            sy = obj.hist_date.strftime('%d.%m.%Y')
        else:
            if obj.hist_year:
                sy = str(obj.hist_year)
            else:
                sy = ''
        if obj.hist_enddate:
            su = obj.hist_enddate.strftime('%d.%m.%Y')
        elif obj.hist_endyear:
            su = str(obj.hist_endyear)
        elif obj.gone:
            su = '?'
        else:
            su = ''
        daatumid = f'{sy}-{su}' if any([sy, su]) else ''
        return daatumid

    def hist_date_view(self, obj):
        return obj.hist_date
    hist_date_view.empty_value_display = '?'

    # Kui palju on isikuga seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()
    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on isikuga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on objektiga seotud viiteid
    def seotud_viiteid(self, obj):
        return obj.viited.count()
    seotud_viiteid.short_description = 'Viiteid'

class OrganisatsioonAdmin(MarkdownxModelAdmin):
    form = OrganisatsioonForm
    readonly_fields = [
        'inp_date',
        'mod_date',
        'created_by',
        'updated_by'
    ]
    list_display = [
        'id',
        'nimi',
        'hist_date',
        'hist_year',
        'hist_endyear',
        'seotud_artikleid',
        'seotud_pilte',
        'seotud_viiteid',
    ]
    fieldsets = [
        (None, {
            'fields': ['nimi', 'kirjeldus']
        }
         ),
        (None, {
            'fields': ['hist_date', 'hist_year', 'hist_month']
        }
         ),
        (None, {
            'fields': ['hist_enddate', 'hist_endyear', 'gone']
        }
         ),
        ('Viited', {
            'fields': [('viited')]
        }
         ),
        ('Seotud', {
            'fields': ['objektid']
        }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
        }
         ),
    ]
    filter_horizontal = [
        'viited',
        'objektid',
    ]
    inlines = [
        PiltOrganisatsioonInline,
    ]
    search_fields = ['id', 'nimi']

    # Kui palju on organisatsiooniga seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()
    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on objektiga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on objektiga seotud viiteid
    def seotud_viiteid(self, obj):
        return obj.viited.count()
    seotud_viiteid.short_description = 'Viiteid'

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        # if objekt.hist_date:
        #     objekt.hist_year = objekt.hist_date.year
        #     objekt.hist_month = objekt.hist_date.month
        #     objekt.hist_searchdate = objekt.hist_date
        # else:
        #     if objekt.hist_year:
        #         y = objekt.hist_year
        #         if objekt.hist_month:
        #             m = objekt.hist_month
        #         else:
        #             m = 1
        #         objekt.hist_searchdate = datetime.datetime(y, m, 1)
        #     else:
        #         objekt.hist_searchdate = None
        # if objekt.hist_enddate:
        #     objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return objekt


class ObjektAdmin(MarkdownxModelAdmin):
    form = ObjektForm
    readonly_fields = [
        # 'hist_searchdate',
        'inp_date', 'created_by',
        'mod_date', 'updated_by',
    ]
    list_display = [
        'id',
        'nimi',
        'hist_date',
        'hist_year',
        'hist_month',
        'seotud_artikleid',
        'seotud_pilte',
        'seotud_viiteid',
    ]
    search_fields = ['id', 'nimi']
    fieldsets = [
        (None, {
            'fields': ['nimi', 'tyyp', 'asukoht', 'kirjeldus']
            }
         ),
        (None, {
            'fields': ['hist_date', 'hist_year', 'hist_month']
            }
         ),
        (None, {
            'fields': ['hist_enddate', 'hist_endyear', 'gone']
            }
         ),
        ('Viited', {
            'fields': [('viited')]
        }
         ),
        ('Seotud', {
            'fields': ['objektid']
            }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]
    filter_horizontal = [
        'viited',
        'objektid',
    ]
    inlines = [
        PiltObjektInline,
    ]

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        # if objekt.hist_date:
        #     objekt.hist_year = objekt.hist_date.year
        #     objekt.hist_month = objekt.hist_date.month
        #     objekt.hist_searchdate = objekt.hist_date
        # else:
        #     if objekt.hist_year:
        #         y = objekt.hist_year
        #         if objekt.hist_month:
        #             m = objekt.hist_month
        #         else:
        #             m = 1
        #         objekt.hist_searchdate = datetime.datetime(y, m, 1)
        #     else:
        #         objekt.hist_searchdate = None
        # if objekt.hist_enddate:
        #     objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return objekt

    # Kui palju on objektiga seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()
    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on objektiga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on objektiga seotud viiteid
    def seotud_viiteid(self, obj):
        return obj.viited.count()
    seotud_viiteid.short_description = 'Viiteid'


class KroonikaAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date', 'mod_date', 'created_by', 'updated_by']
    fieldsets = [
        (None, {
            'fields': ['nimi', 'kirjeldus']}),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]}),
    ]
    

class PiltAdmin(admin.ModelAdmin):
    readonly_fields = [
        'pilt_height_field',
        'pilt_width_field',
        'inp_date', 'created_by', 'mod_date', 'updated_by',
    ]
    list_display = [
        'id',
        'nimi',
        'kasutatud',
        'profiilipilt',
        'pilt',
        'pildi_suurus']
    search_fields = ['nimi']
    filter_horizontal = (
        'viited',
        'allikad',
        'artiklid',
        'isikud',
        'organisatsioonid',
        'objektid'
    )
    # form = PiltForm
    fieldsets = [
        (None, {
            'fields': ['nimi', 'autor', 'kirjeldus', 'pilt']
            }
         ),
        (None, {
            'fields': ['hist_date', 'hist_year', 'hist_month']
            }
         ),
        ('Viited', {
            'fields': [('viited')]
        }
         ),
        ('Seotud', {
            'fields': [
                ('allikad',
                'artiklid',
                'isikud',
                'organisatsioonid',
                'objektid',
                 )
            ]
        }
         ),
        ('Profiilipilt', {
            'fields': [('profiilipilt_allikas',
                        'profiilipilt_artikkel',
                        'profiilipilt_isik',
                        'profiilipilt_organisatsioon',
                        'profiilipilt_objekt')]
        }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]
    # inlines = [
    #     PiltInline,
    # ]


    def link(self, obj):
        if obj.pilt:
            return obj.pilt.url
        else:
            return 'pilti pole'

    def profiilipilt(self, obj):
        # Kas pilti kasutatakse profiilipildina?
        return _boolean_icon(
            obj.profiilipilt_allikas or
            obj.profiilipilt_artikkel or
            obj.profiilipilt_isik or
            obj.profiilipilt_organisatsioon or
            obj.profiilipilt_objekt
        )

    def pildi_suurus(self, obj):
        return f'{obj.pilt_width_field}x{obj.pilt_height_field}',

    def kasutatud(self, obj):
        # Mitu korda on pildile viidatud
        return (
            obj.artiklid.count() +
            obj.isikud.count() +
            obj.organisatsioonid.count() +
            obj.objektid.count() +
            obj.allikad.count()
        )

    def save_model(self, request, obj, form, change):
        # Admin moodulis lisamise/muutmise automaatsed väljatäited
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        # if objekt.hist_date:
        #     objekt.hist_year = objekt.hist_date.year
        #     objekt.hist_month = objekt.hist_date.month
        objekt.save()
        form.save_m2m()
        return objekt

    # def formfield_for_manytomany(self, db_field, request, **kwargs):
    #     if db_field.name == "artiklid":
    #         kwargs["queryset"] = Artikkel.objects.annotate('hist_year=1911)
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


class VihjeAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date']
    fieldsets = [
        (None, {
            'fields': [
                'kirjeldus',
                'kontakt',
                'http_referer',
                'remote_addr',
                'http_user_agent',
                'django_version'
            ]
        }),
        (None, {
            'fields': [('inp_date', 'end_date')]}),
    ]
    list_display = [
        'id',
        'inp_date',
        'lyhi_kirjeldus',
        'kontakt',
        'http_referer',
        'done'
    ]

    def lyhi_kirjeldus(self, obj):
        if len(obj.kirjeldus) < 33:
            tekst = obj.kirjeldus
        else:
            tekst = obj.kirjeldus[:30] + '...'
        return tekst

    lyhi_kirjeldus.short_description = 'Vihje'

    def done(self, obj):
        return _boolean_icon(
            obj.end_date != None
        )

admin.site.register(Allikas, AllikasAdmin)
admin.site.register(Viide, ViideAdmin)
admin.site.register(Kroonika, KroonikaAdmin)
admin.site.register(Artikkel, ArtikkelAdmin)
admin.site.register(Isik, IsikAdmin)
admin.site.register(Organisatsioon, OrganisatsioonAdmin)
admin.site.register(Objekt, ObjektAdmin)
admin.site.register(Pilt, PiltAdmin)
admin.site.register(Vihje, VihjeAdmin)
