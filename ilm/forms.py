from datetime import datetime
import calendar

from django import forms

class NameForm(forms.Form):
    aasta = forms.IntegerField(label='Aasta')
    kuu = forms.IntegerField(label='Kuu', required=False)
    p2ev = forms.IntegerField(label='Päev',required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aasta'].widget.attrs.update(
            { 'class': 'w3-border-0',
             'placeholder': 'Aasta...',
             'min': 1900,
             'max': datetime.now().year
             }
        )
        self.fields['kuu'].widget.attrs.update(
            {'class': 'w3-border-0',
             'placeholder': 'Kuu...',
             'min': 0,
             'max': 12
             }
        )
        self.fields['p2ev'].widget.attrs.update(
            {'class': 'w3-border-0',
             'placeholder': 'Päev...',
             'maxlength': '2',
             'min': 0,
             'max': 31
             }
        )
        
    def clean(self):
        cleaned_data = super().clean()
        aasta = cleaned_data.get("aasta")
        p2ev = cleaned_data.get("p2ev")
        if p2ev:
            if (p2ev < 1) or (p2ev > 31):
                msg = "Päev peab olema vahemikus 1-31 või tühi"
                self.add_error('p2ev', msg)
        kuu = cleaned_data.get("kuu")
        if kuu:
            if kuu < 1 or kuu > 12:
                msg = "Kuu peab olema vahemikus 1-12 või tühi"
                self.add_error('kuu', msg)
            else:
                if aasta and kuu and p2ev:
                    c = calendar.Calendar()
                    if (aasta, kuu, p2ev) not in c.itermonthdays3(aasta, kuu):
                        raise forms.ValidationError(
                            "Sellist kuupäeva ei saa olla"
                        )
