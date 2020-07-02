from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, HTML, ButtonHolder
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import (
    ModelForm,
    Textarea,
    SelectMultiple,
    ValidationError,
    CharField,
    ModelMultipleChoiceField,
)

from .models import Artikkel, Isik, Organisatsioon, Objekt, Vihje, Pilt


class PiltForm(ModelForm):

    class Meta:
        model = Pilt
        exclude = ()


class ArtikkelForm(ModelForm):
    isikud = AutoCompleteSelectMultipleField('isikud')
    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid')
    objektid = AutoCompleteSelectMultipleField('objektid')
    viited = AutoCompleteSelectMultipleField('viited')

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
            'body_text': Textarea(attrs={'rows': 10}),
            # 'isikud': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud isikud'}),
            # 'isikud': FilteredSelectMultiple(
            #     'isikud',
            #     is_stacked=False,
            # ),
            # # 'organisatsioonid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud organisatsioonid'}),
            'organisatsioonid': FilteredSelectMultiple(
                'organisatsioonid',
                is_stacked=False,
            ),
            # 'objektid': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud objektid'}),
            'objektid': FilteredSelectMultiple(
                'objektid',
                is_stacked=False
            ),
            # 'viited': SelectMultiple(attrs={'size': 15, 'title': 'Vali seotud viited'}),
            # 'viited': FilteredSelectMultiple(
            #     'viited',
            #     is_stacked=False
            # ),
        }

    def clean(self):
        if not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
            raise ValidationError("Alguskuupäev või -aasta peab olema")
        return self.cleaned_data

class IsikForm(ModelForm):

    class Meta:
        model = Isik
        fields = ('eesnimi', 'perenimi',
                  'kirjeldus',
                  'hist_date', 'synd_koht', 'hist_year',
                  'hist_enddate', 'surm_koht', 'hist_endyear', 'gone', 'maetud',
                  'objektid',
                  'organisatsioonid',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            'organisatsioonid': FilteredSelectMultiple(
                'organisatsioonid',
                is_stacked=False,
            ),
            'objektid': FilteredSelectMultiple(
                'objektid',
                is_stacked=False
            ),
            'viited': FilteredSelectMultiple(
                'viited',
                is_stacked=False
            ),
        }

class OrganisatsioonForm(ModelForm):

    class Meta:
        model = Organisatsioon
        fields = ('nimi', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear', 'gone',
                  'objektid',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            'objektid': FilteredSelectMultiple(
                'objektid',
                is_stacked=False
            ),
            'viited': FilteredSelectMultiple(
                'viited',
                is_stacked=False
            ),
        }


class ObjektForm(ModelForm):

    objektid = AutoCompleteSelectMultipleField('objektid')
    viited = AutoCompleteSelectMultipleField('viited')

    class Meta:
        model = Objekt
        fields = ('nimi', 'tyyp', 'asukoht', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear', 'gone',
                  'objektid',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            # 'objektid': FilteredSelectMultiple(
            #     'objektid',
            #     is_stacked=False
            # ),
            # 'viited': FilteredSelectMultiple(
            #     'viited',
            #     is_stacked=False
            # ),
        }


class VihjeForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(VihjeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'feedbackForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = 'wiki:feedback'
        self.helper.layout = Layout(
            Fieldset(
                'Olen tänulik, kui märkasid viga või oskad täiendada:',
                'kirjeldus',
                'kontakt',
                HTML('<input type="hidden" value="" name="g-recaptcha-response" class="g-recaptcha-response" >')
            ),
            ButtonHolder(
                # HTML('<span class="hidden">✓ Saved data</span>'),
                Submit('save', 'Saada'),
                Submit('cancel', 'Loobu', onclick='showFeedback()', css_class='btn-default')
            )
        )

    class Meta:
        model = Vihje
        fields = (
            'kirjeldus',
            'kontakt'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
            'kontakt': Textarea(attrs={'cols': 40, 'rows': 1})
        }
