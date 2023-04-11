from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField, AutoCompleteField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, HTML, ButtonHolder
from django.forms import (
    Form, ModelForm,
    Textarea,
    # SelectMultiple,
    ValidationError,
    # CharField,
    ChoiceField, RadioSelect, Select
    # ModelMultipleChoiceField,
)

from .models import (
    Artikkel, Isik, Organisatsioon, Objekt,
    Vihje, Pilt,
    Kaart, Kaardiobjekt
)


class PiltForm(ModelForm):
    viited = AutoCompleteSelectMultipleField('viited', required=False)

    isikud = AutoCompleteSelectMultipleField('isikud', required=False)
    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False)
    objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    artiklid = AutoCompleteSelectMultipleField('artiklid', required=False)
    allikad = AutoCompleteSelectMultipleField('allikad', required=False)

    profiilipilt_isikud = AutoCompleteSelectMultipleField('isikud', required=False)
    profiilipilt_organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False)
    profiilipilt_objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    profiilipilt_artiklid = AutoCompleteSelectMultipleField('artiklid', required=False)
    profiilipilt_allikad = AutoCompleteSelectMultipleField('allikad', required=False)

    class Meta:
        model = Pilt
        exclude = ()


class ArtikkelForm(ModelForm):

    isikud = AutoCompleteSelectMultipleField('isikud', required=False)
    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False)
    objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    viited = AutoCompleteSelectMultipleField('viited', required=False)

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
        }

    def clean(self):
        if not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
            raise ValidationError("Alguskuupäev või -aasta peab olema")
        return self.cleaned_data


class IsikForm(ModelForm):
    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False)
    objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    viited = AutoCompleteSelectMultipleField('viited', required=False)
    eellased = AutoCompleteSelectMultipleField('isikud', required=False)

    class Meta:
        model = Isik
        fields = ('eesnimi', 'perenimi',
                  'kirjeldus',
                  'hist_date', 'synd_koht', 'hist_year',
                  'hist_enddate', 'surm_koht', 'hist_endyear', 'gone', 'maetud',
                  'objektid', 'organisatsioonid', 'eellased',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 100, 'rows': 5}),
        }

class OrganisatsioonForm(ModelForm):
    viited = AutoCompleteSelectMultipleField('viited', required=False)
    objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    eellased = AutoCompleteSelectMultipleField('organisatsioonid', required=False)

    class Meta:
        model = Organisatsioon
        fields = ('nimi', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear', 'gone',
                  'objektid', 'eellased',
                  'viited'
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
        }


class ObjektForm(ModelForm):

    objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    viited = AutoCompleteSelectMultipleField('viited', required=False)
    eellased = AutoCompleteSelectMultipleField('objektid', required=False)

    class Meta:
        model = Objekt
        fields = ('nimi', 'tyyp', 'asukoht', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear', 'gone',
                  'objektid', 'eellased',
                  'viited',
        )
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
        }

class KaartForm(ModelForm):

    viited = AutoCompleteSelectMultipleField('viited', required=False)

    class Meta:
        model = Kaart
        fields = ('nimi', 'aasta', 'kirjeldus', 'tiles', 'viited')
        widgets = {
            'kirjeldus': Textarea(attrs={'cols': 40, 'rows': 5}),
        }


class KaardiobjektForm(ModelForm):

    objekt = AutoCompleteSelectField('objektid', required=False)

    class Meta:
        model = Kaardiobjekt
        fields = (
            'kaart',
            'objekt',
            'tyyp', 'objekt', 'geometry', 'zoom', 'tn', 'nr', 'lisainfo'
        )


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


class V6rdleFormIsik(Form):
    vasak_object = AutoCompleteSelectField(
        'isikud',
        required=False,
        help_text=''
    )
    parem_object = AutoCompleteSelectField(
        'isikud',
        required=False,
        help_text=''
    )


class V6rdleFormObjekt(Form):
    vasak_object = AutoCompleteSelectField(
        'objektid',
        required=False,
        help_text=''
    )
    parem_object = AutoCompleteSelectField(
        'objektid',
        required=False,
        help_text=''
    )

