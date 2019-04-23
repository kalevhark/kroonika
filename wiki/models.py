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


class Allikas(models.Model):
    """
    Raamatu, ajakirja, ajalehe, andmebaasi või fondi andmed
    """
    nimi = models.CharField(
        'Allikas',
        max_length=100
    )
    hist_year = models.IntegerField(  # juhuks kui on teada ainult aasta
        'Ilmumisaasta',
        null=True,
        blank=True,
        help_text='Ilmumisaasta'
    )
    kirjeldus = models.TextField(
        'Kirjeldus',
        null=True,
        blank=True
    )
    url = models.URLField(
        'Internet',
        blank=True,
    ) # Allika internetiaadress

    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
        verbose_name='Muutja'
    )

    def __str__(self):
        ilmumis_aasta = ''
        if self.hist_year:
            ilmumis_aasta = f' ({self.hist_year})'
        return self.nimi + ilmumis_aasta

    def profiilipilt(self):
        return Pilt.objects.filter(allikad=self.id, profiilipilt_allikas=True).first()

    class Meta:
        verbose_name = "Allikas"
        verbose_name_plural = "Allikad"


class Viide(models.Model):
    """
    Viide artikli, isiku, organisatsiooni, objekti tekstis kasutatud allikatele
    """
    allikas = models.ForeignKey(
        Allikas,
        on_delete=models.SET_NULL,
        verbose_name='Allikas',
        help_text="Allikas",
        null=True,
        blank=True
    )
    # TODO: Wiki markup süsteem viitamiseks tekstis
    # Kasutame Wiki markup süsteemi:
    # <ref>Your Source</ref>
    # <ref>[http://www.nytimes.com/article_name.html Article in ''The New York Times'']</ref>
    # <ref>Name of author, [http://www.nytimes.com/article_name.html "Title of article"], ''The New York Times'', date</ref>
    marker = models.CharField( # Tekstis sisalduvad viite markerid
        'Marker',
        max_length=10,
        blank=True
    )
    hist_date = models.DateField(
        'Avaldatud',
        null=True,
        blank=True,
        help_text='Avaldatud'
    )
    hist_year = models.IntegerField( # juhuks kui on teada ainult aasta
        'Avaldatud',
        null=True,
        blank=True,
        help_text='Avaldamise aasta'
    )
    kohaviit = models.CharField( # fonditähis, aastakäigu/väljaande nr, lehekülje nr,
        'Viit',
        max_length=50,
        null=True,
        blank=True
    )
    url = models.URLField( # Allika internetiaadress
        'Internet',
        blank=True,
    )
    mod_date = models.DateTimeField( # Millal viidet kasutatud
        'Kasutatud',
        auto_now=True
    )

    class Meta:
        verbose_name_plural = "Viited"

    def __str__(self):
        viit = ''
        if self.kohaviit:
            viit = viit + ', ' + self.kohaviit
        if self.url:
            viit = viit + ', ' + self.kohaviit.split('/')[-1]
        return f'{self.allikas}{viit}'


class Objekt(models.Model):
    OBJEKTITYYP = (
        ('H', 'Hoone'),
        ('T', 'Tänav'),
        ('E', 'Ehitis'),
        ('A', 'Asula'),
        ('M', 'Muu'),
    )
    nimi = models.CharField(
        max_length=200
    )
    asukoht = models.CharField(
        max_length=200,
        blank=True,
        help_text='Asukoht'
    )
    hist_date = models.DateField(
        'Valminud',
        null=True,
        blank=True,
        help_text='Valminud'
    )
    hist_year = models.IntegerField( # juhuks kui on teada ainult aasta
        'Valmimisaasta',
        null=True,
        blank=True,
        help_text='Valmimisaasta'
    )
    hist_month = models.PositiveSmallIntegerField( # juhuks kui on teada aasta ja kuu
        'Valmimiskuu',
        null=True,
        blank=True,
        choices=KUUD,
        help_text='ja/või kuu'
    )
    hist_enddate = models.DateField(
        'Likvideeritud',
        null=True,
        blank=True,
        help_text='Likvideeritud'
    )
    hist_endyear = models.IntegerField( # juhuks kui on teada ainult aasta
        'Likvideerimise aasta',
        null=True,
        blank=True,
        help_text='Likvideerimise aasta'
    )
    tyyp = models.CharField(
        max_length=1,
        choices=OBJEKTITYYP
    )
    kirjeldus = models.TextField(
        blank=True
    )
    # Seotud:
    objektid = models.ManyToManyField(
        "self",
        blank=True,
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited',
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    hist_searchdate = models.DateField(
        'Tuletatud kuupäev',
        null=True,
        blank=True
    ) # Kuupäevaotsinguteks, kui täpset kuupäeva pole teada
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='+',
        verbose_name='Muutja'
    )

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
    nimi = models.CharField(
        max_length=200
    )
    hist_date = models.DateField(
        'Loodud',
        null=True,
        blank=True,
        help_text='Loodud'
    )
    hist_year = models.IntegerField( # juhuks kui on teada ainult aasta
        'Loomise aasta',
        null=True,
        blank=True,
        help_text='Loomise aasta'
    )
    hist_month = models.PositiveSmallIntegerField( # juhuks kui on teada aasta ja kuu
        'Loomise kuu',
        null=True,
        blank=True,
        choices=KUUD,
        help_text='ja/või kuu'
    )
    hist_enddate = models.DateField(
        'Lõpetatud',
        null=True,
        blank=True,
        help_text='Lõpetatud'
    )
    hist_endyear = models.IntegerField( # juhuks kui on teada ainult aasta
        'Lõpetamise aasta',
        null=True,
        blank=True,
        help_text='Lõpetamise aasta'
    )
    kirjeldus = models.TextField(
        blank=True
    )
    # Seotud:
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited',
    )

    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    hist_searchdate = models.DateField( # Kuupäevaotsinguteks, kui täpset kuupäeva pole teada
        'Tuletatud kuupäev',
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Muutja'
    )

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
    perenimi = models.CharField(
        max_length=100,
        help_text="Perekonnanimi"
    )
    eesnimi = models.CharField(
        max_length=100,
        blank=True,
        help_text="Eesnimi/nimed/initsiaal(id)"
    )
    # Eludaatumid
    hist_date = models.DateField(
        null=True,
        blank=True,
        help_text="Sündinud"
    )
    synd_koht = models.CharField(
        max_length=100,
        blank=True,
        help_text="Sünnikoht"
    )
    hist_enddate = models.DateField(
        null=True,
        blank=True,
        help_text="Surnud"
    )
    surm_koht = models.CharField(
        max_length=100,
        blank=True,
        help_text="Surmakoht"
    )
    maetud = models.CharField(
        max_length=200,
        blank=True,
        help_text="Maetud"
    )
    # Kirjeldus
    kirjeldus = models.TextField(
        blank=True
    )
    # Seotud
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
    )
    organisatsioonid = models.ManyToManyField(
        Organisatsioon,
        blank=True,
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited',
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Muutja'
    )

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
    """
    A. Duvini kroonikaraamatud
    """
    nimi = models.CharField(
        'Kroonika',
        max_length=100
    )
    autorid = models.ManyToManyField(
        Isik
    )
    kirjeldus = models.TextField()

    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
        verbose_name='Muutja'
    )

    def __str__(self):
        return self.nimi

    def profiilipilt(self):
        return Pilt.objects.filter(kroonikad=self.id, profiilipilt_kroonika=True).first()

    class Meta:
        verbose_name = "Kroonika"
        verbose_name_plural = "Kroonikad"


class Artikkel(models.Model):
    # Toimumisaeg
    hist_year = models.IntegerField(  # juhuks kui on teada ainult aasta
        'Aasta',
        null=True,
        blank=True,
        help_text="Aasta"
    )
    hist_month = models.PositiveSmallIntegerField(  # juhuks kui on teada aasta ja kuu
        'Kuu',
        null=True,
        blank=True,
        choices=KUUD,
        help_text="ja/või kuu"
    )
    hist_date = models.DateField( # Sündmus toimus või algas
        'Kuupäev',
        null=True,
        blank=True,
        help_text="Algas"
    )
    hist_enddate = models.DateField( # juhuks kui lõppaeg on teada
        'Lõppes',
        null=True,
        blank=True,
        help_text="Lõppes"
    )
    # Sisu
    body_text = models.TextField(
        'Artikkel',
        help_text='Artikli tekst'
    )
    # Seotud:
    isikud = models.ManyToManyField(
        Isik,
        blank=True,
        verbose_name='Seotud isikud'
    )
    organisatsioonid = models.ManyToManyField(
        Organisatsioon,
        blank=True,
        verbose_name='Seotud organisatsioonid'
    )
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
        verbose_name='Seotud objektid'
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited',
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    hist_searchdate = models.DateField( # Kuupäevaotsinguteks, kui täpset kuupäeva pole teada
        'Tuletatud kuupäev',
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Muutja'
    )
    # A. Duvini kroonikaraamatu viited:
    kroonika = models.ForeignKey(
        Kroonika,
        on_delete=models.SET_NULL,
        verbose_name='Kroonika',
        help_text="Kroonika",
        null=True,
        blank=True
    )
    lehekylg = models.IntegerField(
        'Lehekülg',
        null=True,
        blank=True,
        help_text="lehekülg"
    )

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
    nimi = models.CharField(
        'Pealkiri',
        max_length=100
    )
    autor = models.CharField(
        'Autor',
        max_length=100,
        null=True,
        blank=True
    )
    kirjeldus = models.TextField(
        'Kirjeldus',
        null=True,
        blank=True
    )
    pilt = models.ImageField(
        upload_to='pildid/%Y/%m/%d/',
        max_length=255,
        null=True,
        blank=True
    )
    hist_date = models.DateField(
        'Kuupäev',
        null=True,
        blank=True
    )
    hist_year = models.IntegerField(  # juhuks kui on teada ainult aasta
        'Aasta',
        null=True,
        blank=True,
        help_text="Aasta"
    )
    hist_month = models.PositiveSmallIntegerField(  # juhuks kui on teada aasta ja kuu
        'Kuu',
        null=True,
        blank=True,
        choices=KUUD,
        help_text="ja/või kuu"
    )
    allikad = models.ManyToManyField(
        Allikas,
        blank=True,
        verbose_name='Seotud allikad'
    )
    artiklid = models.ManyToManyField(
        Artikkel,
        blank=True,
        verbose_name='Seotud artiklid'
    )
    isikud = models.ManyToManyField(
        Isik,
        blank=True,
        verbose_name='Seotud isikud'
    )
    organisatsioonid = models.ManyToManyField(
        Organisatsioon,
        blank=True,
        verbose_name='Seotud organisatsioonid'
    )
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
        verbose_name='Seotud objektid'
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited'
    )
    # Kas näidatakse objekti (artikkel, isik, organisatsioon, objekt, kroonika) profiilipildina
    profiilipilt_allikas = models.BooleanField(
        'Allika profiilipilt',
        default=False
    )
    # profiilipilt_kroonika = models.BooleanField('Kroonika profiilipilt', default=False)
    profiilipilt_artikkel = models.BooleanField(
        'Artikli profiilipilt',
        default=False
    )
    profiilipilt_isik = models.BooleanField(
        'Isiku profiilipilt',
        default=False
    )
    profiilipilt_organisatsioon = models.BooleanField(
        'Organisatsiooni profiilipilt',
        default=False
    )
    profiilipilt_objekt = models.BooleanField(
        'Objekti profiilipilt',
        default=False
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Lisaja'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Muutja'
    )

    def __str__(self):
        return self.nimi

    def link(self):
        return self.pilt.url

    class Meta:
        verbose_name_plural = "Pildid"
