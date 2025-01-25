import re

from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField, AutoCompleteField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Fieldset, HTML, ButtonHolder

from django.apps import apps
from django.conf import settings
from django.forms import (
    Form, ModelForm,
    Textarea,
    # SelectMultiple,
    ValidationError,
    CharField,
    # ChoiceField, RadioSelect, Select
    # ModelMultipleChoiceField,
)

from .models import (
    Artikkel, Isik, Organisatsioon, Objekt,
    Vihje, Pilt,
    Kaart, Kaardiobjekt
)

VIGA_TEKSTIS = settings.KROONIKA['VIGA_TEKSTIS']
PATTERN_OBJECTS = settings.KROONIKA['PATTERN_OBJECTS']
PREDECESSOR_DESCENDANT_NAMES = settings.KROONIKA['PREDECESSOR_DESCENDANT_NAMES']

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


class BaasObjectForm(ModelForm):
    
    objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    viited = AutoCompleteSelectMultipleField('viited', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kirjeldus"].widget.attrs.update(cols="100")

    def clean(self, *args, **kwargs):
        string = self.cleaned_data.get('kirjeldus')

        # Kontrollime et kõik viitetagid oleks defineeritud
        pattern_viited = re.compile(r'\s?\[viide_([0-9]*)]')
        tagid = re.finditer(pattern_viited, string)
        for tag in tagid:
            id = tag.groups()[0]
            if id not in self.cleaned_data.get('viited'):
                raise ValidationError(f"Viide {tag[0]} pole defineeritud")
        
        # Kontrollime tekstisisesed markdown viited üle
        pattern = re.compile(PATTERN_OBJECTS)
        tagid = re.finditer(pattern, string)
        for tag in tagid:
            tekst, model_name, id = tag.groups()
            model = apps.get_model('wiki', model_name)
            try:
                _ = model.objects.get(id=id)
            except model.DoesNotExist:
                raise ValidationError(f"Viga: {model_name} id={id}")
        
        # # Kontrollime, et loo algusaeg on märgitud
        # if self.model == Artikkel and not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
        #     raise ValidationError("Alguskuupäev või -aasta peab olema")

        return self.cleaned_data
            

class ArtikkelForm(BaasObjectForm):

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["kirjeldus"].widget.attrs.update(cols="100")

    isikud = AutoCompleteSelectMultipleField('isikud', required=False)
    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False)
    # objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    # viited = AutoCompleteSelectMultipleField('viited', required=False)
    eellased = AutoCompleteSelectMultipleField('artiklid', required=False, help_text='')

    def clean(self, *args, **kwargs):
        # Kontrollime, et loo algusaeg on märgitud
        if not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
            raise ValidationError("Alguskuupäev või -aasta peab olema")
        super().clean(*args, **kwargs)
        return self.cleaned_data
    
    class Meta:
        model = Artikkel
        fields = ('kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate','hist_endyear', 'hist_endmonth',
                  'isikud',
                  'organisatsioonid',
                  'objektid',
                  'viited',
                  'kroonika', 'lehekylg', 'eellased',
        )

    # def clean(self):
    #     # Kontrollime et kõik viitetagid oleks defineeritud
    #     string = self.cleaned_data.get('kirjeldus')
    #     pattern = re.compile(r'\s?\[viide_([0-9]*)]')
    #     tagid = re.finditer(pattern, string)
    #     for tag in tagid:
    #         id = tag.groups()[0]
    #         if id not in self.cleaned_data.get('viited'):
    #             raise ValidationError(f"Viide {tag[0]} pole defineeritud")

    #     # Kontrollime, et loo algusaeg on märgitud
    #     if not any([self.cleaned_data.get('hist_date'), self.cleaned_data.get('hist_year')]):
    #         raise ValidationError("Alguskuupäev või -aasta peab olema")

    #     return self.cleaned_data


class IsikForm(BaasObjectForm):

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["kirjeldus"].widget.attrs.update(cols="100")

    # def clean(self):
    #     # Kontrollime et kõik viitetagid oleks defineeritud
    #     string = self.cleaned_data.get('kirjeldus')
    #     pattern = re.compile(r'\s?\[viide_([0-9]*)]')
    #     tagid = re.finditer(pattern, string)
    #     for tag in tagid:
    #         id = tag.groups()[0]
    #         if id not in self.cleaned_data.get('viited'):
    #             raise ValidationError(f"Viide {tag[0]} pole defineeritud")

    organisatsioonid = AutoCompleteSelectMultipleField('organisatsioonid', required=False, help_text='')
    # objektid = AutoCompleteSelectMultipleField('objektid', required=False, help_text='')
    # viited = AutoCompleteSelectMultipleField('viited', required=False, help_text='')
    eellased = AutoCompleteSelectMultipleField('isikud', required=False, help_text='')

    class Meta:
        model = Isik
        fields = ('eesnimi', 'perenimi',
                  'kirjeldus',
                  'hist_date', 'synd_koht', 'hist_year', 'hist_month',
                  'hist_enddate', 'surm_koht', 'hist_endyear', 'hist_endmonth', 'gone', 'maetud',
                  'objektid', 'organisatsioonid', 'eellased',
                  'viited'
        )


class OrganisatsioonForm(BaasObjectForm):

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["kirjeldus"].widget.attrs.update(cols="100")

    # def clean(self):
    #     # Kontrollime et kõik viitetagid oleks defineeritud
    #     string = self.cleaned_data.get('kirjeldus')
    #     pattern = re.compile(r'\s?\[viide_([0-9]*)]')
    #     tagid = re.finditer(pattern, string)
    #     for tag in tagid:
    #         id = tag.groups()[0]
    #         if id not in self.cleaned_data.get('viited'):
    #             raise ValidationError(f"Viide {tag[0]} pole defineeritud")

    # viited = AutoCompleteSelectMultipleField('viited', required=False)
    # objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    eellased = AutoCompleteSelectMultipleField('organisatsioonid', required=False)

    class Meta:
        model = Organisatsioon
        fields = ('nimi', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear', 'hist_endmonth', 'gone',
                  'objektid', 'eellased',
                  'viited'
        )


class ObjektForm(BaasObjectForm):

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["kirjeldus"].widget.attrs.update(cols="100")

    # def clean(self):
    #     # Kontrollime et kõik viitetagid oleks defineeritud
    #     string = self.cleaned_data.get('kirjeldus')
    #     pattern = re.compile(r'\s?\[viide_([0-9]*)]')
    #     tagid = re.finditer(pattern, string)
    #     for tag in tagid:
    #         id = tag.groups()[0]
    #         if id not in self.cleaned_data.get('viited'):
    #             raise ValidationError(f"Viide {tag[0]} pole defineeritud")

    # objektid = AutoCompleteSelectMultipleField('objektid', required=False)
    # viited = AutoCompleteSelectMultipleField('viited', required=False)
    eellased = AutoCompleteSelectMultipleField('objektid', required=False)

    class Meta:
        model = Objekt
        fields = ('nimi', 'tyyp', 'asukoht', 'kirjeldus',
                  'hist_date', 'hist_year', 'hist_month',
                  'hist_enddate', 'hist_endyear', 'hist_endmonth', 'gone',
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
                    '<input type="hidden" value="" name="g-recaptcha-response" class="g-recaptcha-response" />'
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

# from django_recaptcha.fields import ReCaptchaField
# from django_recaptcha.widgets import ReCaptchaV3

class ConfirmForm(Form):
    # recaptcha = ReCaptchaField(
    #     widget=ReCaptchaV3(
    #         action='wiki:confirm_with_recaptcha',
    #         attrs={
    #             'required_score':0.85
    #         }
    #     )
    # )
    edasi = CharField(label="Edasi", max_length=200, initial='tyhi', required=False)