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
from functools import reduce
from io import BytesIO
import json
from operator import or_
import os
import os.path
import re
import string

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import \
    Count, Max, Min, \
    Case, F, Func, Q, When, \
    Value, BooleanField, DateField, DateTimeField, DecimalField, IntegerField
from django.db.models.functions import Concat, Extract, ExtractYear, ExtractMonth, ExtractDay
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify

import folium

from markdownx.models import MarkdownxField
from markdownx.utils import markdownify

from PIL import Image

from shapely.geometry import shape

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

PREDECESSOR_DESCENDANT_NAMES = {
    'Isik': {
        'predecessor_name': 'Vanem',
        'predecessor_name_plural': 'Vanemad',
        'descendant_name': 'Laps',
        'descendant_name_plural': 'Lapsed'
    },
    'Organisatsioon': {
        'predecessor_name': 'Eelkäija',
        'predecessor_name_plural': 'Eelkäijad',
        'descendant_name': 'Järeltulija',
        'descendant_name_plural': 'Järeltulijad'
    },
    'Objekt': {
        'predecessor_name': 'Eelkäija',
        'predecessor_name_plural': 'Eelkäijad',
        'descendant_name': 'Järeltulija',
        'descendant_name_plural': 'Järeltulijad'
    },
}

def make_thumbnail(dst_image_field, src_image_field, name_suffix, sep='_'):
    """
    make thumbnail image and field from source image field

    @example
        thumbnail(self.thumbnail, self.image, (200, 200), 'thumb')
    """
    # create thumbnail image
    media_dir = settings.MEDIA_ROOT
    with Image.open(media_dir / src_image_field.name) as img:
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
        if dst_ext in ['.jpg', '.jpeg', '.jfif']:
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
# Vajalik funktsiooni escape_numberdot jaoks
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

# Töötleb pilditagid [pilt_nnnn] piltideks
def add_markdownx_pildid(string):
    # Otsime kõik pilditagid
    pattern = re.compile(r'\[pilt_([0-9]*)]')
    tagid = re.finditer(pattern, string)
    for tag in tagid:
        # tag = tag_leitud[0] # '[pilt_nnnn]'
        # id = int(tag.split('_')[-1][:-1])
        id = tag.groups()[0]
        pilt = Pilt.objects.get(id=id)
        if pilt:
            pildi_url = pilt.pilt.url
            pildi_caption = pilt.caption()
            # pildi_markdown = ''.join(
            #     [
            #         '<div class="w3-row">',
            #         f'<img src="{pildi_url}"',
            #         f' class="pilt-pildidtekstis"',
            #         f' alt="{pildi_caption}"',
            #         f' data-pilt-id="{ pilt.id }"',
            #         f'>',
            #         f'<p><small>{pildi_caption}',
            #         f'</small></p>',
            #         '</div>'
            #      ]
            # )
            img = f'<img src="{pildi_url}" class="pilt-pildidtekstis" alt="{pildi_caption}" data-pilt-id="{pilt.id}" >'
            caption = f'<p><small>{pildi_caption}</small></p>'
            html = f'<div class="w3-row">{img}{caption}</div>'
            string = string.replace(tag[0], html)
    return string

# Töötleb lingitagid [Duck Duck Go]([isik_nnnn]) linkideks
def add_markdown_objectid(string):
    """
    @param string:
    @return:
    """
    pattern = re.compile(rf'\[([\wÀ-ÿ\s\"\-]+)\]\(\[(isik|organisatsioon|objekt)_([0-9]*)\]\)')
    tagid = re.finditer(pattern, string)
    for tag in tagid:
        tekst, model_name, id = tag.groups()
        pos = tag.span()[0]
        model = apps.get_model('wiki', model_name)
        obj = model.objects.get(id=id)
        url = obj.get_absolute_url()
        data_attrs = f'data-model="{model_name}" data-id="{obj.id}"'
        span = f'<span id="{model_name}_{obj.id}_pos{pos}" title="{obj}" {data_attrs}>{tekst}</span>'
        html = f'<a class="text-{model_name} hover-{model_name} tooltip-content" href="{url}">{span}</a>'
        string = string.replace(tag[0], html, 1)
    return string

# Lisab objecti tekstile markdown formaadis viited
def add_markdownx_viited(obj):
    viited = obj.viited.all()
    if viited:
        viite_string = '<i class="{% icon_viide %} icon-viide" alt="Viited"></i>'
        viitenr = 1
        for viide in viited:
            viite_string += f'\n[^{viitenr}]: '
            if viide.url:
                viite_string += f'<a class="hover-viide" href="{viide.url}" target="_blank">{viide}</a>'
            else:
                viite_string += f'<span>{viide}</span>'
            viitenr += 1
        viite_string = f'<div class="w3-panel w3-small text-viide">{viite_string}</div>'
    else:
        viite_string = ''
    return viite_string

# Parandab markdownify renderdamise vea
def fix_markdownified_text(text):
    # k6rvaldame ülearuse horisontaaleraldaja
    text = text.replace('<hr />', '')
    # k6rvaldame vale <p> tagi algusest
    text = text[3:]
    # k6rvaldame vale </p> tagi
    text = text.replace('</p>\n<div class="footnote">', '\n<div class="footnote">')
    # k6rvaldame vigase </div> tagi
    text = text.replace('</div>&#160;', '&#160;')
    # lisame l6ppu </div> tagi
    text = text + '</div>'
    return text

# map punctuation to space
# Vajalik funktsiooni object2keywords jaoks
translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))

# Moodustab objecti nimest märksõnad
def object2keywords(obj):
    object_string = str(obj)
    translation = re.sub(' +', ' ', object_string.translate(translator))
    words = translation.split(' ')
    keywords = [word for word in words if len(word) > 2]
    return ','.join(settings.KROONIKA['KEYWORDS'] + [object_string] + keywords)

# tagastab lühendatud kirjelduse content tooltipi jaoks
# v6etakse esimene l6ik (reavahetuseni)
# kui esimene lõik on pikem määratud tähtede arvust, siis lühendatakse s6nade kaupa
def get_kirjeldus_lyhike(self):
    kirjeldus = ''
    if self.kirjeldus:
        kirjeldus = str(self.kirjeldus)
        kirjeldus = kirjeldus.splitlines()[0]
        if len(kirjeldus) > 500:
            splitid = kirjeldus.split(' ')
            for n in range(len(splitid)):
                kirjeldus = ' '.join(splitid[:n])
                if len(kirjeldus) > 500:
                    if len(kirjeldus) < len(str(self.kirjeldus)):
                        kirjeldus += '...'
                    break
    return kirjeldus

# def add_calendarstatus(request):
def get_calendarstatus(request):
    if request:
        # kalendrivalik ukj='on' v6i ukj='off'
        # request.session['ukj'] = request.session.get('ukj', 'off')
        ukj_state = request.session.get('ukj', 'off')
        request.session['ukj'] = ukj_state

        # viimane kalendrivalik 'yyyy-m'
        t2na = timezone.now()
        user_calendar_view_last = date(t2na.year - 100, t2na.month, t2na.day).strftime("%Y-%m")
        request.session['user_calendar_view_last'] = request.session.get('user_calendar_view_last', user_calendar_view_last)
    else:
        ukj_state = 'off'
    return ukj_state

# Filtreerime kanded, mille kohta on teada daatumid, vastavalt valikule vkj/ukj
# vastavalt kasutajaõigustele
class DaatumitegaManager(models.Manager):

    # def get_queryset(self):
    #     return super().get_queryset()

    def daatumitega(self, request=None):
        # Kontrollime kas kasutaja on autenditud ja admin
        user_is_staff = request and request.user.is_authenticated and request.user.is_staff

        # add_calendarstatus(request)
        # ukj_state = 'off'
        # # # Kas kalendrivalik on sessioonis olemas
        # try:
        #     ukj_state = request.session.get('ukj')
        # except:
        #     pass

        # kalendrisüsteemi valik
        ukj_state = get_calendarstatus(request)
        # default queryset from model
        initial_queryset = super().get_queryset()

        # Filtreerime kasutaja järgi
        if initial_queryset.model.__name__ == 'Artikkel':
            # Kui andmebaas on Artikkel
            # if not (request.user.is_authenticated and request.user.is_staff):
            if user_is_staff:
                filtered_queryset = initial_queryset
            else:
                filtered_queryset = initial_queryset.filter(kroonika__isnull=True)

            filtered_queryset = filtered_queryset.annotate(
                search_year=Case(
                    When(hist_date__isnull=False, then=ExtractYear('hist_date')),
                    When(hist_year__isnull=False, then=F('hist_year')),
                    When(hist_year__isnull=True, then=0),
                ),
                search_month=Case(
                    When(hist_date__isnull=False, then=ExtractMonth('hist_date')),
                    When(hist_month__isnull=False, then=F('hist_month')),
                    When(hist_month__isnull=True, then=0),
                    output_field=IntegerField()
                ),
                search_day=Case(
                    When(hist_date__isnull=False, then=ExtractDay('hist_date')),
                    When(hist_date__isnull=True, then=0),
                    output_field=IntegerField()
                )
            ).order_by('search_year', 'search_month', 'search_day', 'id')
        else:
            # Kui andmebaas on Isik, Organisatsioon, Objekt
            # if not (request.user.is_authenticated and request.user.is_staff):
            if not user_is_staff:
                artikkel_qs = Artikkel.objects.daatumitega(request)
                # Algne aeglane päring, mis tekitas Organisatsioon tabeliga 5000+ ms päringuid
                # filtered_queryset = initial_queryset.filter(
                #     Q(viited__isnull=False) |
                #     Q(viited__isnull=True, artikkel__isnull=True) |
                #     Q(artikkel__in=artikkel_qs)
                # ).distinct()
                # Asendus eelmisele päringule, mis on kiirem
                artikliga = initial_queryset. \
                    filter(artikkel__in=artikkel_qs). \
                    values_list('id', flat=True)
                viitega = initial_queryset. \
                    filter(viited__isnull=False). \
                    values_list('id', flat=True)
                viiteta_artiklita = initial_queryset. \
                    filter(viited__isnull=True, artikkel__isnull=True). \
                    values_list('id', flat=True)
                model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])
                filtered_queryset = initial_queryset.filter(id__in=model_ids)
            else:
                filtered_queryset = initial_queryset
        # Arvutame abiväljad vastavalt kasutaja kalendrieelistusele
        # dob: day of begin|birth
        # doe: day of end
        if ukj_state == 'on':  # ukj
            filtered_queryset = filtered_queryset.annotate(
                dob=Case(
                    When(hist_date__gt=date(1918, 1, 31), then=F('hist_date')),
                    When(hist_date__gt=date(1900, 2, 28), then=F('hist_date') + timedelta(days=13)),
                    When(hist_date__gt=date(1800, 2, 28), then=F('hist_date') + timedelta(days=12)),
                    When(hist_date__gt=date(1700, 2, 28), then=F('hist_date') + timedelta(days=11)),
                    When(hist_date__gt=date(1582, 10, 5), then=F('hist_date') + timedelta(days=10)),
                    default=F('hist_date'),
                    output_field=DateField()
                ),
                doe=Case(
                    When(hist_enddate__gt=date(1918, 1, 31), then=F('hist_enddate')),
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
        # return Pilt.objects.filter(allikad=self.id, profiilipilt_allikas=True).first()
        return Pilt.objects.filter(profiilipilt_allikad=self).first()

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
    # TODO: Wiki markup süsteem viitamiseks tekstis, pole enam vaja
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
        'Leidandmed',
        max_length=50,
        null=True,
        blank=True
    )
    url = models.URLField( # Allika internetiaadress
        'Internet',
        blank=True,
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField( # selle j2rgi markdown j2rjestab!
        'Lisatud',
        auto_now_add=True
    )
    mod_date = models.DateTimeField(
        'Kasutatud',
        auto_now=True
    )

    class Meta:
        ordering = ['inp_date'] # NB! selle j2rgi j2rjestab viited markdownx!
        verbose_name_plural = "Viited"

    def __str__(self):
        parts = []
        # Viite autorid
        # autorid = ''
        if self.allikas.autorid.exists():
            autorid = ', '.join([obj.lyhinimi for obj in self.allikas.autorid.all()])
            parts.append(autorid.strip())
        # Viite kohaviida andmed
        if self.allikas.nimi:
            allika_nimi = self.allikas.nimi
            parts.append(allika_nimi.strip())
        # else:
        #    allika_nimi = ''
        # viit = ''
        if self.peatykk:
            peatykk = self.peatykk
            parts.append(peatykk.strip())
        # else:
        #     peatykk = ''
        if self.kohaviit: # kui on füüsiline asukoht
            # viit = viit + ', ' + self.kohaviit
            parts.append(self.kohaviit.strip())
        else: # kui on ainult internetilink
            if self.url:
                # viit = viit + ', ' + self.url # .split('/')[-1]
                parts.append(self.url.strip())
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
        parts.append(aeg.strip())
        # viide = ', '.join([autorid, peatykk, allika_nimi, viit, aeg]).replace(' , ', ', ')
        viide = ', '.join(parts) # .replace(' , ', ', ')
        # while viide.find(',,') > 0:
        #     viide = viide.replace(',,', ',')
        return viide # .strip()

    @property
    def markdownify(self):
        viide = str(self)
        if self.url:
            return f'<a href="{self.url}">{viide}</a>'
        else:
            return viide

class Objekt(models.Model):
    OBJEKTITYYP = (
        ('H', 'Hoone'), # maja
        ('T', 'Tänav'),
        ('E', 'Ehitis'), # sild, laululava,
        ('A', 'Ala'), # plats, piirkond, asustusüksus
        ('M', 'Muu'), # sh looduslikud objektid
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
        help_text='Varasemad aadressikujud'
    )
    hist_date = models.DateField(
        'Valminud',
        null=True,
        blank=True,
        help_text='Valmimise aeg'
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
        help_text='Hävimise või likvideerimise aeg'
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
        help_text='Mis tüüpi koht'
    )
    kirjeldus = MarkdownxField(
        'Kirjeldus',
        blank=True,
        help_text = '<br>'.join(
        [
            'Koha või objekti kirjeldus (MarkDown on toetatud);',
            'Pildi lisamiseks: [pilt_nnnn];',
            'Viite lisamiseks isikule, asutisele või kohale: nt [Mingi Isik]([isik_nnnn])',
        ]
    )
    )
    # Seotud:
    eellased = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Eellased',
        related_name='j2rglane',
        symmetrical=False
    )
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

    def __repr__(self):
        return self.nimi

    def __str__(self):
        # Moodustame nime
        nimeosad = [self.nimi]
        if self.asukoht:
            nimeosad.append(f'({self.asukoht})')

        # Lisame daatumid
        if self.hist_date:
            try:
                sy = self.dob.year
            except:
                sy = self.hist_date.year
        else:
            if self.hist_year:
                sy = self.hist_year
            else:
                sy = ''
        if self.hist_enddate:
            try:
                su = self.doe.year
            except:
                su = self.hist_enddate.year
        elif self.hist_endyear:
            su = self.hist_endyear
        elif sy and self.gone:
            su = '?'
        else:
            su = ''
        if any([sy, su]):
            nimeosad.append(f'{sy}-{su}')
        return ' '.join(nimeosad)

    @property
    def kirjeldus_lyhike(self):
        return get_kirjeldus_lyhike(self)

    # Kui objectil puudub viide, siis punane
    def colored_id(self):
        if self.viited.exists():
            color = ''
        elif not all(el.kroonika for el in self.artikkel_set.all()):
            color = ''
        else:
            color = 'red'
        return format_html(
            '<strong><span style="color: {};">{}</span></strong>',
            color,
            self.id
        )
    colored_id.short_description = 'ID'

    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # Create a property that returns the markdown instead
    # Lisame siia ka viited
    @property
    def formatted_markdown(self):
        tekst = self.kirjeldus
        if len(tekst) == 0:  # markdownx korrektseks tööks vaja, et sisu ei oleks null
            tekst = '<br>'
        tekst = add_markdown_objectid(tekst)
        # tekst = add_markdownx_pildid(tekst)
        viite_string = add_markdownx_viited(self)
        markdownified_text = markdownify(escape_numberdot(tekst) + viite_string)
        # Töötleme tekstisisesed pildid NB! pärast morkdownify, muidu viga!
        markdownified_text = add_markdownx_pildid(markdownified_text)
        if viite_string: # viidete puhul ilmneb markdownx viga
            return fix_markdownified_text(markdownified_text)
        else:
            return markdownified_text

    # Tekstis MarkDown kodeerimiseks
    def markdown_tag(self):
        return f'[{self.nimi}] ([obj_{self.id}])'

    # Keywords
    @property
    def keywords(self):
        return object2keywords(self)

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_objekt_detail', kwargs=kwargs)

    def vanus(self, d=datetime.now()):
        if self.hist_date:
            return d.year - self.dob.year
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    def profiilipilt(self):
        # return Pilt.objects.filter(objektid=self.id, profiilipilt_objekt=True).first()
        return Pilt.objects.filter(profiilipilt_objektid=self).first()

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
        ordering = ['slug'] # erimärkidega nimetuste välistamiseks
        verbose_name = 'objektid'
        verbose_name_plural = "Kohad" # kasutame eesti keeles suupärasemaks tegemiseks


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
        blank=True,
        help_text='<br>'.join(
            [
                'Asutise kirjeldus (MarkDown on toetatud);',
                'Pildi lisamiseks: [pilt_nnnn];',
                'Viite lisamiseks isikule, asutisele või kohale: nt [Mingi Isik]([isik_nnnn])',
            ]
        )
    )
    # Seotud:
    eellased = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Eellased',
        related_name='j2rglane',
        symmetrical=False
    )
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

    def __repr__(self):
        return self.nimi

    def __str__(self):
        if self.hist_date:
            try:
                sy = self.dob.year
            except:
                sy = self.hist_date.year
        else:
            if self.hist_year:
                sy = self.hist_year
            else:
                sy = ''
        if self.hist_enddate:
            try:
                su = self.doe.year
            except:
                su = self.hist_enddate.year
        elif self.hist_endyear:
            su = self.hist_endyear
        elif sy and self.gone:
            su = '?'
        else:
            su = ''
        daatumid = f' {sy}-{su}' if any([sy, su]) else ''
        return self.nimi + daatumid

    @property
    def kirjeldus_lyhike(self):
        return get_kirjeldus_lyhike(self)

    # Kui objectil puudub viide, siis punane
    def colored_id(self):
        if self.viited.exists():
            color = ''
        elif not all(el.kroonika for el in self.artikkel_set.all()):
            color = ''
        else:
            color = 'red'
        return format_html(
            '<strong><span style="color: {};">{}</span></strong>',
            color,
            self.id
        )
    colored_id.short_description = 'ID'

    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # Create a property that returns the markdown instead
    # Lisame siia ka viited
    @property
    def formatted_markdown(self):
        tekst = self.kirjeldus
        if len(tekst) == 0:  # markdownx korrektseks tööks vaja, et sisu ei oleks null
            tekst = '<br>'
        tekst = add_markdown_objectid(tekst)
        # tekst = add_markdownx_pildid(tekst)
        viite_string = add_markdownx_viited(self)
        # return markdownify(escape_numberdot(tekst) + viite_string)
        markdownified_text = markdownify(escape_numberdot(tekst) + viite_string)
        # Töötleme tekstisisesed pildid NB! pärast morkdownify, muidu viga!
        markdownified_text = add_markdownx_pildid(markdownified_text)
        if viite_string:  # viidete puhul ilmneb markdownx viga
            return fix_markdownified_text(markdownified_text)
        else:
            return markdownified_text

    # Tekstis MarkDown kodeerimiseks
    def markdown_tag(self):
        return f'[{self.nimi}] ([org_{self.id}])'

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_organisatsioon_detail', kwargs=kwargs)

    # Keywords
    @property
    def keywords(self):
        return object2keywords(self)

    def vanus(self, d=datetime.now()):
        if self.hist_date:
            return d.year - self.dob.year
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    def profiilipilt(self):
        # return Pilt.objects.filter(organisatsioonid=self.id, profiilipilt_organisatsioon=True).first()
        return Pilt.objects.filter(profiilipilt_organisatsioonid=self).first()

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
        ordering = ['slug'] # erimärkidega nimetuste välistamiseks
        verbose_name = 'organisatsioonid'
        verbose_name_plural = "Asutised" # kasutame eesti keeles suupärasemaks tegemiseks


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
    gone = models.BooleanField( # surnud
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
        help_text='<br>'.join(
            [
                'Isiku kirjeldus ja elulugu (MarkDown on toetatud);',
                'Pildi lisamiseks: [pilt_nnnn];',
                'Viite lisamiseks isikule, asutisele või kohale: nt [Mingi Isik]([isik_nnnn])',
            ]
        )
    )
    # Seotud
    eellased = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Eellased',
        related_name='j2rglane',
        symmetrical=False
    )
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
            try:
                sy = self.dob.year
            except:
                sy = self.hist_date.year
        else:
            if self.hist_year:
                sy = self.hist_year
            else:
                sy = ''
        # Surmaaeg
        if self.hist_enddate:
            try:
                su = self.doe.year
            except:
                su = self.hist_enddate.year
        elif self.hist_endyear:
            su = self.hist_endyear
        elif sy and self.gone:
            su = '?'
        else:
            su = ''
        daatumid = f'{sy}-{su}' if any([sy, su]) else ''
        return ' '.join([eesnimi, self.perenimi, daatumid])

    def __repr__(self):
        lyhinimi = self.perenimi
        eesnimi = self.eesnimi
        if eesnimi:
            if eesnimi.split(' ')[0] in ['hr', 'pr', 'dr', 'prl']:
                eesnimi = eesnimi.split(' ')[0]
            else:
                eesnimi = eesnimi[0] + '.'
            lyhinimi += ', ' + eesnimi
        return lyhinimi

    @property
    def kirjeldus_lyhike(self):
        return get_kirjeldus_lyhike(self)

    # Kui objectil puudub viide, siis punane
    def colored_id(self):
        if self.viited.exists():
            color = ''
        elif not all(el.kroonika for el in self.artikkel_set.all()):
            color = ''
        else:
            color = 'red'
        return format_html(
            '<strong><span style="color: {};">{}</span></strong>',
            color,
            self.id
        )
    colored_id.short_description = 'ID'

    # @property
    def nimi(self):
        isikunimi = ' '.join(nimi for nimi in [self.eesnimi, self.perenimi] if nimi)
        return isikunimi

    @property
    def lyhinimi(self):
        return repr(self)

    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # # Create a property that returns the markdown instead
    # # Lisame siia ka viited
    # @property
    # def formatted_markdown(self):
    #     sisu = self.kirjeldus
    #     if len(sisu) == 0: # markdownx korrektseks tööks vaja, et sisu ei oleks null
    #         sisu = '<br>'
    #     viite_string = add_markdownx_viited(self)
    #     return markdownify(escape_numberdot(sisu) + viite_string)

    # Create a property that returns the markdown instead
    # Lisame siia ka viited
    @property
    def formatted_markdown(self):
        tekst = self.kirjeldus
        if len(tekst) == 0:  # markdownx korrektseks tööks vaja, et sisu ei oleks null
            tekst = '<br>'
        tekst = add_markdown_objectid(tekst)
        # tekst = add_markdownx_pildid(tekst)
        viite_string = add_markdownx_viited(self)
        # return markdownify(escape_numberdot(tekst) + viite_string)
        markdownified_text = markdownify(escape_numberdot(tekst) + viite_string)
        # Töötleme tekstisisesed pildid NB! pärast morkdownify, muidu viga!
        markdownified_text = add_markdownx_pildid(markdownified_text)
        if viite_string:  # viidete puhul ilmneb markdownx viga
            return fix_markdownified_text(markdownified_text)
        else:
            return markdownified_text

    # Tekstis MarkDown kodeerimiseks
    @property
    def markdown_tag(self):
        return f'[{self.nimi()}] ([isik_{self.id}])'

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('wiki:wiki_isik_detail', kwargs=kwargs)

    # Keywords
    @property
    def keywords(self):
        return object2keywords(self)

    def vanus(self, d=datetime.now()):
        if self.hist_date:
            return d.year - self.dob.year # arvutatakse vastavalt vkj või ukj järgi
        elif self.hist_year:
            return d.year - self.hist_year
        else:
            return None

    # def vanus_ukj(self, d=timezone.now()):
    #     if self.hist_date_ukj:
    #         return d.year - self.hist_date_ukj.year
    #     elif self.hist_year:
    #         return d.year - self.hist_year
    #     else:
    #         return None

    def profiilipilt(self):
        # return Pilt.objects.filter(isikud=self.id, profiilipilt_isik=True).first()
        return Pilt.objects.filter(profiilipilt_isikud=self).first()

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
        ordering = [
            # 'id',
            'perenimi',
            'eesnimi'
        ]
        verbose_name = 'isikud'
        verbose_name_plural = "Isikud"  # kasutame eesti keeles suupärasemaks tegemiseks


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
        help_text='<br>'.join(
            [
                'Tekst (MarkDown on toetatud);',
                'Pildi lisamiseks: [pilt_nnnn];',
                'Viite lisamiseks isikule, asutisele või kohale: nt [Mingi Isik]([isik_nnnn])',
            ]
        )
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
        tekst = add_markdown_objectid(tekst)
        return tekst

    def __repr__(self):
        tekst = str(self.hist_year) + ':' + self.body_text
        tekst = add_markdown_objectid(tekst)
        return tekst

    def colored_id(self):
        if self.kroonika:
            color = 'red'
        else:
            color = ''
        return format_html(
            '<strong><span style="color: {};">{}</span></strong>',
            color,
            self.id
        )
    colored_id.short_description = 'ID'

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
        # ordering = [
        #     'hist_searchdate',
        #     'id'
        # ]
        verbose_name = "Lugu"
        verbose_name_plural = "Lood" # kasutame eesti keeles suupärasemaks tegemiseks

    # Keywords
    @property
    def keywords(self):
        return object2keywords(self)

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
        # return Pilt.objects.filter(
        #     artiklid=self.id,
        #     profiilipilt_artikkel=True
        # ).first()
        # return Pilt.objects.filter(profiilipilt_artklid=self).first()
        return Pilt.objects. \
            filter(profiilipilt_artiklid__in=[self]). \
            first()

    # Kui tekstis on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.body_text

    @property
    def hist_dates_string(self):
        dob = self.dob
        if self.doe:
            doe = self.doe
        else:
            doe = dob
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
    # Lisame siia ka viited
    @property
    def formatted_markdown(self):
        tekst = self.body_text
        tekst = add_markdown_objectid(tekst)
        viite_string = add_markdownx_viited(self)
        markdownified_text = markdownify(escape_numberdot(tekst) + viite_string)
        # Töötleme tekstisisesed pildid NB! pärast morkdownify, muidu viga!
        markdownified_text = add_markdownx_pildid(markdownified_text)
        if viite_string:  # viidete puhul ilmneb markdownx viga
            return fix_markdownified_text(markdownified_text)
        else:
            return markdownified_text

    # Create a property that returns the summary markdown instead
    @property
    def formatted_markdown_summary(self):
        summary = self.body_text
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        return markdownify(escape_numberdot(summary[:100]) + "...")

    @property
    def nimi(self):
        dates = []
        if self.hist_date:
            dates.append(self.dob.strftime('%d.%m.%Y'))
        elif self.hist_month:
            dates.append(f'{self.get_hist_month_display()} {self.hist_year}')
        else:
            dates.append(str(self.hist_year))
        if self.hist_enddate:
            dates.append(self.doe.strftime('%d.%m.%Y'))
        return '-'.join(date for date in dates)

    # Tekstis MarkDown kodeerimiseks
    @property
    def markdown_tag(self):
        return f'[{self.nimi}] ([art_{self.id}])'


class PiltSortedManager(models.Manager):

    # J2rjestame pildid kronoloogiliselt pildi hist_date, hist_year, kui need puuduvad, siis viite hist_date, hist_year
    def sorted(self):
        queryset = self.annotate(
            search_year=Case(
                When(hist_date__isnull=False, then=ExtractYear('hist_date')),
                When(hist_year__isnull=False, then=F('hist_year')),
                When(viited=None, then=0),
                When(viited__hist_date__isnull=False, then=ExtractYear(Max('viited__hist_date'))),
                When(viited__hist_year__isnull=False, then=Max('viited__hist_year')),
                # When(hist_year__isnull=True, then=0),
                output_field=IntegerField()
            ),
            search_month=Case(
                When(hist_date__isnull=False, then=ExtractMonth('hist_date')),
                When(hist_month__isnull=False, then=F('hist_month')),
                When(viited=None, then=0),
                When(viited__hist_date__isnull=False, then=ExtractMonth(Max('viited__hist_date'))),
                # When(hist_month__isnull=True, then=0),
                output_field=IntegerField()
            ),
            search_day=Case(
                When(hist_date__isnull=False, then=ExtractDay('hist_date')),
                When(viited=None, then=0),
                When(viited__hist_date__isnull=False, then=ExtractDay(Max('viited__hist_date'))),
                # When(hist_date__isnull=True, then=0),
                output_field=IntegerField()
            )
        ).order_by(
            'tyyp',
            F('search_year').asc(nulls_last=True),
            'search_month',
            'search_day',
            'id'
        )
        return queryset


class Pilt(models.Model):
    PILT = 'P'
    TEKST = 'T'
    MUU = 'M'
    PILDITYYP = (
        (PILT, 'Pilt'),  # foto, joonistus, skeem
        (TEKST, 'Tekst'), # tekstiskaneering
        (MUU, 'Muu')
    )
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
    tyyp = models.CharField(
        max_length=1,
        choices=PILDITYYP,
        default=TEKST, # 'T'
        help_text='Mis tüüpi pildifail (foto, tekstiskaneering, muu)'
    )
    allikad = models.ManyToManyField(
        Allikas,
        blank=True,
        related_name='pildid',
        verbose_name='Seotud allikad'
    )
    artiklid = models.ManyToManyField(
        Artikkel,
        blank=True,
        related_name='pildid',
        verbose_name='Seotud artiklid'
    )
    isikud = models.ManyToManyField(
        Isik,
        blank=True,
        related_name='pildid',
        verbose_name='Seotud isikud'
    )
    organisatsioonid = models.ManyToManyField(
        Organisatsioon,
        blank=True,
        related_name='pildid',
        verbose_name='Seotud organisatsioonid'
    )
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
        related_name='pildid',
        verbose_name='Seotud objektid'
    )
    # NB! Pildi puhul kasutatakse veebis ainult esimest viidet
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited'
    )
    # Kas näidatakse objecti profiilipildina (pole kasutusel)
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
    # Millistele objectidel kuvatakse profiilipildina (uus lahendus)
    profiilipilt_allikad = models.ManyToManyField(
        Allikas,
        blank=True,
        related_name='profiilipildid',
        verbose_name='Seotud allikad'
    )
    profiilipilt_artiklid = models.ManyToManyField(
        Artikkel,
        blank=True,
        related_name='profiilipildid',
        verbose_name='Seotud artiklid'
    )
    profiilipilt_isikud = models.ManyToManyField(
        Isik,
        blank=True,
        related_name='profiilipildid',
        verbose_name='Seotud isikud'
    )
    profiilipilt_organisatsioonid = models.ManyToManyField(
        Organisatsioon,
        blank=True,
        related_name='profiilipildid',
        verbose_name='Seotud organisatsioonid'
    )
    profiilipilt_objektid = models.ManyToManyField(
        Objekt,
        blank=True,
        related_name='profiilipildid',
        verbose_name='Seotud objektid'
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

    objects = PiltSortedManager()

    def __str__(self):
        return self.nimi

    def __repr__(self):
        return self.nimi

    def caption(self):
        tekst = self.nimi
        kirjeldus = self.kirjeldus
        if kirjeldus:
            tekst = f'{tekst} {kirjeldus}'
        viide = self.viited.first()
        if viide:
            tekst = f'{tekst} (Allikas: {viide})'
        return tekst

    def link(self):
        return self.pilt.url

    # Kui objectil puudub viide, siis punane
    def colored_id(self):
        if self.viited.exists():
            color = ''
        else:
            color = 'red'
        return format_html(
            '<strong><span style="color: {};">{}</span></strong>',
            color,
            self.id
        )

    colored_id.short_description = 'ID'

    # Tekstis MarkDown kodeerimiseks
    def markdown_tag(self):
        return f'[pilt_{self.id}]'

    def image_preview(self):
        if self.pilt_thumbnail:
            return mark_safe('<img src="{0}" width="150" height="150" />'.format(self.pilt_thumbnail.url))
        else:
            return '(No image)'

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


# Kaartide andmed
class Kaart(models.Model):

    nimi = models.CharField(
        'Pealkiri',
        max_length=200,
        help_text='Kaardi pealkiri'
    )
    aasta = models.CharField(
        'Väljaandmise aeg',
        max_length=200,
        unique=True,
        help_text='Väljaandmise aeg'
    )
    kirjeldus = MarkdownxField(
        'Kirjeldus',
        # max_length=200,
        blank=True,
        help_text='Kaardi kirjeldus'
    )
    tiles = models.CharField(  # Kaardi internetiaadress folium leafleti jaoks
        'Internetikaart',
        max_length=100,
        blank=True,
        help_text='Internetikaardi asukoht'
    )
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        verbose_name='Viited',
    )
    # Tehnilised väljad
    inp_date = models.DateTimeField(
        'Lisatud',
        auto_now_add=True,
        blank=True
    )
    mod_date = models.DateTimeField(
        'Muudetud',
        auto_now=True,
        blank=True
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

    def __str__(self):
        return f'{self.aasta} {self.nimi}'

    @property
    def kirjeldus_html(self):
        kirjeldus = '<br>'.join(
            [
                f'<h4>{self.aasta} {self.nimi}</h4>',
                markdownify(escape_numberdot(self.kirjeldus)),
                f'Allikas: {self.viited.first()}'
            ]
        )
        return f'<div class="kaart-tooltip">{kirjeldus}</div>'


    class Meta:
        ordering = ['-aasta']
        verbose_name_plural = "Kaardid"

DEFAULT_MAP = Kaart.objects.filter(aasta=settings.DEFAULT_MAP_AASTA).first()

class Kaardiobjekt(models.Model):
    TYYP = (
        ('H', 'Hoone(d)'),
        ('A', 'Ala'),
        ('M', 'Muu'),
    )
    kaart = models.ForeignKey(
        Kaart,
        on_delete=models.SET_NULL,
        verbose_name='Kaart',
        help_text='Seotud kaart',
        null=True,
        blank=True
    )
    objekt = models.ForeignKey(
        Objekt,
        on_delete=models.SET_NULL,
        verbose_name='Objekt',
        help_text='Seotud objekt',
        # related_name='kaardiobjektid',
        null=True,
        blank=True
    )
    tyyp = models.CharField(
        max_length=1,
        choices=TYYP,
        help_text='Mis liiki kaardiobjekt',
        default='H'
    )
    geometry = models.JSONField(
        'Kaardiobjekt',
        null=True,
        blank=True,
        help_text='Kaardiobjekti GeoJSON-andmed (geometry)'
    )
    zoom = models.SmallIntegerField(
        'Algne kaardi suurendusaste',
        null=True,
        blank=True,
    )
    tn = models.CharField(
        'Tänav',
        max_length=80,
        blank=True,
        help_text='Tänava nimi kaardikihil'
    )
    nr = models.CharField(
        'Majanumber',
        max_length=80,
        blank=True,
        help_text='Maja number kaardikihil'
    )
    lisainfo = models.CharField(
        'Lisainfo',
        max_length=80,
        blank=True,
        help_text='Lisainfo kaardikihil'
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

    def __str__(self):
        return ' '.join([self.kaart.aasta, self.tn, self.nr, self.tyyp, self.lisainfo])

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
        }
        return reverse('wiki:wiki_kaardiobjekt_detail', kwargs=kwargs)

    @property
    def centroid(self, *args, **kwargs):
        try:
            # s = shape(self.geometry).centroid # andis vale tulemuse!
            # print(s.x, s.y, s.wkt)
            # return s # s.x ja s.y kasutamiseks
            s = shape(self.geometry).bounds
            return [
                (s[3]+s[1])/2,
                (s[2]+s[0])/2
            ]
        except:
            pass

    def colored_id(self):
        if not self.objekt:
            color = 'red'
        else:
            color = ''
        return format_html(
            '<strong><span style="color: {};">{}</span></strong>',
            color,
            self.id
        )
    colored_id.short_description = 'ID'

    def get_leaflet(self):
        if self.geometry:
            zoom_start = self.zoom if self.zoom else settings.DEFAULT_MAP_ZOOM_START
            # Loome aluskaardi
            map = folium.Map(
                location=self.centroid, # kaardiobjekt.centroid,  # NB! tagurpidi: [lat, lon],
                zoom_start=zoom_start,
                min_zoom=settings.DEFAULT_MIN_ZOOM,
                zoom_control=True,
                tiles=None,
            )

            map.default_css = settings.LEAFLET_DEFAULT_CSS
            map.default_js = settings.LEAFLET_DEFAULT_JS

            feature_group_kaardiobjekt = folium.FeatureGroup(
                name=f'<span class="kaart-control-layers">{self.kaart.aasta}</span>',
                overlay=False
            )
            folium.TileLayer(
                tiles=self.kaart.tiles,
                attr=f'{self.kaart.__str__()}<br>{self.kaart.viited.first()}',
            ).add_to(feature_group_kaardiobjekt)
            feature_group_kaardiobjekt.add_to(map)

            feature_group_default = folium.FeatureGroup(
                name=f'<span class="kaart-control-layers">{DEFAULT_MAP.aasta}</span>',
                overlay=False
            )
            folium.TileLayer(
                tiles=DEFAULT_MAP.tiles,
                attr=f'{DEFAULT_MAP.__str__()}<br>{DEFAULT_MAP.viited.first()}',
            ).add_to(feature_group_default)
            feature_group_default.add_to(map)

            # lisame vektorkihid
            geometry = self.geometry
            tyyp = self.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
            name = f'{self.__str__()} ({dict(Kaardiobjekt.TYYP)[tyyp].lower()})'
            feature_collection = {
                "type": "FeatureCollection",
                "name": name,
                "features": [geometry]
            }
            style = settings.GEOJSON_STYLE[tyyp]
            f = json.dumps(feature_collection)
            folium.GeoJson(
                f,
                name=name,
                style_function=lambda x: style
            ).add_to(map)

            # Lisame kihtide kontrolli
            folium.LayerControl().add_to(map)

            map_html = map._repr_html_()
            # v2ike h2kk, mis muudab vertikaalset suurust
            map_html = map_html.replace(';padding-bottom:60%;', ';padding-bottom:100%;', 1)
            return mark_safe(map_html)
        else:
            return '(No image)'

    get_leaflet.short_description = 'Leaflet kaart'

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
        }
        return reverse('wiki:wiki_kaardiobjekt_detail', kwargs=kwargs)

    class Meta:
        ordering = ['kaart', 'tn', 'nr']
        verbose_name_plural = "Kaardiobjektid"


#signal used for is_active=False to is_active=True
# @receiver(pre_save, sender=User, dispatch_uid='active')
# def active(sender, instance, **kwargs):
#     if instance.is_active and User.objects.filter(pk=instance.pk, is_active=False).exists():
#         subject = 'Active account'
#         message = '%s your account is now active' %(instance.username)
#         from_email = settings.EMAIL_HOST_USER
#         print('2active', message, from_email)
#         # send_mail(subject, message, from_email, [instance.email], fail_silently=False)

#signal to send an email to the admin when a user creates a new account
@receiver(post_save, sender=User, dispatch_uid='register')
def register(sender, instance, **kwargs):
    if kwargs.get('created', False):
        subject = 'Uus kasutaja: %s' %(instance.username)
        message = 'Uus kasutaja: %s' %(instance.username)
        from_email, to = f'valgalinn.ee <{settings.DEFAULT_FROM_EMAIL}>', 'kalevhark@gmail.com'
        merge_data = {
            'message': message
        }
        html_content = render_to_string('wiki/email/feedback2admin.html', merge_data)
        msg = EmailMultiAlternatives(subject, message, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
