"""
kroonika wiki mudelid.

hist_date: algushetke originaalkuupäev kehtinud kalendri järgi
hist_year: algushetke aasta, kui ainult teada
hist_month: algushetke kuu, kui see on teada
hist_enddate: l6pphetke originaalkuup2ev kehtinud kalendri j2rgi
hist_endyear: l6pphetke aasta, kui ainult teada
dob = vastavalt valikule vkj v6i ukj hist_date j2rgi arvutatud kuup2ev
doe = vastavalt valikule vkj v6i ukj hist_enddate j2rgi arvutatd kuup2ev
"""
from datetime import date, datetime, timedelta
from functools import reduce
from io import BytesIO
import itertools
import json
from operator import or_
import os
import os.path
import re
import string

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
# from django.core.exceptions import FieldDoesNotExist
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import \
    Max, Case, F, When, \
    Value, CharField, DateField, IntegerField
from django.db.models.functions import Cast, Concat, Coalesce, ExtractYear, ExtractMonth, ExtractDay, LPad
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify

import folium

from idna import intranges_contain
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

VIGA_TEKSTIS = settings.KROONIKA['VIGA_TEKSTIS']
PATTERN_OBJECTS = settings.KROONIKA['PATTERN_OBJECTS']
PREDECESSOR_DESCENDANT_NAMES = settings.KROONIKA['PREDECESSOR_DESCENDANT_NAMES']
CALENDAR_SYSTEM_DEFAULT = settings.KROONIKA['CALENDAR_SYSTEM_DEFAULT']


def get_calendarstatus(request) -> str:
    """
    Tagasta kasutaja kalendrisüsteemi valik (vkj/ukj)
    :param request: HttpRequest or None
    :return: calendar_system
    :rtype: str
    """
    if request:
        # kalendrivalik calendar_system='ukj' v6i calendar_system='vkj'
        request.session['calendar_system'] = request.session.get('calendar_system', CALENDAR_SYSTEM_DEFAULT)

        # viimane kalendrivalik 'yyyy-m'
        t2na = timezone.now()
        user_calendar_view_last = date(t2na.year - 100, t2na.month, t2na.day).strftime("%Y-%m")
        request.session['user_calendar_view_last'] = request.session.get('user_calendar_view_last', user_calendar_view_last)
        return request.session.get('calendar_system', CALENDAR_SYSTEM_DEFAULT)
    else:
        return CALENDAR_SYSTEM_DEFAULT


class DaatumitegaManager(models.Manager):
    """
    Manager, mis filtreerib kirjed vastavalt kasutajaõigustele ja lisab objektidele daatumitega seotud abiväljad.
    """

    def daatumitega(self, request=None):
        model_name = self.model.__name__

        # Kontrollime kas kasutaja on autenditud ja admin
        user_is_staff = (request and request.user.is_authenticated and request.user.is_staff)

        # kalendrisüsteemi valik
        calendar_system = get_calendarstatus(request)

        # default queryset from model
        initial_queryset = super().get_queryset()

        # Filtreerime kasutaja järgi
        if model_name == 'Artikkel':
            # Kui andmebaas on Artikkel
            if user_is_staff:
                filtered_queryset = initial_queryset
            else:
                filtered_queryset = initial_queryset.filter(kroonika__isnull=True)
        else:
            # Kui andmebaas on Isik, Organisatsioon, Objekt
            if not user_is_staff:
                artikkel_qs = Artikkel.objects.daatumitega(request)
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
        if calendar_system == 'ukj':  # ukj
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
        filtered_queryset = filtered_queryset.annotate(
            # dobm=Coalesce('dob__month', 'hist_month', 0, output_field=IntegerField()),
            yob=Coalesce('dob__year', 'hist_year', 0, output_field=IntegerField()),
        )
        if model_name == 'Artikkel':
            filtered_queryset = filtered_queryset.annotate(
                search_index=Concat(
                    LPad(
                        Cast(Coalesce('dob__year', 'hist_year', 0), output_field=CharField()),
                        4, fill_text=Value("0")
                    ),
                    LPad(
                        Cast(Coalesce('dob__month', 'hist_month', 0), output_field=CharField()),
                        2, fill_text=Value("0")
                    ),
                    LPad(
                        Cast(Coalesce('dob__day', 0), output_field=CharField()),
                        2, fill_text=Value("0")
                    ),
                    LPad(
                        Cast('id', output_field=CharField()),
                        7, fill_text=Value("0")
                    )
                )
            ).order_by('search_index')
        return filtered_queryset

    def sel_kuul(self, request=None, month=None):
        initial_qs = self.model.objects.daatumitega(request)
        
        sel_kuul_dob = initial_qs.filter(dob__month=month). \
                    values_list('id', flat=True)
        
        sel_kuul_mob = initial_qs.filter(hist_date__isnull=True). \
                    filter(hist_month=month). \
                    values_list('id', flat=True)
        
        if self.model == Artikkel:
            sel_kuul_doe = initial_qs.filter(doe__month=month). \
                    values_list('id', flat=True)
        else:
            sel_kuul_doe = initial_qs.none().values_list('id', flat=True)

        model_ids = reduce(or_, [sel_kuul_dob, sel_kuul_mob, sel_kuul_doe])
        sel_kuul = initial_qs.filter(id__in=model_ids).order_by(ExtractDay('dob'))
        return sel_kuul
    
    def sel_aastal(self, request=None, year=None):
        initial_qs = self.model.objects.daatumitega(request)

        sel_aastal_dob = initial_qs.filter(dob__year=year). \
                values_list('id', flat=True)
        
        sel_aastal_yob = initial_qs.filter(hist_date__isnull=True). \
                filter(hist_year=year). \
                values_list('id', flat=True)
        
        if self.model == Artikkel:
            sel_aastal_doe = initial_qs.filter(doe__year=year). \
                    values_list('id', flat=True)
        else:
            sel_aastal_doe = initial_qs.none().values_list('id', flat=True)
        model_ids = reduce(or_, [sel_aastal_dob, sel_aastal_yob, sel_aastal_doe])
        sel_aastal = initial_qs.filter(id__in=model_ids).order_by(ExtractDay('dob'))
        return sel_aastal
    

class BaasAddUpdateInfoModel(models.Model):
    """
    Tehnilised väljad andmete lisamise/muutmise kohta
    """
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

    class Meta:
        abstract = True


class Allikas(BaasAddUpdateInfoModel):
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

    def __str__(self):
        ilmumise_aasta = ''
        if self.hist_year:
            ilmumise_aasta = f' ({self.hist_year})'
        return self.nimi + ilmumise_aasta

    def __repr__(self):
        return self.nimi

    def profiilipilt(self):
        return Pilt.objects.filter(profiilipilt_allikad=self).first()

    class Meta:
        ordering = ['nimi']
        verbose_name_plural = "Allikad"


class BaasObjectDatesModel(models.Model):
    """
    Object, Viide, Pilt, Kaart daatumid
    """
    hist_date = models.DateField(
        null=True,
        blank=True,
        help_text="kuupäev",
        default=None
    )
    hist_year = models.IntegerField(  # juhuks kui on teada ainult aasta
        null=True,
        blank=True,
        help_text="aasta",
        default=None
    )
    hist_month = models.PositiveSmallIntegerField(  # juhuks kui on teada aasta ja kuu
        null=True,
        blank=True,
        choices=KUUD,
        help_text="kuu",
        default=None
    )
    
    hist_enddate = models.DateField( # juhuks kui lõppaeg on teada
        null=True,
        blank=True,
        help_text="kuupäev",
        default=None
    )
    hist_endyear = models.IntegerField( # juhuks kui on teada ainult aasta
        null=True,
        blank=True,
        help_text='aasta'
    )
    hist_endmonth = models.PositiveSmallIntegerField(  # juhuks kui on teada aasta ja kuu
        null=True,
        blank=True,
        choices=KUUD,
        help_text="kuu",
        default=None
    )

    class Meta:
        abstract = True


class Viide(BaasAddUpdateInfoModel, BaasObjectDatesModel):
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
        if self.peatykk:
            peatykk = self.peatykk
            parts.append(peatykk.strip())
        if self.kohaviit: # kui on füüsiline asukoht
            parts.append(self.kohaviit.strip())
        else: # kui on ainult internetilink
            if self.url:
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
        viide = ', '.join(parts)
        return viide

    @property
    def markdownify(self):
        viide = str(self)
        if self.url:
            return f'<a href="{self.url}">{viide}</a>'
        else:
            return viide


model = Viide
model._meta.get_field('hist_date').verbose_name = "Avaldatud"
model._meta.get_field('hist_year').verbose_name = "Avaldamise aasta"
model._meta.get_field('hist_month').verbose_name = "Avaldamise kuu"
model._meta.get_field('hist_enddate').verbose_name = "Avaldamise lõpu aeg"
model._meta.get_field('hist_endyear').verbose_name= "Avaldamise lõpu aasta"
model._meta.get_field('hist_endmonth').verbose_name = "Avaldamise lõpu kuu"


# map punctuation to space
# Vajalik funktsiooni object2keywords jaoks
translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))

def object2keywords(obj) -> str:
    """
    Moodusta objecti nimest märksõnad
    
    :param obj: wiki model object
    :return: märksõnad
    :rtype: str
    """
    object_string = str(obj)
    translation = re.sub(' +', ' ', object_string.translate(translator))
    words = translation.split(' ')
    keywords = [word for word in words if len(word) > 2]
    return ','.join(settings.KROONIKA['KEYWORDS'] + [object_string] + keywords)


def make_thumbnail(dst_image_field, src_image_field, name_suffix, sep='_') -> None:
    """
    make thumbnail image and field from source image field

    @example
        thumbnail(self.thumbnail, self.image, (200, 200), 'thumb')
    """
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


def add_markdownx_pildid(kirjeldus: str) -> str:
    """Töötleb kirjelduses pilditagid [pilt_nnnn] piltideks"""
    # Otsime kõik pilditagid
    pattern = re.compile(r'\[pilt_([0-9]*)]')
    tagid = re.finditer(pattern, kirjeldus)
    for tag in tagid:
        id = tag.groups()[0]
        pilt = Pilt.objects.get(id=id)
        if pilt:
            pildi_url = pilt.pilt.url
            pildi_caption = pilt.caption()
            img = f'<img src="{pildi_url}" class="pilt-pildidtekstis" alt="{pildi_caption}" data-pilt-id="{pilt.id}" >'
            caption = f'<p><small>{pildi_caption}</small></p>'
            html = f'<div class="w3-row">{img}{caption}</div>'
            kirjeldus = kirjeldus.replace(tag[0], html)
    return kirjeldus


def remove_markdown_tags(obj) -> str:
    """
    Otsi ja eemalda k6ik lingid objectidele ja markdown koodid

    :param obj: wiki model object
    :return: cleaned kirjeldus
    """
    kirjeldus = obj.kirjeldus
    if kirjeldus: # not blank or None
        # eemaldame objecti lingid
        kirjeldus = re.sub(PATTERN_OBJECTS, r'\1', kirjeldus)

        # Otsime kõik pilditagid
        pattern_pildid = re.compile(r'\[pilt_([0-9]*)]')
        tagid = re.finditer(pattern_pildid, kirjeldus)
        for tag in tagid:
            id = tag.groups()[0]
            pilt = Pilt.objects.get(id=id)
            if pilt:
                pildi_caption = pilt.caption()
                kirjeldus = kirjeldus.replace(tag[0], f'Pilt: {pildi_caption}')
        
        # eemaldame viited
        kirjeldus = re.sub(r'\s?\[(viide\_|\^)([0-9]*)]', '', kirjeldus)

        # eemaldame markdown tagid
        kirjeldus = re.sub(r'\*\*(.*?)\*\*', r'\1', kirjeldus)
        kirjeldus = re.sub(r'__(.*?)__', r'\1', kirjeldus)
        
        kirjeldus = re.sub(r'\*(.*?)\*', r'\1', kirjeldus)
        kirjeldus = re.sub(r'_(.*?)_', r'\1', kirjeldus)
        
        kirjeldus = re.sub(r'`(.*?)`', r'\1', kirjeldus)
        
        kirjeldus = re.sub(r'~~(.*?)~~', r'\1', kirjeldus)
        kirjeldus = re.sub(r'###',"", kirjeldus)
    return kirjeldus


def replace_wiki_viited_to_markdown(obj) -> str:
    """
    Asenda wiki viited markdown formaadis viidetega.

    :param obj: wiki model object
    :param kirjeldus: string
    :return: modified kirjeldus
    """
    kirjeldus = obj.kirjeldus
    viited = obj.viited.all()
    if viited:
        viitenr = itertools.count(1)
        translate_viited = {
            f'[viide_{viide.id}]': f'[^{next(viitenr)}]'
            for viide
            in viited
        }
        for translate_viide in translate_viited:
            kirjeldus = kirjeldus.replace(translate_viide, translate_viited[translate_viide])
    return kirjeldus


def make_wiki_viited_list(obj) -> str:
    """
    Moodusta wiki objekti viidetest markdown formaadis viiteloend
    :param obj: wiki model object
    :return: viiteloend markdown formaadis
    :rtype: str
    """
    viited = obj.viited.all()
    viiteplokk = ''
    if viited:
        viitenr = itertools.count(1)
        for viide in viited:
            viiteplokk += f'\n[^{next(viitenr)}]: '
            if viide.url:
                viiteplokk += f'<a class="hover-viide" href="{viide.url}" target="_blank">{viide}</a>'
            else:
                viiteplokk += f'<span>{viide}</span>'
    return viiteplokk


def add_markdownx_viited(obj) -> tuple: 
    """
    Lisa objecti tekstile markdown formaadis viited tekstis ja viiteloendi
    
    :param obj: wiki model object
    :return: (kirjeldus_formatted_markdown, viiteplokk_formatted_markdown)
    :rtype: tuple
    """
    kirjeldus = replace_wiki_viited_to_markdown(obj)
    viiteplokk = make_wiki_viited_list(obj)
    formatted_markdown = markdownify(f'{kirjeldus}{viiteplokk}')
    # jagame kaheks osaks, et saaks kasutada eraldi
    viiteploki_algus = formatted_markdown.find('<div class="footnote">')
    if viiteploki_algus > 0:
        kirjeldus_formatted_markdown = formatted_markdown[:viiteploki_algus]
        viiteplokk_formatted_markdown = formatted_markdown[viiteploki_algus:]
    else:
        kirjeldus_formatted_markdown = formatted_markdown
        viiteplokk_formatted_markdown = ''
    return (kirjeldus_formatted_markdown, viiteplokk_formatted_markdown)


def get_kirjeldus_lyhike(obj) -> str:
    """
    Tagasta lühendatud kirjeldus content tooltipi jaoks

    v6etakse esimene l6ik (reavahetuseni)
    kui esimene lõik on pikem määratud tähtede arvust, siis lühendatakse s6nade kaupa
    :param obj: wiki model object
    :return: lühendatud kirjeldus
    :rtype: str
    """
    # kirjeldus = str(obj.kirjeldus)
    kirjeldus = remove_markdown_tags(obj) # puhastame markdown koodist
    kirjeldus = kirjeldus.splitlines()[0] # v6tame esimese rea kirjeldusest

    if len(kirjeldus) > 100:
        splitid = kirjeldus.split(' ')
        for n in range(len(splitid)):
            kirjeldus = ' '.join(splitid[:n])
            if len(kirjeldus) > 100:
                if len(kirjeldus) < len(str(obj.kirjeldus)):
                    kirjeldus += '...'
                break
    return kirjeldus


def get_object_nimi(obj) -> str:
    """
    Tagasta objecti nimi erinevate objektitüüpide puhul
    :param obj: wiki model object
    :return: object nimi
    :rtype: str
    """
    if isinstance(obj, Artikkel):
        dates = []
        if obj.hist_date:
            dates.append(obj.dob.strftime('%d.%m.%Y'))
        elif obj.hist_month:
            dates.append(f'{obj.get_hist_month_display()} {obj.hist_year}')
        else:
            dates.append(str(obj.hist_year))
        if obj.hist_enddate:
            dates.append(obj.doe.strftime('%d.%m.%Y'))
        return '-'.join(date for date in dates)
    if isinstance(obj, Isik):
        return ' '.join(nimi for nimi in [obj.eesnimi, obj.perenimi] if nimi)
    return str(obj) # kui object nimi


class BaasObjectMixinModel(BaasObjectDatesModel, BaasAddUpdateInfoModel):
    """
    Objecti kirjeldus ja seosed teiste objectidega
    """
    kirjeldus = MarkdownxField(
        'Kirjeldus',
        blank=True,
        help_text='<br>'.join(
            [
                'Tekst (MarkDown on toetatud);',
                'Pildi lisamiseks: [pilt_nnnn];',
                'Viite lisamiseks loole, isikule, asutisele või kohale: nt [Mingi Nimi]([isik_nnnn])',
            ]
        ),
        default=''
    )

    # Viited
    viited = models.ManyToManyField(
        Viide,
        blank=True,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)s",
        verbose_name='Viited',
    )

    # parent objects
    eellased = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Eellased',
        related_name='j2rglane',
        symmetrical=False
    )

    # Vaatamisi
    last_accessed = models.DateTimeField(
        verbose_name='Vaadatud',
        default=timezone.now
    )
    total_accessed = models.PositiveIntegerField(
        verbose_name='Vaatamisi',
        default=0
    )
    
    # show base object dates according ukj/vkj choice
    objects = DaatumitegaManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if self.hist_date:
            self.hist_year = self.hist_date.year
            self.hist_month = self.hist_date.month
        if self.hist_enddate:
            self.hist_endyear = self.hist_enddate.year
            self.hist_endmonth = self.hist_enddate.month
        if isinstance(self, Artikkel):
            # Täidame järjestuseks vajaliku kuupäevavälja olemasolevate põhjal
            if self.hist_date:
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

        # Loome slugi
        if isinstance(self, Artikkel):
            # Loome slugi teksti esimesest 10 sõnast max 200 tähemärki
            value = ' '.join(self.kirjeldus.split(' ')[:10])[:200]
        elif isinstance(self, Isik):
            # Loome slugi isikunimedest
            value = ' '.join(filter(None, [self.eesnimi, self.perenimi]))
        else: # Organisatsioon, Objekt
            value = self.nimi
        self.slug = slugify(value, allow_unicode=True)

        super().save(*args, **kwargs)

    # Keywords
    @property
    def keywords(self):
        return object2keywords(self)

    def get_absolute_url(self):
        model = self.__class__.__name__.lower()
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse(f'wiki:wiki_{model}_detail', kwargs=kwargs)

    def vanus(self, d=datetime.now()):
        if self.hist_date:
            return d.year - self.dob.year
        elif self.hist_year:
            return d.year - self.yob
        else:
            return None

    def profiilipilt(self):
        model = self.__class__.__name__.lower()
        model_filters = {
            'artikkel':       'profiilipilt_artiklid__id',
            'isik':           'profiilipilt_isikud__id',
            'organisatsioon': 'profiilipilt_organisatsioonid__id',
            'objekt':         'profiilipilt_objektid__id',
        }
        filter = {
            model_filters[model]: self.id
        }
        return Pilt.objects.filter(**filter).first()
    
    # Kui kirjelduses on vigase koha märge
    @property
    def vigane(self):
        return VIGA_TEKSTIS in self.kirjeldus if self.kirjeldus else False

    # Create a property that returns the markdown instead
    # @property
    # def formatted_markdown_old(self):
    #     tekst = self.kirjeldus
    #     if len(tekst) == 0:  # markdownx korrektseks tööks vaja, et sisu ei oleks null
    #         tekst = '<br>'
    #     tekst = add_markdown_objectid(self)
    #     viite_string = add_markdownx_viited(self)
    #     # markdownified_text = markdownify(escape_numberdot(tekst) + viite_string)
    #     markdownified_text = markdownify(tekst + viite_string)
    #     # Töötleme tekstisisesed pildid NB! pärast morkdownify, muidu viga!
    #     markdownified_text = add_markdownx_pildid(markdownified_text)
    #     if viite_string: # viidete puhul ilmneb markdownx viga
    #         markdownified_text = fix_markdownified_text(markdownified_text)
    #     return markdownified_text

    # Create a property that returns the markdown instead
    @property
    def formatted_markdown(self):
        kirjeldus_formatted_markdown, _ = add_markdownx_viited(self)
        if len(kirjeldus_formatted_markdown) == 0:  # markdownx korrektseks tööks vaja, et sisu ei oleks null
            kirjeldus_formatted_markdown = '<br>'
        # Töötleme tekstisisesed pildid NB! pärast morkdownify, muidu viga!
        kirjeldus_formatted_markdown = add_markdownx_pildid(kirjeldus_formatted_markdown)
        return kirjeldus_formatted_markdown
    
    # Create a property that returns the reference block in markdown
    @property
    def formatted_markdown_viited(self):
        _, viiteplokk_formatted_markdown = add_markdownx_viited(self)
        # k6rvaldame ülearuse horisontaaleraldaja
        viiteplokk_formatted_markdown = viiteplokk_formatted_markdown.replace('<hr />', '')
        return viiteplokk_formatted_markdown
    
    # Tekstis MarkDown kodeerimiseks
    def markdown_tag(self):
        return f'[{self.nimi}]([{self.__class__.__name__.lower()}_{self.id}])'
    
    @property
    def kirjeldus_lyhike(self):
        return get_kirjeldus_lyhike(self)

    # Kui objectil puudub viide, siis punane
    def colored_id(self):
        if isinstance(self, Artikkel): # TODO: Vaja üle vaadata algoritm
            if self.kroonika:
                color = 'red'
            else:
                color = ''
        else:
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


class Objekt(BaasObjectMixinModel):
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
    objektid = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Kohad'
    )

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

    class Meta:
        ordering = ['slug'] # erimärkidega nimetuste välistamiseks
        verbose_name = 'objektid'
        verbose_name_plural = "Kohad" # kasutame eesti keeles suupärasemaks tegemiseks


model = Objekt
model._meta.get_field('hist_date').verbose_name = "Valmimise aeg"
model._meta.get_field('hist_year').verbose_name = "Valmimise aasta"
model._meta.get_field('hist_month').verbose_name = "Valmimise kuu"
model._meta.get_field('hist_enddate').verbose_name = "Likvideerimise aeg"
model._meta.get_field('hist_endyear').verbose_name= "Likvideerimise aasta"
model._meta.get_field('hist_endmonth').verbose_name = "Likvideerimise kuu"


class Organisatsioon(BaasObjectMixinModel):
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
    gone = models.BooleanField(  # surnud teadmata ajal
        'Lõpetatud/likvideeritud',
        default=False,
        help_text='Lõpetatud/likvideeritud'
    )
    objektid = models.ManyToManyField(
        Objekt,
        blank=True,
    )

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

    class Meta:
        ordering = ['slug'] # erimärkidega nimetuste välistamiseks
        verbose_name = 'organisatsioonid'
        verbose_name_plural = "Asutised" # kasutame eesti keeles suupärasemaks tegemiseks


model = Organisatsioon
model._meta.get_field('hist_date').verbose_name = "Loomise aeg"
model._meta.get_field('hist_year').verbose_name = "Loomise aasta"
model._meta.get_field('hist_month').verbose_name = "Loomise kuu"
model._meta.get_field('hist_enddate').verbose_name = "Lõpetamise aeg"
model._meta.get_field('hist_endyear').verbose_name= "Lõpetamise aasta"
model._meta.get_field('hist_endmonth').verbose_name = "Lõpetamise kuu"


class Isik(BaasObjectMixinModel):
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
    synd_koht = models.CharField(
        'Sünnikoht',
        max_length=100,
        blank=True,
        help_text="Sünnikoht"
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

    # @property
    def nimi(self):
        # isikunimi = ' '.join(nimi for nimi in [self.eesnimi, self.perenimi] if nimi)
        # return isikunimi
        return get_object_nimi(self)

    @property
    def lyhinimi(self):
        return repr(self)

    class Meta:
        ordering = [
            'perenimi',
            'eesnimi'
        ]
        verbose_name = 'isikud'
        verbose_name_plural = "Isikud"  # kasutame eesti keeles suupärasemaks tegemiseks


model = Isik
model._meta.get_field('hist_date').verbose_name = "Sünniaeg"
model._meta.get_field('hist_year').verbose_name = "Sünniaasta"
model._meta.get_field('hist_month').verbose_name = "Sünnikuu"
model._meta.get_field('hist_enddate').verbose_name = "Surma-aeg"
model._meta.get_field('hist_endyear').verbose_name= "Surma-aasta"
model._meta.get_field('hist_endmonth').verbose_name = "Surma-kuu"


class Kroonika(BaasAddUpdateInfoModel):
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

    def __str__(self):
        return self.nimi

    def profiilipilt(self):
        return Pilt.objects.filter(kroonikad=self.id, profiilipilt_kroonika=True).first()

    class Meta:
        verbose_name = "Kroonika"
        verbose_name_plural = "Kroonikad"
 
   
class Artikkel(BaasObjectMixinModel):
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=200,
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
        summary = self.kirjeldus
        if summary:
            summary = remove_markdown_tags(self)
            if summary and summary.find('\n') > 0:
                summary = summary[:summary.find('\n')]
            splits = summary.split(' ')
            tekst = ' '.join(splits[:10]) # 10 esimest sõna
            if len(tekst) < len(self.kirjeldus):
                tekst += '...'
        else:
            tekst = ''
        return tekst

    def __repr__(self):
        tekst = str(self.hist_year) + ':' + self.kirjeldus
        tekst = remove_markdown_tags(self, tekst)
        return tekst
    
    class Meta:
        verbose_name = "Lugu"
        verbose_name_plural = "Lood" # kasutame eesti keeles suupärasemaks tegemiseks
        default_manager_name = "objects"

    
    def headline(self):
        if len(self.kirjeldus) > 50:
            tyhik = self.kirjeldus.find(' ',50,70)
            if tyhik > 0:
                return self.kirjeldus[:tyhik] + '...'
        return self.kirjeldus[:50]
    headline.short_description = 'Lugu'

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

    # Create a property that returns the summary markdown instead
    @property
    def formatted_markdown_summary(self):
        summary = self.kirjeldus
        if summary.find('\n') > 0:
            summary = summary[:summary.find('\n')]
        return markdownify(summary[:100] + "...")

    @property
    def nimi(self):
        return get_object_nimi(self)

model = Artikkel
model._meta.get_field('hist_date').verbose_name = "Toimumise aeg"
model._meta.get_field('hist_year').verbose_name = "Toimumise aasta"
model._meta.get_field('hist_month').verbose_name = "Toimumise kuu"
model._meta.get_field('hist_enddate').verbose_name = "Toimumise lõpuaeg"
model._meta.get_field('hist_endyear').verbose_name= "Toimumise lõpu aasta"
model._meta.get_field('hist_endmonth').verbose_name = "Toimumise lõpu kuu"


class PiltSortedManager(models.Manager):
    """
    J2rjestame pildid kronoloogiliselt pildi hist_date, hist_year, kui need puuduvad, siis viite hist_date, hist_year
    """
    def sorted(self):
        queryset = self.annotate(
            search_year=Case(
                When(hist_date__isnull=False, then=ExtractYear('hist_date')),
                When(hist_year__isnull=False, then=F('hist_year')),
                When(viited=None, then=0),
                When(viited__hist_date__isnull=False, then=ExtractYear(Max('viited__hist_date'))),
                When(viited__hist_year__isnull=False, then=Max('viited__hist_year')),
                output_field=IntegerField()
            ),
            search_month=Case(
                When(hist_date__isnull=False, then=ExtractMonth('hist_date')),
                When(hist_month__isnull=False, then=F('hist_month')),
                When(viited=None, then=0),
                When(viited__hist_date__isnull=False, then=ExtractMonth(Max('viited__hist_date'))),
                output_field=IntegerField()
            ),
            search_day=Case(
                When(hist_date__isnull=False, then=ExtractDay('hist_date')),
                When(viited=None, then=0),
                When(viited__hist_date__isnull=False, then=ExtractDay(Max('viited__hist_date'))),
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


class Pilt(BaasAddUpdateInfoModel, BaasObjectDatesModel):
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
    # Millistele objectidel kuvatakse profiilipildina
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
    
    @property
    def orientation(self):
        return "portree" if self.pilt_height_field/self.pilt_width_field > 0.9 else "postkaart"

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
        help_text='Siia kirjuta vihje parandamiseks/täiendamiseks',
    )
    kontakt = models.CharField(
        'Kontakt',
        help_text='Palun märgi siia oma nimi ja kontaktandmed',
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


class Kaart(BaasAddUpdateInfoModel):
    """
    Kaartide andmed
    """

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

    def __str__(self):
        return f'{self.aasta} {self.nimi}'

    @property
    def kirjeldus_html(self):
        kirjeldus = '<br>'.join(
            [
                f'<h4>{self.aasta} {self.nimi}</h4>',
                markdownify(self.kirjeldus),
                f'Allikas: {self.viited.first()}'
            ]
        )
        return f'<div class="kaart-tooltip">{kirjeldus}</div>'


    class Meta:
        ordering = ['-aasta']
        verbose_name_plural = "Kaardid"


class Kaardiobjekt(BaasAddUpdateInfoModel):
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

    def __str__(self):
        return ' '.join([self.kaart.aasta, self.tn, self.nr, self.tyyp, self.lisainfo])

    @property
    def centroid(self, *args, **kwargs):
        try:
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
            DEFAULT_MAP = Kaart.objects.filter(aasta=settings.DEFAULT_MAP_AASTA).first()
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

