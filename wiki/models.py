import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone

from django.core.files.base import ContentFile
import os
import os.path
from PIL import Image
from io import BytesIO

def make_thumbnail(dst_image_field, src_image_field, name_suffix, sep='_'):
    """
    make thumbnail image and field from source image field

    @example
        thumbnail(self.thumbnail, self.image, (200, 200), 'thumb')
    """
    # create thumbnail image
    media_dir = settings.MEDIA_ROOT
    with Image.open(media_dir + src_image_field.name) as img:
        if name_suffix == 'thumb':
            dest_size = (img.size[0], 128)
        else:
            dest_size = (img.size[0], 64)

        img.thumbnail(dest_size) #, Image.ANTIALIAS)

        # build file name for dst
        dst_path, dst_ext = os.path.splitext(src_image_field.name)
        dst_ext = dst_ext.lower()
        dst_fname = dst_path + sep + name_suffix + dst_ext

        # check extension
        if dst_ext in ['.jpg', '.jpeg']:
            filetype = 'JPEG'
        elif dst_ext == '.gif':
            filetype = 'GIF'
        elif dst_ext == '.png':
            filetype = 'PNG'
        else:
            raise RuntimeError('unrecognized file type of "%s"' % dst_ext)

        # Save thumbnail to in-memory file as StringIO
        dst_bytes = BytesIO()
        img.save(dst_bytes, filetype)
        dst_bytes.seek(0)

        # set save=False, otherwise it will run in an infinite loop
        dst_image_field.save(dst_fname, ContentFile(dst_bytes.read()), save=False)
        dst_bytes.close()

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

VIGA_TEKSTIS = '(?)'

class Allikas(models.Model):
    """
    Raamatu, ajakirja, ajalehe, andmebaasi või fondi andmed
    """
    nimi = models.CharField(
        'Allikas',
        max_length=100
    )
    autorid = models.ManyToManyField(
        'Isik',
        blank=True,
        verbose_name='Autorid'
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

    def __repr__(self):
        return self.nimi

    def profiilipilt(self):
        return Pilt.objects.filter(allikad=self.id, profiilipilt_allikas=True).first()

    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Allikad"


class Viide(models.Model):
    """
    Viide artikli, isiku, organisatsiooni, objekti tekstis kasutatud allikatele
    """
    allikas = models.ForeignKey(
        Allikas,
        on_delete=models.SET_NULL,
        verbose_name='Allikas',
        help_text='Allikas',
        null=True,
        blank=True
    )
    peatykk = models.CharField(
        'Peatükk',
        max_length=200,
        blank=True,
        help_text='Artikli või peatüki pealkiri'
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
        # Viite autorid
        autorid = ''
        if self.allikas.autorid:
            for obj in self.allikas.autorid.all():
                autorid = ', '.join([obj.lyhinimi])
        # Viite kohaviida andmed
        peatykk = ''
        if self.peatykk:
            peatykk = str(self.peatykk)
        allika_nimi = ''
        if self.allikas.nimi:
            allika_nimi = str(self.allikas.nimi)
        viit = ''
        if self.kohaviit: # kui on füüsiline asukoht
            viit = viit + ', ' + self.kohaviit
        else: # kui on ainult internetilink
            if self.url:
                viit = viit + ', ' + self.url.split('/')[-1]
        # Ilmumise aeg
        aeg = self.mod_date.strftime('%d.%m.%Y') # kasutame algselt viite kasutamise kuupäeva
        if self.hist_date: # kui olemas, võtame ilmumise kuupäeva
            aeg = self.hist_date.strftime('%d.%m.%Y')
        else: # kui kuupäeva pole, siis ilmumisaasta
            if self.hist_year:
                aeg = str(self.hist_year)
            else: # kui viite ilmumisaastat pole, siis allika ilmumisaasta
                if self.allikas.hist_year:
                    aeg = str(self.allikas.hist_year)
        return ' '.join([autorid, peatykk, allika_nimi, viit, aeg])


class Objekt(models.Model):
    OBJEKTITYYP = (
        ('H', 'Hoone'),
        ('T', 'Tänav'),
        ('E', 'Ehitis'),
        ('A', 'Asula'),
        ('M', 'Muu'),
    )
    nimi = models.CharField(
        'Kohanimi',
        max_length=200,
        help_text='Kohanimi/nimed'
    )
    asukoht = models.CharField(
        'Asukoht',
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
    gone = models.BooleanField(  # surnud teadmata ajal
        'Hävinud/likvideeritud',
        default=False,
        help_text='Hävinud/likvideeritud'
    )
    tyyp = models.CharField(
        max_length=1,
        choices=OBJEKTITYYP,
        help_text='Mis liiki koht'
    )
    kirjeldus = models.TextField(
        'Kirjeldus',
        blank=True,
        help_text='Koha või objekti kirjeldus'
    )
    # Seotud:
    objektid = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Kohad'
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
        if self.hist_date:
            sy = self.hist_date.year
        else:
            if self.hist_year:
                sy = self.hist_year
            else:
                sy = ''
        if self.hist_enddate:
            su = self.hist_enddate.year
        elif self.hist_endyear:
            su = self.hist_endyear
        elif self.gone:
            su = '?'
        else:
            su = ''
        daatumid = f' {sy}-{su}' if any([sy, su]) else ''
        return self.nimi + daatumid

    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus

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
        return Pilt.objects.filter(objektid=self.id, profiilipilt_objekt__isnull=False).first()

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
    gone = models.BooleanField(  # surnud teadmata ajal
        'Lõpetatud/likvideeritud',
        default=False,
        help_text='Lõpetatud/likvideeritud'
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
        if self.hist_date:
            sy = self.hist_date.year
        else:
            if self.hist_year:
                sy = self.hist_year
            else:
                sy = ''
        if self.hist_enddate:
            su = self.hist_enddate.year
        elif self.hist_endyear:
            su = self.hist_endyear
        elif self.gone:
            su = '?'
        else:
            su = ''
        daatumid = f' {sy}-{su}' if any([sy, su]) else ''
        return self.nimi + daatumid

    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus

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
        return Pilt.objects.filter(organisatsioonid=self.id, profiilipilt_organisatsioon__isnull=False).first()

    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Organisatsioonid"


class Isik(models.Model):
    perenimi = models.CharField(
        'Perekonnanimi',
        max_length=100,
        help_text="Perekonnanimi"
    )
    eesnimi = models.CharField(
        'Eesnimi',
        max_length=100,
        blank=True,
        help_text="Eesnimi/nimed/initsiaal(id)"
    )
    # Eludaatumid
    hist_date = models.DateField(
        'Sünniaeg',
        null=True,
        blank=True,
        help_text="Sündinud"
    )
    hist_year = models.IntegerField(  # juhuks kui on teada ainult aasta
        'Sünniaasta',
        null=True,
        blank=True,
        help_text='Sünniaasta'
    )
    synd_koht = models.CharField(
        'Sünnikoht',
        max_length=100,
        blank=True,
        help_text="Sünnikoht"
    )
    hist_enddate = models.DateField(
        'Surmaaeg',
        null=True,
        blank=True,
        help_text="Surmaaeg"
    )
    hist_endyear = models.IntegerField(  # juhuks kui on teada ainult aasta
        'Surma-aasta',
        null=True,
        blank=True,
        help_text='Surma-aasta'
    )
    gone = models.BooleanField( # surnud teadmata ajal
        'Surnud',
        default=False,
        help_text='Kas on surnud?'
    )
    surm_koht = models.CharField(
        'Surmakoht',
        max_length=100,
        blank=True,
        help_text="Surmakoht"
    )
    maetud = models.CharField(
        'Maetud',
        max_length=200,
        blank=True,
        help_text="Matmiskoht"
    )
    # Kirjeldus
    kirjeldus = models.TextField(
        blank=True,
        help_text="Elulugu"
    )
    # Seotud
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
        help_text="Milliste kohtadega seotud"
    )
    organisatsioonid = models.ManyToManyField(
        Organisatsioon,
        blank=True,
        help_text="Milliste organisatsioonidega seotud"
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
        # Eesnimi
        if self.eesnimi:
            eesnimi = self.eesnimi
        else:
            eesnimi = ''
        # Sünniaeg
        if self.hist_date:
            sy = self.hist_date.year
        else:
            if self.hist_year:
                sy = self.hist_year
            else:
                sy = ''
        # Surmaaeg
        if self.hist_enddate:
            su = self.hist_enddate.year
        elif self.hist_endyear:
            su = self.hist_endyear
        elif self.gone:
            su = '?'
        else:
            su = ''
        daatumid = f'{sy}-{su}' if any([sy, su]) else ''
        return ' '.join([eesnimi, self.perenimi, daatumid])

    def __repr__(self):
        lyhinimi = self.perenimi
        if self.eesnimi:
            lyhinimi += ', ' + self.eesnimi[0] + '.'
        return lyhinimi

    @property
    def lyhinimi(self):
        lyhinimi = self.perenimi
        if self.eesnimi:
            lyhinimi += ', ' + self.eesnimi[0] + '.'
        return lyhinimi

    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus

    def get_absolute_url(self):
        return reverse('wiki:wiki_isik_detail', kwargs={'pk': self.pk})

    def vanus(self, d=datetime.date.today()):
        if self.hist_date:
            return d.year - self.hist_date.year
        else:
            return None

    def profiilipilt(self):
        return Pilt.objects.filter(isikud=self.id, profiilipilt_isik__isnull=False).first()

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


# Ajutine filtreeriv Manager kui vaja näidata ilma Kroonikata TODO: Kuni revisjoni lõpuni
class KroonikataArtikkelManager(models.Manager):
    def get_queryset(self):
       return super().get_queryset().filter(kroonika__isnull=True)


# # Tagastab ainult kirjed, kus algus- ja lõppkuupäev on esitatud
# class HistDatesStringArtikkelManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().filter(hist_date__isnull=False, hist_enddate__isnull=False)
#
#     def with_histdates_strings(self):
#         from django.db import connection
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT a.id, a.hist_date, a.hist_enddate
#                 FROM wiki_artikkel a
#                 WHERE a.hist_date IS NOT NULL AND a.hist_enddate IS NOT NULL
#                 ORDER BY a.hist_date""")
#             result_list = []
#             for row in cursor.fetchall():
#                 a = self.model(id=row[0], hist_date=row[1], hist_enddate=row[2])
#                 tekst = f'{str(a.hist_date.month).zfill(2)}{str(a.hist_date.day).zfill(2)}'
#                 vahemik = (a.hist_enddate - a.hist_date).days
#                 if vahemik < 100: # kui on loogiline vahemik (max 100 päeva)
#                     from datetime import timedelta
#                     for n in range(vahemik):
#                         vahemiku_p2ev = a.hist_date + timedelta(days=n+1)
#                         vahemiku_p2eva_string = f' {str(vahemiku_p2ev.month).zfill(2)}{str(vahemiku_p2ev.day).zfill(2)}'
#                         tekst += vahemiku_p2eva_string
#                 a.hist_dates_string = tekst
#                 result_list.append(a)
#         return result_list

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
    hist_searchdate = models.DateField(  # automaatne väli, kui täpset kuupäeva pole teada
        'Tuletatud kuupäev',
        null=True,
        blank=True
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
    last_accessed = models.DateTimeField(
        verbose_name='Vaadatud',
        default=timezone.now
    )
    total_accessed = models.PositiveIntegerField(
        verbose_name='Vaatamisi',
        default=0
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

    objects = models.Manager()  # The default manager
    # objects = KroonikataArtikkelManager() # Ajutine seade TODO: Kuni revisjoni lõpuni
    # hist_date_ranges = HistDatesStringArtikkelManager()

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
        return Pilt.objects.filter(artiklid=self.id, profiilipilt_artikkel__isnull=False).first()

    # Kui tekstis on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.body_text

    @property # TODO: Selleks et otsida kuupäeva, mis jääb alguse ja lõpu vahele [str in hist_dates_string]
    def hist_dates_string(self):
        tekst = f'{str(self.hist_date.month).zfill(2)}{str(self.hist_date.day).zfill(2)}'
        if all([self.hist_date, self.hist_enddate]):
            vahemik = (self.hist_enddate - self.hist_date).days
            if vahemik < 100: # kui on loogiline vahemik (max 100 päeva)
                from datetime import timedelta
                for n in range(vahemik):
                    vahemiku_p2ev = self.hist_date + timedelta(days=n+1)
                    vahemiku_p2eva_string = f' {str(vahemiku_p2ev.month).zfill(2)}{str(vahemiku_p2ev.day).zfill(2)}'
                    tekst += vahemiku_p2eva_string
        return tekst

    class Meta:
        ordering = ['hist_searchdate']
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
    pilt_height_field = models.IntegerField() # pildi mõõt
    pilt_width_field = models.IntegerField() # pildi mõõt
    pilt = models.ImageField(
        upload_to='pildid/%Y/%m/%d/',
        max_length=255,
        height_field = 'pilt_height_field',
        width_field = 'pilt_width_field',
        null=True,
        blank=True
    )
    pilt_thumbnail = models.ImageField(
        upload_to='', # Salvestatakse samasse kataloogi pildiga make_thumbnail abil
        editable=False,
        blank=True
    )
    pilt_icon = models.ImageField(
        upload_to='', # Salvestatakse samasse kataloogi pildiga make_thumbnail abil
        editable=False,
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
    # NB! Pildi puhul kasutatakse veebis ainult esimest viidet
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
        tekst = self.kirjeldus or self.nimi # Kui on, siis kirjeldus, muidu pealkiri
        return tekst

    def __repr__(self):
        return self.nimi

    def caption(self):
        tekst = self.kirjeldus or self.nimi # Kui on, siis kirjeldus, muidu pealkiri
        viide = self.viited.first()
        if viide:
            tekst = f'{tekst} (Allikas: {viide})'
        return tekst

    def link(self):
        return self.pilt.url

    def save(self, *args, **kwargs):
        # save for image
        super(Pilt, self).save(*args, **kwargs)
        make_thumbnail(self.pilt_thumbnail, self.pilt, 'thumb')
        make_thumbnail(self.pilt_icon, self.pilt, 'icon')
        # save for thumbnail and icon
        super(Pilt, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Pildid"


class Vihje(models.Model):
    kirjeldus = models.TextField(
        'Vihje',
        help_text='Vihje parandamiseks/täiendamiseks',
    )
    kontakt = models.CharField(
        'Kontakt',
        help_text='Sinu nimi/kontaktandmed',
        max_length=100,
        blank=True
    )
    http_referer = models.CharField(
        'Objekt',
        max_length=100,
        blank=True
    )
    remote_addr = models.CharField(
        'IP aadress',
        max_length=40,
        blank=True
    )
    django_version = models.CharField(
        'Django versioon',
        max_length=10,
        blank=True
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True
    )
    end_date = models.DateField(  # parandatud/lahendatud
        'Lahendatud',
        null=True,
        blank=True,
        help_text="Lahendatud/parandatud"
    )

    def __str__(self):
        tekst = self.kirjeldus[:50]
        if len(self.kirjeldus) > 50:
            tyhik = self.kirjeldus.find(' ',50,70)
            if tyhik > 0:
                tekst = self.kirjeldus[:tyhik] + '...'
        return tekst

    def __repr__(self):
        y_str = str(self.inp_date.year)
        m_str = str(self.inp_date.month).zfill(2)
        d_str = str(self.inp_date.day).zfill(2)
        tekst = self.kirjeldus[:50]
        return f'{y_str}{m_str}{d_str}: {tekst}'


    class Meta:
        verbose_name_plural = "Vihjed"