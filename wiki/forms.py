import re

from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField, AutoCompleteField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Fieldset, HTML, ButtonHolder
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body_text"].widget.attrs.update(cols="100")

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

    def clean(self):
        # Kontrollime et kõik viitetagid oleks defineeritud
        string = self.cleaned_data.get('body_text')
        pattern = re.compile(r'\s?\[viide_([0-9]*)]')
        tagid = re.finditer(pattern, string)
        for tag in tagid:
            id = tag.groups()[0]
            if id not in self.cleaned_data.get('viited'):
                raise ValidationError(f"Viide {tag[0]} pole defineeritud")

        # Kontrollime, et loo algusaeg on märgitud
        if not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
            raise ValidationError("Alguskuupäev või -aasta peab olema")

        return self.cleaned_data


class IsikForm(ModelForm):
    # error_css_class = 'error'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.helper = FormHelper(self)
        self.fields["kirjeldus"].widget.attrs.update(cols="100")

    def clean(self):
        # Kontrollime et kõik viitetagid oleks defineeritud
        string = self.cleaned_data.get('kirjeldus')
        pattern = re.compile(r'\s?\[viide_([0-9]*)]')
        tagid = re.finditer(pattern, string)
        for tag in tagid:
            id = tag.groups()[0]
            if id not in self.cleaned_data.get('viited'):
                raise ValidationError(f"Viide {tag[0]} pole defineeritud")

    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False, help_text='')
    objektid = AutoCompleteSelectMultipleField('objektid', required=False, help_text='')
    viited = AutoCompleteSelectMultipleField('viited', required=False, help_text='')
    eellased = AutoCompleteSelectMultipleField('isikud', required=False, help_text='')

    class Meta:
        model = Isik
        fields = ('eesnimi', 'perenimi',
                  'kirjeldus',
                  'hist_date', 'synd_koht', 'hist_year',
                  'hist_enddate', 'surm_koht', 'hist_endyear', 'gone', 'maetud',
                  'objektid', 'organisatsioonid', 'eellased',
                  'viited'
        )
        # widgets = {
        #     'kirjeldus': Textarea(attrs={'cols': '100', 'rows': '10'}),
        # }


class OrganisatsioonForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kirjeldus"].widget.attrs.update(cols="100")

    def clean(self):
        # Kontrollime et kõik viitetagid oleks defineeritud
        string = self.cleaned_data.get('kirjeldus')
        pattern = re.compile(r'\s?\[viide_([0-9]*)]')
        tagid = re.finditer(pattern, string)
        for tag in tagid:
            id = tag.groups()[0]
            if id not in self.cleaned_data.get('viited'):
                raise ValidationError(f"Viide {tag[0]} pole defineeritud")

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


class ObjektForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kirjeldus"].widget.attrs.update(cols="100")

    def clean(self):
        # Kontrollime et kõik viitetagid oleks defineeritud
        string = self.cleaned_data.get('kirjeldus')
        pattern = re.compile(r'\s?\[viide_([0-9]*)]')
        tagid = re.finditer(pattern, string)
        for tag in tagid:
            id = tag.groups()[0]
            if id not in self.cleaned_data.get('viited'):
                raise ValidationError(f"Viide {tag[0]} pole defineeritud")

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


class KaartForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kirjeldus"].widget.attrs.update(cols="100")

    viited = AutoCompleteSelectMultipleField('viited', required=False)

    class Meta:
        model = Kaart
        fields = ('nimi', 'aasta', 'kirjeldus', 'tiles', 'viited')


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
        self.helper.form_show_labels = False
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                'Olen tänulik, kui märkasid viga või oskad täiendada:',
                Field(
                    'kirjeldus',
                    autocomplete='off',
                    css_class="vihje-kirjeldus w3-input w3-border w3-round"
                ),
                HTML(
                    '<p></p>' # kahe v2lja eraldamiseks vahe
                ),
                Field(
                    'kontakt',
                    css_class="vihje-kontakt w3-input w3-border w3-round"
                ),
                HTML(
                    '<input type="hidden" value="" name="g-recaptcha-response" class="g-recaptcha-response" >'
                ),
                ButtonHolder(
                    Submit('save', 'Saada', css_class='w3-button w3-round w3-left w3-green'),
                    Submit('cancel', 'Loobu', onclick='showFeedback()', css_class='w3-button w3-round w3-right w3-light-grey'),
                    css_class="w3-padding-16"
                ),
                css_class="w3-round"
            )
        )

    class Meta:
        model = Vihje
        fields = (
            'kirjeldus',
            'kontakt'
        )
        # widgets = {
        #     'kirjeldus': Textarea(attrs={
        #         'rows': 5,
        #         'placeholder': 'Siia palun kirjuta vihje parandamiseks/täiendamiseks'
        #     }),
        #     'kontakt': Textarea(attrs={'rows': 1, 'placeholder': 'Nimi ja kontaktandmed'})
        # }
        help_texts = {
            'kirjeldus': None,
            'kontakt': None,
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
