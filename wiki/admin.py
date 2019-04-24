from django.contrib import admin
# from django.db.models import Count
# from django.forms import ModelForm
import datetime

from .models import Allikas, Viide, Kroonika, Artikkel, Isik, Organisatsioon, Objekt, Pilt
from .forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm

    
class AllikasAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date', 'mod_date', 'created_by', 'updated_by']
    list_display = (
        'id',
        'nimi',
        'hist_year'
    )
    fieldsets = [
        (None, {
            'fields': ['nimi', 'hist_year', 'kirjeldus', 'url']}),
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
    readonly_fields = ['mod_date']
    list_display = (
        'id',
        'kohaviit',
        'seotud_allikas',
        'seotud_artikleid',
        'seotud_isikuid',
        'seotud_organeid',
        'seotud_objekte',
        'seotud_pilte',
    )
    fieldsets = [
        (None, {
            'fields': [
                'allikas',
                'hist_date',
                'hist_year',
                'kohaviit',
                'marker',
                'url'
            ]
        }),
        (None, {
            'fields': [('mod_date')]}),
    ]

    # Seotud allika nimi
    def seotud_allikas(self, obj):
        return obj.allikas.nimi

    seotud_allikas.short_description = 'Allikas'

    # Kui palju on viitega seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()

    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on viitega seotud organisatsioone
    def seotud_organeid(self, obj):
        return obj.organisatsioon_set.count()

    seotud_organeid.short_description = 'Ühendusi'

    # Kui palju on artikliga seotud isikuid
    def seotud_isikuid(self, obj):
        return obj.isik_set.count()

    seotud_isikuid.short_description = 'Isikuid'

    # Kui palju on artikliga seotud objekte
    def seotud_objekte(self, obj):
        return obj.objekt_set.count()

    seotud_objekte.short_description = 'Objekte'

    # Kui palju on objektiga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()

    seotud_pilte.short_description = 'Pilte'


class ArtikkelAdmin(admin.ModelAdmin):
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
        'seotud_viiteid'
    )
    list_filter = ['hist_year']
    search_fields = ['body_text']
    filter_horizontal = [
        'isikud',
        'organisatsioonid',
        'objektid',
        'viited'
    ]
    fieldsets = [
        (None, {
            'fields': ['body_text']
            }
         ),
        ('Toimus', {
            'fields': [('hist_date', 'hist_year', 'hist_month', 'hist_enddate')]
            }
         ),
        ('Seotud', {
            'fields': [('isikud', 'organisatsioonid', 'objektid')]
            }
         ),
        ('Viited', {
            'fields': [('viited')]
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
    seotud_pilte.short_description = 'Viiteid'

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        objekt.save()
        form.save_m2m()
        return objekt

    
class IsikAdmin(admin.ModelAdmin):
    form = IsikForm
    list_display = (
        'perenimi',
        'eesnimi',
        'eluaeg',
        'seotud_artikleid',
        'seotud_pilte',
    )
    search_fields = ['perenimi']
    readonly_fields = ['inp_date', 'mod_date', 'created_by', 'updated_by']
    fieldsets = [
        (None, {
            'fields': ['eesnimi', 'perenimi']
            }
         ),
        ('Elas', {
            'fields': [('hist_date', 'synd_koht', 'hist_enddate', 'surm_koht', 'maetud')]
            }
         ),
        ('Lisainfo', {
            'fields': [('kirjeldus')]
            }
         ),
        ('Seotud', {
            'fields': [('organisatsioonid', 'objektid')]
            }
         ),
        ('Viited', {
            'fields': [('viited')]
            }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]
    filter_horizontal = [
        'organisatsioonid',
        'objektid',
        'viited'
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

    def eluaeg(self, obj):
        if obj.hist_date:
            sy = obj.hist_date.strftime('%d.%m.%Y')
        else:
            sy = ''
        if obj.hist_enddate:
            su = obj.hist_enddate.strftime('%d.%m.%Y')
        else:
            su = ''
        return sy + '-' + su

    def hist_date_view(self, obj):
        return obj.hist_date
    hist_date_view.empty_value_display = '?'

    # Kui palju on isikuga seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()
    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on objektiga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()
    seotud_pilte.short_description = 'Pilte'


class OrganisatsioonAdmin(admin.ModelAdmin):
    form = OrganisatsioonForm
    readonly_fields = [
        'inp_date',
        'mod_date',
        'hist_searchdate',
        'created_by',
        'updated_by'
    ]
    list_display = [
        'nimi',
        'hist_date',
        'hist_year',
        'hist_month',
        'seotud_artikleid',
        'seotud_pilte',
    ]
    filter_horizontal = [
        'viited'
    ]
    search_fields = ['nimi']

    # Kui palju on organisatsiooniga seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()
    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on objektiga seotud pilte
    def seotud_pilte(self, obj):
        return obj.pilt_set.count()
    seotud_pilte.short_description = 'Pilte'

    # Admin moodulis lisamise/muutmise automaatsed väljatäited
    def save_model(self, request, obj, form, change):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = request.user
        else:
            objekt.updated_by = request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return objekt


class ObjektAdmin(admin.ModelAdmin):
    form = ObjektForm
    readonly_fields = [
        'hist_searchdate',
        'inp_date', 'created_by',
        'mod_date', 'updated_by',
    ]
    list_display = [
        'nimi',
        'hist_date',
        'hist_year',
        'hist_month',
        'seotud_artikleid',
        'seotud_pilte',
    ]
    search_fields = ['nimi']
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
            'fields': ['hist_enddate', 'hist_endyear']
            }
         ),
        ('Seotud', {
            'fields': ['objektid']
            }
         ),
        ('Viited', {
            'fields': [('viited')]
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
    ]
    filter_horizontal = [
        'viited'
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
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
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


class KroonikaAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date', 'mod_date', 'created_by', 'updated_by']
    fieldsets = [
        (None, {
            'fields': ['nimi', 'kirjeldus']}),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]}),
    ]
    

class PiltAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date', 'created_by', 'mod_date', 'updated_by',]
    list_display = [
        'nimi',
        'kasutatud',
        'profiilipilt',
        'pilt']
    search_fields = ['nimi']
    filter_horizontal = (
        'viited',
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
        ('Seotud', {
            'fields': [('allikad',
                        'artiklid',
                        'isikud',
                        'organisatsioonid',
                        'objektid')]
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
    filter_horizontal = [
        'viited'
    ]

    def link(self, obj):
        if obj.pilt:
            return obj.pilt.url
        else:
            return 'pilti pole'

    def profiilipilt(self, obj):
        from django.contrib.admin.templatetags.admin_list import _boolean_icon
        # Kas pilti kasutatakse profiilipildina?
        return _boolean_icon(
                obj.profiilipilt_allikas or
                obj.profiilipilt_artikkel or
                obj.profiilipilt_isik or
                obj.profiilipilt_organisatsioon or
                obj.profiilipilt_objekt
        )
        profiilipilt.boolean = True

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
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
        objekt.save()
        form.save_m2m()
        return objekt

    # def formfield_for_manytomany(self, db_field, request, **kwargs):
    #     if db_field.name == "artiklid":
    #         kwargs["queryset"] = Artikkel.objects.annotate('hist_year=1911)
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Allikas, AllikasAdmin)
admin.site.register(Viide, ViideAdmin)
admin.site.register(Kroonika, KroonikaAdmin)
admin.site.register(Artikkel, ArtikkelAdmin)
admin.site.register(Isik, IsikAdmin)
admin.site.register(Organisatsioon, OrganisatsioonAdmin)
admin.site.register(Objekt, ObjektAdmin)
admin.site.register(Pilt, PiltAdmin)
