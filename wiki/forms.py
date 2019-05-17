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
        
##    def save_model(self, request, obj, form, change): 
##        # Lisaja/muutja andmed
##        obj.user = request.user
##        blah
##        if not obj.id:
##            obj.created_by = obj.user
##        else:
##            obj.updated_by = obj.user
##        return obj
##        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
##        if obj.hist_date:
##            obj.hist_year = obj.hist_date.year
##            obj.hist_month = obj.hist_date.month
##            obj.hist_searchdate = obj.hist_date
##        else:
##            if obj.hist_year:
##                y = obj.hist_year
##                blah
##                if obj.hist_month:
##                    m = obj.hist_month
##                else:
##                    m = 1
##                obj.hist_searchdate = datetime.datetime(y, m, 1)
##        if obj.hist_enddate:
##            obj.hist_endyear = obj.hist_enddate.year
##        # Salvestame objekti
##        obj.save()
##        obj.save_m2m()
##        return obj


##class ObjektForm(ModelForm):
##    class Meta:
##        model = Objekt
##        fields = ('nimi', 'kirjeldus')
##        
##    def __init__(self, *args, **kwargs):
##        self.user = kwargs.pop('user', None)
##        super(ObjektForm, self).__init__(*args, **kwargs)

##    def form_valid(self, form):
##        objekt = form.save(commit=False)
##        # Lisaja/muutja andmed
##        if not objekt.id:
##            objekt.created_by = self.request.user
##        else:
##            objekt.updated_by = self.request.user
##        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
##        if objekt.hist_date:
##            objekt.hist_year = objekt.hist_date.year
##            objekt.hist_month = objekt.hist_date.month
##            objekt.hist_searchdate = objekt.hist_date
##        else:
##            if objekt.hist_year:
##                y = objekt.hist_year
##                if objekt.hist_month:
##                    m = objekt.hist_month
##                else:
##                    m = 1
##                objekt.hist_searchdate = datetime.datetime(y, m, 1)
##            else:
##                objekt.hist_searchdate = None
##        if objekt.hist_endyear:
##            objekt.hist_endyear = objekt.hist_enddate.year
##        objekt.save()
##        form.save_m2m()
##        return redirect('wiki:wiki_objekt_detail', pk=self.object.id)


##def save(self, *args, **kwargs):
##        # Lisaja/muutja andmete lisamine salvestamisel
##        if not self.id:
##            self.created_by = User.objects.first()
##        else:
##            self.updated_by = User.objects.first()
##        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
##        if self.hist_date:
##            self.hist_year = self.hist_date.year
##            self.hist_month = self.hist_date.month
##            self.hist_searchdate = self.hist_date
##        else:
##            if self.hist_year:
##                y = self.hist_year
##                if self.hist_month:
##                    m = self.hist_month
##                else:
##                    m = 1
##                self.hist_searchdate = datetime.datetime(y, m, 1)
##        if self.hist_enddate:
##            self.hist_endyear = self.hist_enddate.year
##            
##        super(Objekt, self).save(*args, **kwargs)
