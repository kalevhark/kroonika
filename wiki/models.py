from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
import datetime

KUUD = (
        (1, 'jaanuar'),
        (2, 'veebruar'),
        (3, 'märts'),
        (4, 'aprill'),
        (5, 'mai'),
        (6, 'juuni'),
        (7, 'juuli'),
        (8, 'august'),
        (9, 'september'),
        (10, 'oktoober'),
        (11, 'november'),
        (12, 'detsember'),
        )

MITMIK_VALIK = "Mitme valimiseks hoia all <Ctrl> klahvi"


class Objekt(models.Model):
    OBJEKTITYYP = (
        ('H', 'Hoone'),
        ('T', 'Tänav'),
        ('E', 'Ehitis'),
        ('A', 'Asula'),
        ('M', 'Muu'),
    )
    nimi = models.CharField(max_length=200)
    asukoht = models.CharField(max_length=200, blank=True, help_text='Asukoht')
    hist_date = models.DateField('Valminud', null=True, blank=True, help_text='Valminud')
    hist_year = models.IntegerField('Valmimisaasta', null=True, blank=True, help_text='Valmimisaasta') # juhuks kui on teada ainult aasta
    hist_month = models.PositiveSmallIntegerField('Valmimiskuu', null=True, blank=True, choices=KUUD, help_text='ja/või kuu') # juhuks kui on teada aasta ja kuu
    hist_enddate = models.DateField('Likvideeritud', null=True, blank=True, help_text='Likvideeritud')
    hist_endyear = models.IntegerField('Likvideerimise aasta', null=True, blank=True, help_text='Likvideerimise aasta') # juhuks kui on teada ainult aasta
    objektid = models.ManyToManyField("self", blank=True, help_text=MITMIK_VALIK)
    tyyp = models.CharField(max_length=1, choices=OBJEKTITYYP)
    kirjeldus = models.TextField(blank=True)

    # Tehnilised väljad
    inp_date = models.DateTimeField('Lisatud', auto_now_add=True)
    mod_date = models.DateTimeField('Muudetud', auto_now=True)
    hist_searchdate = models.DateField('Tuletatud kuupäev', null=True, blank=True) # Kuupäevaotsinguteks, kui täpset kuupäeva pole teada
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Lisaja')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='+', verbose_name='Muutja')

    def __str__(self):
        return self.nimi

    def get_absolute_url(self):
        return reverse('wiki:wiki_objekt_detail', kwargs={'pk': self.pk})


    def vanus(self, d=datetime.date.today()):
        if self.hist_date:
            return d.year - self.hist_date.year
        else:
            if self.hist_year:
                return d.year - self.hist_year
        return None

    def profiilipilt(self):
        return Pilt.objects.filter(objektid=self.id, profiilipilt_objekt=True).first()

    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Objektid"


class Organisatsioon(models.Model):
    nimi = models.CharField(max_length=200)
    hist_date = models.DateField('Loodud', null=True, blank=True, help_text='Loodud')
    hist_year = models.IntegerField('Loomise aasta', null=True, blank=True, help_text='Loomise aasta') # juhuks kui on teada ainult aasta
    hist_month = models.PositiveSmallIntegerField('Loomise kuu', null=True, blank=True, choices=KUUD, help_text='ja/või kuu') # juhuks kui on teada aasta ja kuu
    hist_enddate = models.DateField('Lõpetatud', null=True, blank=True, help_text='Lõpetatud')
    hist_endyear = models.IntegerField('Lõpetamise aasta', null=True, blank=True, help_text='Lõpetamise aasta') # juhuks kui on teada ainult aasta
    kirjeldus = models.TextField(blank=True)
    objektid = models.ManyToManyField(Objekt, blank=True, help_text=MITMIK_VALIK)

    # Tehnilised väljad
    inp_date = models.DateTimeField('Lisatud', auto_now_add=True)
    mod_date = models.DateTimeField('Muudetud', auto_now=True)
    hist_searchdate = models.DateField('Tuletatud kuupäev', null=True, blank=True) # Kuupäevaotsinguteks, kui täpset kuupäeva pole teada
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lisaja')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='Muutja')

    def __str__(self):
        return self.nimi

    def get_absolute_url(self):
        return reverse('wiki:wiki_organisatsioon_detail', kwargs={'pk': self.pk})

    def vanus(self, d=datetime.date.today()):
        if self.hist_date:
            return d.year - self.hist_date.year
        else:
            if self.hist_year:
                return d.year - self.hist_year
        return None

    def profiilipilt(self):
        return Pilt.objects.filter(organisatsioonid=self.id, profiilipilt_organisatsioon=True).first()

    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Organisatsioonid"


class Isik(models.Model):
    perenimi = models.CharField(max_length=100, help_text="Perekonnanimi")
    eesnimi = models.CharField(max_length=100, blank=True, help_text="Eesnimi/nimed/initsiaal(id)")
    # Eludaatumid
    hist_date = models.DateField(null=True, blank=True, help_text="Sündinud")
    synd_koht = models.CharField(max_length=100, blank=True, help_text="Sünnikoht")
    hist_enddate = models.DateField(null=True, blank=True, help_text="Surnud")
    surm_koht = models.CharField(max_length=100, blank=True, help_text="Surmakoht")
    maetud = models.CharField(max_length=200, blank=True, help_text="Maetud")
    # Kirjeldus
    # pilt = models.ForeignKey(Pilt, on_delete=models.SET_NULL, null=True, blank=True)
    kirjeldus = models.TextField(blank=True)
    # Seotud
    objektid = models.ManyToManyField(Objekt, blank=True, help_text=MITMIK_VALIK)
    organisatsioonid = models.ManyToManyField(Organisatsioon, blank=True, help_text=MITMIK_VALIK)
##    wiki_link = URLField(blank=True, help_text="Link Wikipedia artiklile")
##    isik_link = URLField(blank=True, help_text="Link andmebaasile ISIK")
    # Tehnilised väljad
    inp_date = models.DateTimeField('Lisatud', auto_now_add=True)
    mod_date = models.DateTimeField('Muudetud', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lisaja')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='Muutja')

    def __str__(self):
        return ' '.join([self.eesnimi, self.perenimi])

    def get_absolute_url(self):
        return reverse('wiki:wiki_isik_detail', kwargs={'pk': self.pk})

    def vanus(self, d=datetime.date.today()):
        if self.hist_date:
            return d.year - self.hist_date.year
        else:
            return None

    def profiilipilt(self):
        return Pilt.objects.filter(isikud=self.id, profiilipilt_isik=True).first()

    class Meta:
        ordering = ['perenimi', 'eesnimi']
        verbose_name_plural = "Isikud"


class Kroonika(models.Model):
    nimi = models.CharField('Allikas', max_length=100)
    autorid = models.ManyToManyField(Isik)
    kirjeldus = models.TextField()

    # Tehnilised väljad
    inp_date = models.DateTimeField('Lisatud', auto_now_add=True)
    mod_date = models.DateTimeField('Muudetud', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Lisaja')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+', verbose_name='Muutja')

    def __str__(self):
        return self.nimi

    def profiilipilt(self):
        return Pilt.objects.filter(kroonikad=self.id, profiilipilt_kroonika=True).first()

    # Lisamise/muutmise andmete salvestamine
    def save_model(self, request, obj, form, change):
        obj.user = request.user
        if not obj.id:
            obj.created_by = obj.user
        else:
            obj.updated_by = obj.user
        obj.save()
        return obj


    class Meta:
        verbose_name = "Allikas"
        verbose_name_plural = "Allikad"


class Artikkel(models.Model):
    # Allikas
    kroonika = models.ForeignKey(
        Kroonika, on_delete=models.SET_NULL, verbose_name='Allikas', help_text="Allikas",
        null=True, blank=True)
    lehekylg = models.IntegerField('Lehekülg', null=True, blank=True, help_text="lehekülg")
    # Toimumisaeg
    hist_year = models.IntegerField('Aasta', null=True, blank=True, help_text="Aasta") # juhuks kui on teada ainult aasta
    hist_month = models.PositiveSmallIntegerField('Kuu', null=True, blank=True, choices=KUUD, help_text="ja/või kuu") # juhuks kui on teada aasta ja kuu
    hist_date = models.DateField('Kuupäev', null=True, blank=True, help_text="Algas")
    hist_enddate = models.DateField('Lõppes', null=True, blank=True, help_text="Lõppes") # juhuks kui kestvusaeg on teada
    # Sisu
    body_text = models.TextField('Artikkel', help_text='Artikli tekst')
    # Seotud:
    isikud = models.ManyToManyField(Isik, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud isikud')
    organisatsioonid = models.ManyToManyField(Organisatsioon, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud organisatsioonid')
    objektid = models.ManyToManyField(Objekt, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud objektid')
    # Tehnilised väljad
    inp_date = models.DateTimeField('Lisatud', auto_now_add=True)
    mod_date = models.DateTimeField('Muudetud', auto_now=True)
    hist_searchdate = models.DateField('Tuletatud kuupäev', null=True, blank=True) # Kuupäevaotsinguteks, kui täpset kuupäeva pole teada
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lisaja')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='Muutja')

    def __str__(self):
        tekst = self.body_text[:50]
        if len(self.body_text) > 50:
            tyhik = self.body_text.find(' ',50,70)
            if tyhik > 0:
                tekst = self.body_text[:tyhik] + '...'
        return tekst

    def __repr__(self):
        tekst = str(self.hist_year) + ':' + self.body_text
        return tekst

    def get_absolute_url(self):
        return reverse('wiki:wiki_artikkel_detail', kwargs={'pk': self.pk})

    def headline(self):
        if len(self.body_text) > 50:
            tyhik = self.body_text.find(' ',50,70)
            if tyhik > 0:
                return self.body_text[:tyhik] + '...'
        return self.body_text[:50]
    headline.short_description = 'Artikkel'

    def profiilipilt(self):
        return Pilt.objects.filter(artiklid=self.id, profiilipilt_artikkel=True).first()

    class Meta:
        verbose_name_plural = "Artiklid"


class Pilt(models.Model):
    nimi = models.CharField('Pealkiri', max_length=100)
    autor = models.CharField('Autor', max_length=100, null=True, blank=True)
    kirjeldus = models.TextField('Kirjeldus', null=True, blank=True)
    pilt = models.ImageField(upload_to='pildid/%Y/%m/%d/', max_length=255,
        null=True, blank=True)
    hist_date = models.DateField('Kuupäev', null=True, blank=True)
    hist_year = models.IntegerField(
        'Aasta', null=True, blank=True,
        help_text="Aasta")  # juhuks kui on teada ainult aasta
    hist_month = models.PositiveSmallIntegerField(
        'Kuu', null=True, blank=True, choices=KUUD,
        help_text="ja/või kuu")  # juhuks kui on teada aasta ja kuu
    # Seotud:
    kroonikad = models.ManyToManyField(Kroonika, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud allikad')
    artiklid = models.ManyToManyField(Artikkel, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud artiklid')
    isikud = models.ManyToManyField(Isik, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud isikud')
    organisatsioonid = models.ManyToManyField(
        Organisatsioon, blank=True, help_text=MITMIK_VALIK,
        verbose_name='Seotud organisatsioonid')
    objektid = models.ManyToManyField(Objekt, blank=True, help_text=MITMIK_VALIK, verbose_name='Seotud objektid')
    # Kas näidatakse objekti (artikkel, isik, organisatsioon, objekt, kroonika) profiilipildina
    profiilipilt_kroonika = models.BooleanField('Allika profiilipilt', default=False)
    profiilipilt_artikkel = models.BooleanField('Artikli profiilipilt', default=False)
    profiilipilt_isik = models.BooleanField('Isiku profiilipilt', default=False)
    profiilipilt_organisatsioon = models.BooleanField('Organisatsiooni profiilipilt', default=False)
    profiilipilt_objekt = models.BooleanField('Objekti profiilipilt', default=False)
    # Tehnilised väljad
    inp_date = models.DateTimeField('Lisatud', auto_now_add=True)
    mod_date = models.DateTimeField('Muudetud', auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Lisaja')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                                   verbose_name='Muutja')

    def __str__(self):
        return self.nimi

    def link(self):
        return self.pilt.url

    class Meta:
        verbose_name_plural = "Pildid"
