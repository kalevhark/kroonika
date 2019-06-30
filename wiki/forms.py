from crispy_forms.helper import FormHelper
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import Form, ModelForm, Textarea, SelectMultiple, ValidationError, CharField, ModelMultipleChoiceField

from .models import Artikkel, Isik, Organisatsioon, Objekt, Vihje

class ArtikkelForm(ModelForm):
    class Meta:
        model = Artikkel
        fields = ('body_text',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate',
                  'isikud',
                  'organisatsioonid',
                  'objektid',
                  'viited',
                  'kroonika', 'lehekylg',
        )
        widgets = {
            'body_text': Textarea(attrs={'cols': 80, 'rows': 10}),
            'isikud': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud isikud'}),
            'organisatsioonid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud organisatsioonid'}),
            'objektid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud objektid'}),
            'viited': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud viited'}),
        }

    def clean(self):
        # start_date = self.cleaned_data.get('start_date')
        # end_date = self.cleaned_data.get('end_date')
        if not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
            raise ValidationError("Alguskuupäev või -aasta peab olema")
        return self.cleaned_data

class IsikForm(ModelForm):
    class Meta:
        model = Isik
        fields = ('eesnimi', 'perenimi',
                  'kirjeldus',
                  'hist_date', 'synd_koht', 'hist_year',
                  'hist_enddate', 'surm_koht', 'hist_endyear', 'maetud',
                  'objektid',
                  'organisatsioonid',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            'objektid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud objektid'}),
            'organisatsioonid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud organisatsioonid'}),
            'viited': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud viited'}),
        }

class OrganisatsioonForm(ModelForm):
    class Meta:
        model = Organisatsioon
        fields = ('nimi', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear',
                  'objektid',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            'objektid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud objektid'}),
            'viited': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud viited'}),
        }


class ObjektForm(ModelForm):

    # class Media:
    #     css = {'all': ('admin/css/widgets.css',), }
    #     js = ('/kroonika/admin/jsi18n/',)

    class Meta:
        model = Objekt
        fields = ('nimi', 'tyyp', 'asukoht', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear',
                  'objektid',
                  'viited'
        )
        # objektid = ModelMultipleChoiceField(
        #     Objekt.objects.all(),
        #     required=True,
        #     widget = FilteredSelectMultiple(
        #         "Seotud objektid",
        #         is_stacked=False,
        #         attrs={'rows': '10'}
        #     )
        # )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            'objektid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud objektid'}),
            'viited': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud viited'}),
        }

    # def __init__(self, parents=None, *args, **kwargs):
    #     super(ObjektForm, self).__init__(*args, **kwargs)

# class FeedBackForm(Form):
#     your_name = CharField(label='Sinu nimi', max_length=100)
#     your_feedback = CharField(label='Sinu sõnum', widget=Textarea(attrs={'cols': '30', 'rows': '5'}))

class VihjeForm(ModelForm):
    class Meta:
        model = Objekt
        fields = (
            'kirjeldus',
            'kontakt'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 80, 'rows': 5}),
            'kontakt': Textarea(attrs={'cols': 80, 'rows': 1})
        }
    # def __init__(self, *args, **kwargs):
    #     super(VihjeForm, self).__init__(*args, **kwargs)
    #     self.helper = FormHelper()

    # kirjeldus = CharField(
    #     label='Vihje parandamiseks/täiendamiseks',
    #     widget=Textarea(attrs={'cols': '80', 'rows': '5'})
    # )
    # kontakt = CharField(
    #     label='Sinu nimi/kontaktandmed',
    #     widget=Textarea(attrs={'cols': '80', 'rows': '1'}),
    #     max_length=80,
    #     required=False
    # )
