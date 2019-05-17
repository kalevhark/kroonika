from .models import Artikkel, Isik, Organisatsioon, Objekt
from django.forms import ModelForm, Textarea, SelectMultiple
import datetime

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
    class Meta:
        model = Objekt
        fields = ('nimi', 'tyyp', 'asukoht', 'kirjeldus',
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

