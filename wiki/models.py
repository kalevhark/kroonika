#
# Andmebaaside kirjeldused
# hist_date: algushetke originaalkuupäev kehtinud kalendri järgi
# hist_year: algushetke aasta, kui ainult teada
# hist_month: algushetke kuu, kui see on teada
# hist_enddate: l6pphetke originaalkuup2ev kehtinud kalendri j2rgi
# hist_endyear: l6pphetke aasta, kui ainult teada
# dob = vastavalt valikule vkj v6i ukj hist_date j2rgi arvutatud kuup2ev
# doe = vastavalt valikule vkj v6i ukj hist_enddate j2rgi arvutatd kuup2ev

from datetime import date, datetime, timedelta
from io import BytesIO
import os
import os.path
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import \
    Count, Max, Min, \
    Case, F, Func, Q, When, \
    Value, BooleanField, DateField, DecimalField, IntegerField, \
    ExpressionWrapper

from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

from PIL import Image

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

VIGA_TEKSTIS = '[?]'

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

# Lisab numbri ja punkti vahele backslashi
def add_escape(matchobj):
    leiti = matchobj.group(0)
    return "\\".join([leiti[:-1], "."])

# Muudab teksti, et markdown ei märgistaks automaatselt nummerdatud liste
def escape_numberdot(string):
    # Otsime kas teksti alguses on arv ja punkt
    string_modified = re.sub(r"(\A)(\d+)*\.", add_escape, string)
    # Otsime kas lõigu alguses on arv ja punkt
    string_modified = re.sub(r"(\n)(\d+)*\.", add_escape, string_modified)
    return string_modified

# Tagastab andmebaasi kanded, millel on hist_date, hist_year, hist_enddate, hist_endyear andmed
# koos ukj v6i vkj arvutamisega
# def filtered_queryset_with_dob_doe(initial_queryset, ukj_state):
#     if ukj_state == 'true': # ukj
#         filtered_queryset = initial_queryset. \
#             exclude(
#             hist_date__isnull=True,
#             hist_year__isnull=True,
#             hist_enddate__isnull=True,
#             hist_endyear__isnull=True,
#         ). \
#             annotate(
#             dob=Case(
#                 When(hist_date__gt=date(1919, 1, 31), then=F('hist_date')),
#                 When(hist_date__gt=date(1900, 2, 28), then=F('hist_date') + timedelta(days=13)),
#                 When(hist_date__gt=date(1800, 2, 28), then=F('hist_date') + timedelta(days=12)),
#                 When(hist_date__gt=date(1700, 2, 28), then=F('hist_date') + timedelta(days=11)),
#                 When(hist_date__gt=date(1582, 10, 5), then=F('hist_date') + timedelta(days=10)),
#                 default=F('hist_date'),
#                 output_field=DateField()
#             ), \
#             doe=Case(
#                 When(hist_enddate__gt=date(1919, 1, 31), then=F('hist_enddate')),
#                 When(hist_enddate__gt=date(1900, 2, 28), then=F('hist_enddate') + timedelta(days=13)),
#                 When(hist_enddate__gt=date(1800, 2, 28), then=F('hist_enddate') + timedelta(days=12)),
#                 When(hist_enddate__gt=date(1700, 2, 28), then=F('hist_enddate') + timedelta(days=11)),
#                 When(hist_enddate__gt=date(1582, 10, 5), then=F('hist_enddate') + timedelta(days=10)),
#                 default=F('hist_enddate'),
#                 output_field=DateField()
#             )
#         )
#     else: # vkj
#         filtered_queryset = initial_queryset. \
#             exclude(
#             hist_date__isnull=True,
#             hist_year__isnull=True,
#             hist_enddate__isnull = True,
#             hist_endyear__isnull = True
#         ). \
#             annotate(
#             dob=F('hist_date'),
#             doe=F('hist_enddate')
#         )
#     return filtered_queryset


# Filtreerime kanded, mille kohta on teada daatumid vastavalt valikule vkj/ukj
class DaatumitegaManager(models.Manager):

    def daatumitega(self, request):
        ukj_state = request.session.get('ukj', 'false')
        initial_queryset = super().get_queryset()
        if initial_queryset.model.__name__ == 'Artikkel':
            # Kui andmebaas on Artikkel, siis filtreerime kasutaja järgi
            if not (request.user.is_authenticated and request.user.is_staff):
                initial_queryset = initial_queryset.filter(kroonika__isnull=True)
            # Filtreerime välja ilma daatumiteta kirjed
            filtered_queryset = initial_queryset. \
                exclude(
                hist_date__isnull=True,
                hist_year__isnull=True,
                hist_enddate__isnull=True,
            )
        else: # Kui andmebaas on Isik, Organisatsioon, Objekt
            # Filtreerime välja ilma daatumiteta kirjed
            filtered_queryset = initial_queryset. \
                exclude(
                hist_date__isnull=True,
                hist_year__isnull=True,
                hist_enddate__isnull=True,
                hist_endyear__isnull=True,
            )
        # Arvutame abiväljad vastavalt kasutaja kalendrieelistusele
        # dob: day of begin|birth
        # dow: day of end
        if ukj_state == 'true':  # ukj
            filtered_queryset = filtered_queryset.annotate(
                dob=Case(
                    When(hist_date__gt=date(1919, 1, 31), then=F('hist_date')),
                    When(hist_date__gt=date(1900, 2, 28), then=F('hist_date') + timedelta(days=13)),
                    When(hist_date__gt=date(1800, 2, 28), then=F('hist_date') + timedelta(days=12)),
                    When(hist_date__gt=date(1700, 2, 28), then=F('hist_date') + timedelta(days=11)),
                    When(hist_date__gt=date(1582, 10, 5), then=F('hist_date') + timedelta(days=10)),
                    default=F('hist_date'),
                    output_field=DateField()
                ),
                doe=Case(
                    When(hist_enddate__gt=date(1919, 1, 31), then=F('hist_enddate')),
                    When(hist_enddate__gt=date(1900, 2, 28), then=F('hist_enddate') + timedelta(days=13)),
                    When(hist_enddate__gt=date(1800, 2, 28), then=F('hist_enddate') + timedelta(days=12)),
                    When(hist_enddate__gt=date(1700, 2, 28), then=F('hist_enddate') + timedelta(days=11)),
                    When(hist_enddate__gt=date(1582, 10, 5), then=F('hist_enddate') + timedelta(days=10)),
                    default=F('hist_enddate'),
                    output_field=DateField()
                )
            )
        else:  # vkj
            filtered_queryset = filtered_queryset.annotate(
                dob=F('hist_date'),
                doe=F('hist_enddate')
            )
        filtered_queryset = filtered_queryset.annotate(
            calc_searchdate=Case(
                When(dob=None, then=F('hist_searchdate')),
                default=F('dob'),
                output_field=DateField()
            )
        )
        from django.db.models.functions import ExtractYear, Extract, Cast
        from django.db.models import ExpressionWrapper
        calc_qs = filtered_queryset.annotate(
            y = Extract('dob', 'year', output_field=IntegerField()),
            m = Extract('dob', 'month', output_field=IntegerField()),
            d = Extract('dob', 'day', output_field=IntegerField())
        ).annotate(calc_searchdate=Func(F('y'), F('m'), F('d'), function='CONCAT'))
        print(calc_qs[2000].calc_searchdate)
        return filtered_queryset

#
# Allikad: raamatud. ajakirjandusväljaanded, veebilehed, arhiivid jne
#
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
        ordering = ['hist_date', 'hist_year']
        verbose_name_plural = "Viited"

    def __str__(self):
        # Viite autorid
        autorid = ''
        if self.allikas.autorid:
            for obj in self.allikas.autorid.all():
                autorid = ', '.join([obj.lyhinimi])
        # Viite kohaviida andmed
        if self.allikas.nimi:
            allika_nimi = self.allikas.nimi
        else:
            allika_nimi = ''
        viit = ''
        if self.peatykk:
            peatykk = self.peatykk
        else:
            peatykk = ''
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

# # Ajutine filtreeriv Manager kui vaja näidata kuni 100 aastat tagasi TODO: Kuni revisjoni lõpuni
# class ObjektSajandTagasiManager(models.Manager):
#     def get_queryset(self):
#         sajandtagasi = datetime.date.today().year - 100
#         return super().get_queryset().filter(Q(hist_year__lte=sajandtagasi) | Q(hist_year__isnull=True))



class Objekt(models.Model):
    OBJEKTITYYP = (
        ('H', 'Hoone'),
        ('T', 'Tänav'),
        ('E', 'Ehitis'),
        ('A', 'Asustusüksus'),
        ('M', 'Muu'),
    )
    nimi = models.CharField(
        'Kohanimi',
        max_length=200,
        help_text='Kohanimi/nimed'
    )
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
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
    kirjeldus = MarkdownxField(
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

    objects = DaatumitegaManager()

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
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        return markdownify(escape_numberdot(self.kirjeldus))

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_objekt_detail', kwargs=kwargs)

    def vanus(self, d=timezone.now()):
        if self.hist_date:
            return d.year - self.hist_date.year
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    def profiilipilt(self):
        return Pilt.objects.filter(objektid=self.id, profiilipilt_objekt=True).first()

    def save(self, *args, **kwargs):
        # Loome slugi
        value = self.nimi
        self.slug = slugify(value, allow_unicode=True)
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if self.hist_date:
            self.hist_year = self.hist_date.year
            self.hist_month = self.hist_date.month
        if self.hist_enddate:
            self.hist_endyear = self.hist_enddate.year
        super().save(*args, **kwargs)


    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Kohad"


# # Ajutine filtreeriv Manager kui vaja näidata kuni 100 aastat tagasi TODO: Kuni revisjoni lõpuni
# class OrganisatsioonSajandTagasiManager(models.Manager):
#     def get_queryset(self):
#         sajandtagasi = datetime.date.today().year - 100
#         return super().get_queryset().filter(Q(hist_year__lte=sajandtagasi) | Q(hist_year__isnull=True))


class Organisatsioon(models.Model):
    nimi = models.CharField(
        'Asutise nimi',
        max_length=200,
        help_text='Asutise nimi/nimed'
    )
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
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
    kirjeldus=MarkdownxField(
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

    objects = DaatumitegaManager()

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
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        return markdownify(escape_numberdot(self.kirjeldus))

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_organisatsioon_detail', kwargs=kwargs)

    def vanus(self, d=timezone.now()):
        if self.hist_date:
            return d.year - self.hist_date.year
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    def profiilipilt(self):
        return Pilt.objects.filter(organisatsioonid=self.id, profiilipilt_organisatsioon=True).first()

    def save(self, *args, **kwargs):
        # Loome slugi
        value = self.nimi
        self.slug = slugify(value, allow_unicode=True)
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if self.hist_date:
            self.hist_year = self.hist_date.year
            self.hist_month = self.hist_date.month
        if self.hist_enddate:
            self.hist_endyear = self.hist_enddate.year
        super().save(*args, **kwargs)


    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Asutised"


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
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
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
    kirjeldus=MarkdownxField(
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

    # objects = models.Manager()
    objects = DaatumitegaManager()

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
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        return markdownify(escape_numberdot(self.kirjeldus))

    # Sünnikuupäev uue kalendri järgi #TODO hetkel ei kasuta!
    # @property
    # def hist_date_ukj(self):
    #     return vkj2ukj(self.hist_date)

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_isik_detail', kwargs=kwargs)

    def vanus(self, d=timezone.now()):
        if self.hist_date:
            return d.year - self.hist_date.year
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    def vanus_ukj(self, d=timezone.now()):
        if self.hist_date_ukj:
            return d.year - self.hist_date_ukj.year
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    def profiilipilt(self):
        return Pilt.objects.filter(isikud=self.id, profiilipilt_isik=True).first()

    def save(self, *args, **kwargs):
        # Loome slugi
        value = ' '.join(filter(None, [self.eesnimi, self.perenimi]))
        self.slug = slugify(value, allow_unicode=True)
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if self.hist_date:
            self.hist_year = self.hist_date.year
        if self.hist_enddate:
            self.hist_endyear = self.hist_enddate.year
        super().save(*args, **kwargs)


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


# # Ajutine filtreeriv Manager kui vaja näidata ilma Kroonikata TODO: Kuni revisjoni lõpuni
# class ArtikkelKroonikataManager(models.Manager):
#     def get_queryset(self):
#        return super().get_queryset().filter(kroonika__isnull=True)
#
# # Ajutine filtreeriv Manager kui vaja näidata kuni 100 aastat tagasi TODO: Kuni revisjoni lõpuni
# class ArtikkelSajandTagasiManager(models.Manager):
#     def get_queryset(self):
#         sajandtagasi = datetime.date.today().year - 100
#         return super().get_queryset().filter(hist_year__lte=sajandtagasi)

class Artikkel(models.Model):
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
    )
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
    body_text = MarkdownxField(
        'Lugu',
        help_text='Tekst'
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
        verbose_name='Seotud asutised'
    )
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
        verbose_name='Seotud kohad'
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Seotud viited',
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

    # objects = models.Manager()  # The default manager
    objects = DaatumitegaManager()

    def __str__(self):
        summary = self.body_text
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        splits = summary.split(' ')
        tekst = ' '.join(splits[:10]) # 10 esimest sõna
        if len(tekst) < len(self.body_text):
            tekst += '...'
        return tekst

    def __repr__(self):
        tekst = str(self.hist_year) + ':' + self.body_text
        return tekst

    # def get_absolute_url(self):
    #     return reverse('wiki:wiki_artikkel_detail', kwargs={'pk': self.pk})

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_artikkel_detail', kwargs=kwargs)

    def headline(self):
        if len(self.body_text) > 50:
            tyhik = self.body_text.find(' ',50,70)
            if tyhik > 0:
                return self.body_text[:tyhik] + '...'
        return self.body_text[:50]
    headline.short_description = 'Lugu'

    def profiilipilt(self):
        return Pilt.objects.filter(artiklid=self.id, profiilipilt_artikkel=True).first()

    # Kui tekstis on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.body_text

    @property # TODO: Selleks et otsida kuupäeva, mis jääb alguse ja lõpu vahele [str in hist_dates_string]
    def hist_dates_string(self):
        dob = self.dob
        doe = self.doe
        tekst = f'{str(dob.month).zfill(2)}{str(dob.day).zfill(2)}'
        if all([dob, doe]):
            vahemik = (doe - dob).days
            if vahemik < 100: # kui on loogiline vahemik (max 100 päeva)
                for n in range(vahemik):
                    vahemiku_p2ev = dob + timedelta(days=n+1)
                    vahemiku_p2eva_string = f' {str(vahemiku_p2ev.month).zfill(2)}{str(vahemiku_p2ev.day).zfill(2)}'
                    tekst += vahemiku_p2eva_string
        return tekst

    # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        return markdownify(escape_numberdot(self.body_text))

    # Create a property that returns the summary markdown instead
    @property
    def formatted_markdown_summary(self):
        summary = self.body_text
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        return markdownify(escape_numberdot(summary[:100]) + "...")

    def save(self, *args, **kwargs):
        # Loome slugi teksti esimesest 10 sõnast max 200 tähemärki
        value = ' '.join(self.body_text.split(' ')[:10])[:200]
        self.slug = slugify(value, allow_unicode=True)
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if self.hist_date:
            self.hist_year = self.hist_date.year
            self.hist_month = self.hist_date.month
            self.hist_searchdate = self.hist_date
        else:
            if self.hist_year:
                y = self.hist_year
                if self.hist_month:
                    m = self.hist_month
                else:
                    m = 1
                self.hist_searchdate = datetime(y, m, 1)
            else:
                self.hist_searchdate = None
        super().save(*args, **kwargs)

    class Meta:
        ordering = [
            'hist_year',
            'hist_month',
            'hist_date',
            'id'
        ]
        verbose_name = "Lugu"
        verbose_name_plural = "Lood"


class Pilt(models.Model):
    nimi = models.CharField(
        'Pealkiri',
        max_length=100,
        blank=True
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
    pilt_height_field = models.IntegerField(
        null=True
    ) # pildi mõõt
    pilt_width_field = models.IntegerField(
        null=True
    ) # pildi mõõt
    pilt = models.ImageField(
        upload_to='pildid/%Y/%m/%d/',
        max_length=255,
        height_field = 'pilt_height_field',
        width_field = 'pilt_width_field',
        # null=True,
        # blank=True
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

    # def clean(self):
    #     # Täidame tühja nimekoha failinimega ilma laiendita
    #     if not self.nimi and self.pilt:
    #         base = os.path.basename(self.pilt.name)
    #         self.nimi = os.path.splitext(base)[0]

    def caption(self):
        tekst = self.kirjeldus or self.nimi # Kui on, siis kirjeldus, muidu pealkiri
        viide = self.viited.first()
        if viide:
            tekst = f'{tekst} (Allikas: {viide})'
        return tekst

    def link(self):
        return self.pilt.url

    def save(self, *args, **kwargs):
        # Täidame tühja nimekoha failinimega ilma laiendita
        if not self.nimi and self.pilt:
            base = os.path.basename(self.pilt.name)
            self.nimi = os.path.splitext(base)[0]
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if self.hist_date:
            self.hist_year = self.hist_date.year
            self.hist_month = self.hist_date.month
        # save for image
        super(Pilt, self).save(*args, **kwargs)
        # Loome pisipildid
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
        max_length=250,
        blank=True
    )
    remote_addr = models.CharField(
        'IP aadress',
        max_length=40,
        blank=True
    )
    http_user_agent = models.CharField(
        'Veebilehitseja',
        max_length=200,
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