import json

from ajax_select import make_ajax_form
from ajax_select.admin import AjaxSelectAdmin, AjaxSelectAdminTabularInline
from ajax_select.fields import AutoCompleteSelectWidget
from ajax_select.registry import registry

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import site as admin_site
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.admin.views.main import IS_POPUP_VAR, TO_FIELD_VAR
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.forms.utils import flatatt
from django.template.defaultfilters import force_escape
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

# from django.db.models import Case, F, When, IntegerField
# from django.db.models.functions import ExtractDay
# from markdownx.admin import MarkdownxModelAdmin

from .models import (
    Allikas, Viide, Kroonika,
    Artikkel, Isik, Organisatsioon, Objekt,
    Pilt, Vihje,
    Kaart, Kaardiobjekt
)
from .forms import (
    ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm,
    PiltForm,
    KaartForm, KaardiobjektForm
)

# EI OLE KASUTUSEL
class MyRelatedFieldWidgetWrapper(RelatedFieldWidgetWrapper):
    """
    This class is a wrapper to a given widget to add the add icon for the
    admin interface.
    """

    def __init__(self, *args, **kwargs):
        self.parent_object = kwargs.get('parent_object')
        try:
            del kwargs['parent_object']  # superclass will choke on this
        except:
            pass
        super(MyRelatedFieldWidgetWrapper, self).__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        rel_opts = self.rel.model._meta
        info = (rel_opts.app_label, rel_opts.model_name)
        # self.widget.choices = self.choices
        related_field_name = self.rel.get_related_field().name
        url_params = "&".join(
            "%s=%s" % param
            for param in [
                (TO_FIELD_VAR, related_field_name),
                (IS_POPUP_VAR, 1),
                (self.parent_object.__class__.__name__.lower(), self.parent_object.id) # lisame viite parent objectile
            ]
        )
        context = {
            "rendered_widget": self.widget.render(name, value, attrs),
            "is_hidden": self.is_hidden,
            "name": name,
            "url_params": url_params,
            "model": rel_opts.verbose_name,
            "can_add_related": self.can_add_related,
            "can_change_related": self.can_change_related,
            "can_delete_related": self.can_delete_related,
            "can_view_related": self.can_view_related,
            "model_has_limit_choices_to": self.rel.limit_choices_to,
        }
        if self.can_add_related:
            context["add_related_url"] = self.get_related_url(info, "add")
        if self.can_delete_related:
            context["delete_related_template_url"] = self.get_related_url(
                info, "delete", "__fk__"
            )
        if self.can_view_related or self.can_change_related:
            context["view_related_url_params"] = f"{TO_FIELD_VAR}={related_field_name}"
            context["change_related_template_url"] = self.get_related_url(
                info, "change", "__fk__"
            )
        return context

#
# Vajalikud MyAutoCompleteSelectWidget jaoks
#
json_encoder = import_string(
    getattr(
        settings,
        'AJAX_SELECT_JSON_ENCODER',
        'django.core.serializers.json.DjangoJSONEncoder'
    )
)

def make_plugin_options(lookup, channel_name, widget_plugin_options, initial):
    """ Make a JSON dumped dict of all options for the jQuery ui plugin."""
    po = {}
    if initial:
        po['initial'] = initial
    po.update(getattr(lookup, 'plugin_options', {}))
    po.update(widget_plugin_options)
    if not po.get('source'):
        po['source'] = reverse('ajax_lookup', kwargs={'channel': channel_name})

    # allow html unless explicitly set
    if po.get('html') is None:
        po['html'] = True

    return {
        'plugin_options': mark_safe(json.dumps(po, cls=json_encoder)),
        'data_plugin_options': force_escape(
                json.dumps(po, cls=json_encoder)
        )
    }

# Kohandatud, et lisada parent object
class MyAutoCompleteSelectWidget(AutoCompleteSelectWidget):
    """
    Widget to search for a model and return it as text for use in a CharField.
    """
    def __init__(self, channel, help_text='', show_help_text=True, plugin_options=None, *args, **kwargs):
        self.parent_object = kwargs.get('parent_object')
        try:
            del kwargs['parent_object']  # superclass will choke on this
        except:
            pass
        super(MyAutoCompleteSelectWidget, self).__init__(
            channel, *args, **kwargs
        )

    def render(self, name, value, attrs=None, renderer=None, **_kwargs):
        value = value or ''

        final_attrs = self.build_attrs(self.attrs)
        final_attrs.update(attrs or {})
        final_attrs.pop('required', None)
        self.html_id = final_attrs.pop('id', name)

        current_repr = ''
        initial = None
        lookup = registry.get(self.channel)
        if value:
            objs = lookup.get_objects([value])
            try:
                obj = objs[0]
            except IndexError:
                raise Exception(f"{lookup} cannot find object:{value}")
            current_repr = lookup.format_item_display(obj)
            initial = [current_repr, obj.pk]

        if self.show_help_text:
            help_text = self.help_text
        else:
            help_text = ''

        context = {
            'name': name,
            'html_id': self.html_id,
            'current_id': value,
            'current_repr': current_repr,
            'help_text': help_text,
            'extra_attrs': mark_safe(flatatt(final_attrs)),
            'func_slug': self.html_id.replace("-", ""),
            'add_link': self.add_link,
            'parent_object': self.parent_object # lisatud parent object
        }
        context.update(
                make_plugin_options(lookup, self.channel, self.plugin_options, initial))
        templates = (
            f'ajax_select/autocompleteselect_{self.channel}.html',
            'ajax_select/autocompleteselect.html')
        out = render_to_string(templates, context)
        return mark_safe(out)


#
# Piltide lisamiseks artiklite halduris
#
# EI OLE KASUTUSEL
class PiltArtikkelInline(admin.TabularInline):
    model = Pilt.artiklid.through
    extra = 1
    template = 'admin/edit_inline/tabular_pilt.html'

    def __init__(self, *args, **kwargs):
        self.parent_object = kwargs.get('obj')
        try:
            del kwargs['obj']  # superclass will choke on this
        except:
            pass
        super(PiltArtikkelInline, self).__init__(*args, **kwargs)

    # lisame pildi lisamisel artikli viited, isikud, organisatsioonid, objektid
    def get_formset(self, request, obj=None, **kwargs):
        formset = super(PiltArtikkelInline, self).get_formset(request, obj, **kwargs)
        if obj:
            form = formset.form
            form.base_fields['pilt'].widget = MyRelatedFieldWidgetWrapper(
                form.base_fields['pilt'].widget,
                self.model._meta.get_field('pilt').remote_field,
                admin_site,
                parent_object=obj
            )
        return formset


#
# Piltide lisamiseks artiklite halduris ver 2
#
class PiltArtikkelInline2(AjaxSelectAdminTabularInline):
    model = Pilt.artiklid.through
    extra = 1
    template = 'admin/edit_inline/tabular_pilt.html'
    form = make_ajax_form(Pilt.artiklid.through, {
        'artikkel': 'artiklid',
        'pilt': 'pildid'
    })

    def __init__(self, *args, **kwargs):
        self.parent_object = kwargs.get('obj')
        try:
            del kwargs['obj']  # superclass will choke on this
        except:
            pass
        super(PiltArtikkelInline2, self).__init__(*args, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        from ajax_select.fields import autoselect_fields_check_can_add
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            form = formset.form
            form.base_fields['pilt'].widget = MyAutoCompleteSelectWidget(
                'pildid',
                help_text = '',
                show_help_text = True,
                plugin_options = None,
                parent_object = obj
            )
        autoselect_fields_check_can_add(formset.form, self.model, request.user)
        return formset
#
# Piltide lisamiseks isikute halduris
#
class PiltIsikInline(AjaxSelectAdminTabularInline):
    model = Pilt.isikud.through
    extra = 1
    template = 'admin/edit_inline/tabular_pilt.html'
    form = make_ajax_form(Pilt.isikud.through, {
        'isik': 'isikud',
        'pilt': 'pildid'
    })


#
# Piltide lisamiseks organisatsioonide halduris
#
class PiltOrganisatsioonInline(AjaxSelectAdminTabularInline):
    model = Pilt.organisatsioonid.through
    extra = 1
    template = 'admin/edit_inline/tabular_pilt.html'
    form = make_ajax_form(Pilt.organisatsioonid.through, {
        'organisatsioon': 'organisatsioonid',
        'pilt': 'pildid'
    })


#
# Piltide lisamiseks objektide halduris
class PiltObjektInline(AjaxSelectAdminTabularInline):
    model = Pilt.objektid.through
    extra = 1
    template = 'admin/edit_inline/tabular_pilt.html'
    form = make_ajax_form(Pilt.objektid.through, {
        'objekt': 'objektid',
        'pilt': 'pildid'
    })


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


class ArtikkelAdmin(AjaxSelectAdmin):

    form = ArtikkelForm
    readonly_fields = [
        'hist_searchdate',
        'inp_date', 'created_by',
        'mod_date', 'updated_by',
        'last_accessed', 'total_accessed'
    ]
    list_display = (
        # 'id',
        'colored_id', # punane, kui läbi vaatamata
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
    fieldsets = [
        (None, {
            'fields': [('body_text')]
            }
         ),
        ('Toimus', {
            'fields': [('hist_date', 'hist_year', 'hist_month', 'hist_enddate')]
            }
         ),
        ('Seotud', {
            'fields': [('viited'), ('isikud', 'organisatsioonid', 'objektid')]
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
        PiltArtikkelInline2,
    ]

    def get_queryset(self, request):
        return Artikkel.objects.daatumitega(request)

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
        # return obj.pilt_set.count()
        return obj.pildid.count()
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

    
class IsikAdmin(AjaxSelectAdmin):
    form = IsikForm
    list_display = (
        # 'id',
        'colored_id',
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
        # ('Viited', {
        #     'fields': [('viited')]
        # }
        #  ),
        ('Seotud', {
            'fields': [
                ('viited'),
                ('organisatsioonid', 'objektid', 'eellased')
            ]
            }
         ),

        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]
    filter_horizontal = [
        # 'viited',
        # 'organisatsioonid',
        # 'objektid',
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
        # return obj.pilt_set.count()
        return obj.pildid.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on objektiga seotud viiteid
    def seotud_viiteid(self, obj):
        return obj.viited.count()
    seotud_viiteid.short_description = 'Viiteid'


class OrganisatsioonAdmin(AjaxSelectAdmin):
    form = OrganisatsioonForm
    readonly_fields = [
        'inp_date',
        'mod_date',
        'created_by',
        'updated_by'
    ]
    list_display = [
        # 'id',
        'colored_id',
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
        # ('Viited', {
        #     'fields': [('viited')]
        # }
        #  ),
        ('Seotud', {
            'fields': [
                ('viited'),
                ('objektid', 'eellased')
            ]
        }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
        }
         ),
    ]
    filter_horizontal = [
        # 'viited',
        # 'objektid',
    ]
    inlines = [
        PiltOrganisatsioonInline,
    ]
    search_fields = ['id', 'nimi']

    # Kui palju on organisatsiooniga seotud artikleid
    def seotud_artikleid(self, obj):
        return obj.artikkel_set.count()
    seotud_artikleid.short_description = 'Artikleid'

    # Kui palju on organisatsiooniga seotud pilte
    def seotud_pilte(self, obj):
        # return obj.pilt_set.count()
        return obj.pildid.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on organisatsiooniga seotud viiteid
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
        objekt.save()
        form.save_m2m()
        return objekt


# class ObjektAdmin(MarkdownxModelAdmin):
class ObjektAdmin(AjaxSelectAdmin):

    form = ObjektForm
    readonly_fields = [
        # 'hist_searchdate',
        'inp_date', 'created_by',
        'mod_date', 'updated_by',
    ]
    list_display = [
        # 'id',
        'colored_id',
        'seotud_kaardiga',
        # 'nimi',
        # 'asukoht',
        '__str__',
        'hist_date',
        'hist_year',
        'hist_month',
        'seotud_artikleid',
        'seotud_pilte',
        'seotud_viiteid',
    ]
    search_fields = ['id', 'nimi', 'asukoht']
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
            'fields': ['objektid', 'eellased']
            }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]
    filter_horizontal = [
        # 'viited',
        # 'objektid',
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
        # return obj.pilt_set.count()
        return obj.pildid.count()
    seotud_pilte.short_description = 'Pilte'

    # Kui palju on objektiga seotud viiteid
    def seotud_viiteid(self, obj):
        return obj.viited.count()
    seotud_viiteid.short_description = 'Viiteid'

    def seotud_kaardiga(self, obj):
        return _boolean_icon(
            obj.kaardiobjekt_set.count() > 0
        )
    seotud_kaardiga.short_description = 'Kaardiga'


class KroonikaAdmin(admin.ModelAdmin):
    readonly_fields = ['inp_date', 'mod_date', 'created_by', 'updated_by']
    fieldsets = [
        (None, {
            'fields': ['nimi', 'kirjeldus']}),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]}),
    ]
    

# class PiltAdmin(admin.ModelAdmin):
class PiltAdmin(AjaxSelectAdmin):

    readonly_fields = [
        'pilt_height_field',
        'pilt_width_field',
        'inp_date', 'created_by', 'mod_date', 'updated_by',
    ]
    list_display = [
        # 'id',
        'colored_id',
        'nimi',
        'kasutatud',
        'profiilipilt',
        'pilt',
        'pildi_suurus'
    ]
    list_filter = ['tyyp']
    search_fields = ['id', 'nimi']
    filter_horizontal = (
        # 'viited',
        # 'allikad',
        # 'artiklid',
        # 'isikud',
        # 'organisatsioonid',
        # 'objektid'
    )
    form = PiltForm
    fieldsets = [
        (None, {
            'fields': ['tyyp', 'pilt', 'nimi', 'autor', 'kirjeldus']
            }
         ),
        (None, {
            'fields': ['hist_date', 'hist_year', 'hist_month']
            }
         ),
        # ('Viited', {
        #     'fields': [('viited')]
        # }
        #  ),
        ('Seotud', {
            'fields': [
                ('viited'),
                (
                'isikud',
                'organisatsioonid',
                'objektid',
                'allikad',
                'artiklid',
                 )
            ]
        }),
        ('Profiilipildid', {
            'fields': [
                (
                    'profiilipilt_artiklid',
                    'profiilipilt_isikud',
                    'profiilipilt_organisatsioonid',
                    'profiilipilt_objektid',
                    'profiilipilt_allikad',
                )
            ]
        }
         ),
        (None, {
            'fields': [('created_by', 'inp_date', 'updated_by', 'mod_date')]
            }
         ),
    ]

    # Kui alusobjektiks on Artikkel object, siis lisatakse sealt viited, isikud, organisatsioonid, objektid
    # Artikkel tuleb enne salvestada koos seostega!
    def get_changeform_initial_data(self, request):
        parent_object_id = request.GET.get('artikkel', None)
        if parent_object_id:
            artikkel = Artikkel.objects.daatumitega(request).get(id=int(parent_object_id))
            viited = artikkel.viited.all() # values_list('id', flat=True)
            isikud = artikkel.isikud.values_list('id', flat=True)
            organisatsioonid = artikkel.organisatsioonid.values_list('id', flat=True)
            objektid = artikkel.objektid.values_list('id', flat=True)
        else:
            viited = []
            isikud = []
            organisatsioonid = []
            objektid = []

        return {
            'viited': viited,
            'isikud': isikud,
            'organisatsioonid': organisatsioonid,
            'objektid': objektid
        }

    def link(self, obj):
        if obj.pilt:
            return obj.pilt.url
        else:
            return 'pilti pole'

    def profiilipilt(self, obj):
        # Kas pilti kasutatakse profiilipildina?
        return _boolean_icon(
            obj.profiilipilt_allikad.exists() or
            obj.profiilipilt_artiklid.exists() or
            obj.profiilipilt_isikud.exists() or
            obj.profiilipilt_organisatsioonid.exists() or
            obj.profiilipilt_objektid.exists()
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
        object = form.save(commit=False)
        # Lisaja/muutja andmed
        if not object.id:
            object.created_by = request.user
        else:
            object.updated_by = request.user
        # # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        # if object.hist_date:
        #     object.hist_year = object.hist_date.year
        #     object.hist_month = object.hist_date.month
        object.save()
        form.save_m2m()
        return object


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
    list_filter = [
        'end_date'
    ]
    list_display = [
        'id',
        'done',
        'inp_date',
        'lyhi_kirjeldus',
        'http_referer',
        'kontakt',
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

# Funktsiooni erinevate admin vaadete tegemiseks samale modelile
def create_modeladmin(modeladmin, model, name = None):
    class Meta:
        proxy = True
        app_label = model._meta.app_label
        verbose_name = model._meta.verbose_name + " kiirparandusteks"
        verbose_name_plural = model._meta.verbose_name_plural + " kiirparandusteks"

    attrs = {'__module__': '', 'Meta': Meta}
    newmodel = type(name, (model,), attrs)
    admin.site.register(newmodel, modeladmin)
    return modeladmin


class IsikPiltidetaAdmin(IsikAdmin):
    inlines = []

create_modeladmin(IsikPiltidetaAdmin, name='isikud-kiirparandusteks', model=Isik)


class OrganisatsioonPiltidetaAdmin(OrganisatsioonAdmin):
    inlines = []

create_modeladmin(OrganisatsioonPiltidetaAdmin, name='asutised-kiirparandusteks', model=Organisatsioon)

class ObjektPiltidetaAdmin(ObjektAdmin):
    inlines = []

create_modeladmin(ObjektPiltidetaAdmin, name='kohad-kiirparandusteks', model=Objekt)


class KaartAdmin(AjaxSelectAdmin):

    form = KaartForm

    list_display = (
        'id',
        '__str__',
    )

admin.site.register(Kaart, KaartAdmin)


class KaardiobjektAdmin(AjaxSelectAdmin):

    form=KaardiobjektForm

    list_display = (
        'colored_id',
        'tyyp',
        '__str__',
    )
    list_filter = ['kaart', 'tn']
    search_fields = [
        'tn',
        'nr',
        'lisainfo',
        'id'
    ]

admin.site.register(Kaardiobjekt, KaardiobjektAdmin)

from django.contrib import admin
from ajax_select import make_ajax_form
# from yourapp.models import YourModel

@admin.register(Pilt.artiklid.through)
class YourModelAdmin(AjaxSelectAdmin):

    form = make_ajax_form(Pilt.artiklid.through, {
        'artikkel': 'artiklid',  # ManyToManyField
        'pilt':'pildid'      # ForeignKeyField
    })