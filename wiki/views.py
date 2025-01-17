import base64
from functools import reduce
import json
import sys
from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta
from io import BytesIO

import logging
logger = logging.getLogger(__name__)

import math
from operator import or_
import os
from pathlib import Path
import pkg_resources
import tempfile
from typing import Dict, Any

from ajax_select.fields import autoselect_fields_check_can_add

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session
from django.contrib.staticfiles import finders
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import \
    Count, Max, Min, \
    Case, F, Func, Q, When, \
    Value, IntegerField, \
    ExpressionWrapper
from django.db.models.functions import Concat, Extract, ExtractYear, ExtractMonth, ExtractDay
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.version import get_version
from django.views import generic
from django.views.generic.dates import ArchiveIndexView, YearArchiveView, MonthArchiveView, DayArchiveView
from django.views.generic.edit import UpdateView

import django_filters
from django_filters.views import FilterView
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from PIL import Image, ImageOps, ImageDraw
import qrcode
import qrcode.image.svg
import requests

from blog.models import Comment
from wiki.models import (
    Allikas, Viide,
    Artikkel, Isik, Objekt, Organisatsioon,
    Pilt,
    Vihje,
    Kaart, Kaardiobjekt
)
from wiki.forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm, KaardiobjektForm
from wiki.forms import VihjeForm, V6rdleFormIsik, V6rdleFormObjekt

from wiki.utils.shp_util import (
    make_objekt_leaflet_combo,
    make_kaardiobjekt_leaflet,
    kaardiobjekt_match_db,
    make_big_maps_leaflet
)

TMP_ALGUSKUVA = Path(tempfile.gettempdir()) / '_valgalinn.ee_algus.tmp'

# Error Handling Templates
def custom_500(request):
    return render(request,'500.html', status=500)

#
# reCAPTCHA kontrollifunktsioon
#
def check_recaptcha(request):
    if settings.DEBUG:
        return True

    data = request.POST
    # get the token submitted in the form
    recaptcha_response = data.get('g-recaptcha-response')
    # captcha verification
    url = f'https://www.google.com/recaptcha/api/siteverify'
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
    payload = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    resp = requests.post(
        url,
        headers=headers,
        data=payload
    )
    result_json = resp.json()
    if result_json.get('success'):
        return True
    else:
        # Päringu teostamise IP aadress
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        logger.warning(f'recaptcha failed: {ip}')
        return False

#
# wiki_base info
#
def wiki_base_info(request):
    user = request.user
    if user.is_authenticated and user.is_staff:
        # Vaatame ainult viimase 24h kandeid
        tagasi24h = timezone.now() - timedelta(days=1)
        feedbacks = Vihje.objects.\
            exclude(end_date__isnull=False).\
            filter(inp_date__gt=tagasi24h).count()
        comments = Comment.objects.filter(inp_date__gt=tagasi24h).count()
    else:
         feedbacks = 0
         comments = 0

    data = {
        'feedbacks': feedbacks,
        'comments': comments,
    }
    return JsonResponse(data)

# cookie consent policy
def privacy(request):
    return render(
        request,
        'wiki/privacy.html',
        {}
    )

#
# Infolehekülg
#
def info(request):
    time = datetime.now()
    time_log = {}
    time_log['0'] = datetime.now() - time
    # Filtreerime kasutaja järgi
    artikkel_qs = Artikkel.objects.daatumitega(request)
    isik_qs = Isik.objects.daatumitega(request)
    organisatsioon_qs = Organisatsioon.objects.daatumitega(request)
    objekt_qs = Objekt.objects.daatumitega(request)

    kaardiobjektiga_objektid_ids = set(
        kaardiobjekt.objekt.id
        for kaardiobjekt
        in Kaardiobjekt.objects.filter(objekt__isnull=False)
    )
    andmebaasid = []
    # Allikad ja viited
    tyhjad_viited = Viide.objects.annotate(
        num_art=Count('wiki_artikkel__id'),
        num_isik=Count('wiki_isik__id'),
        num_org=Count('wiki_organisatsioon__id'),
        num_obj=Count('wiki_objekt__id'),
        num_pilt=Count('pilt__id')
    ).filter(
        num_art=0,
        num_isik=0,
        num_org=0,
        num_obj=0,
        num_pilt=0
    ).count()
    time_log['1'] = datetime.now() - time
    andmebaasid.append(
        ' '.join(
            [
                'Allikad:',
                f'{Allikas.objects.count()} kirjet',
                f'millele viitab: {Viide.objects.count()} (kasutuid {tyhjad_viited}) kirjet',
            ]
        )
    )
    time_log['1a'] = datetime.now() - time
    andmebaasid.append(
        ' '.join(
            [
                'Artikkel: ',
                f'kirjeid {artikkel_qs.count()} ',
                f'viidatud {artikkel_qs.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {artikkel_qs.filter(pildid__isnull=False).distinct().count()} ',
                f'profiilipildiga {artikkel_qs.filter(profiilipildid__isnull=False).distinct().count()} ',
            ]
        )
    )
    time_log['1b'] = datetime.now() - time
    andmebaasid.append(
        ' '.join(
            [
                'Isik: ',
                f'kirjeid {isik_qs.count()} ',
                f'viidatud {isik_qs.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {isik_qs.filter(pildid__isnull=False).distinct().count()} ',
                f'profiilipildiga {isik_qs.filter(profiilipildid__isnull=False).distinct().count()} ',
            ]
        )
    )
    time_log['1c'] = datetime.now() - time
    andmebaasid.append(
        ' '.join(
            [
                'Objekt: ',
                f'kirjeid {objekt_qs.count()} ',
                f'viidatud {objekt_qs.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {objekt_qs.filter(pildid__isnull=False).distinct().count()} ',
                f'profiilipildiga {objekt_qs.filter(profiilipildid__isnull=False).distinct().count()} ',
                f'seotud kaardiga {objekt_qs.filter(id__in=kaardiobjektiga_objektid_ids).count()} '
            ]
        )
    )
    time_log['1d'] = datetime.now() - time
    andmebaasid.append(
        ' '.join(
            [
                'Organisatsioon: ',
                f'kirjeid {organisatsioon_qs.count()} ',
                f'viidatud {organisatsioon_qs.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {organisatsioon_qs.filter(pildid__isnull=False).distinct().count()} ',
                f'profiilipildiga {organisatsioon_qs.filter(profiilipildid__isnull=False).distinct().count()} ',
            ]
        )
    )
    time_log['1e'] = datetime.now() - time
    andmebaasid.append(
        ' '.join(
            [
                'Pilt: ',
                f'kirjeid {Pilt.objects.count()} ',
                f'viidatud {Pilt.objects.filter(viited__isnull=False).distinct().count()} '
            ]
        )
    )
    time_log['2'] = datetime.now() - time
    # Artiklite ülevaade
    andmed = artikkel_qs.aggregate(Count('id'), Min('hist_year'), Max('hist_year'))
    perioodid = artikkel_qs. \
        filter(hist_year__isnull=False). \
        values('hist_searchdate__year', 'hist_searchdate__month'). \
        annotate(ct=Count('id')). \
        order_by('hist_searchdate__year', 'hist_searchdate__month')
    artikleid_kuus = [
        [
            periood['hist_searchdate__year'],
            periood['hist_searchdate__month'],
            periood['ct']
        ] for periood in perioodid
    ]
    if artikleid_kuus:
        artikleid_kuus_max = max([kuu_andmed[2] for kuu_andmed in artikleid_kuus])
    else:
        artikleid_kuus_max = 1 # kui ei ole artikleid sisestatud
    time_log['3'] = datetime.now() - time
    # TODO: Ajutine ümberkorraldamiseks
    revision_data: Dict[str, Any] = {}
    revision_data['kroonika'] = artikkel_qs.\
        filter(kroonika__isnull=False).\
        count()
    revision_data['revised'] = artikkel_qs.\
        filter(kroonika__isnull=False).\
        annotate(num_viited=Count('viited')).\
        filter(num_viited__gt=1)
    time_log['4'] = datetime.now() - time
    revision_data['viiteta'] = artikkel_qs.filter(viited__isnull=True)

    # Koondnäitajad aastate ja kuude kaupa
    a = dict()
    artikleid_aasta_kaupa = artikkel_qs.\
        filter(hist_year__isnull=False).\
        values('hist_year').\
        annotate(Count('hist_year')).\
        order_by('-hist_year')
    a['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa

    time_log['5'] = datetime.now() - time

    # Moodulid, mis kasutusel

    env = dict(
        tuple(str(ws).split())
        for ws
        in pkg_resources.working_set
    )

    model_example = Isik
    model_example_obj = model_example.objects.daatumitega(request).first()

    from .templatetags import wiki_extras
    model_verbose_examples = {
        'model': str(model_example), # Isik
        'model_verbose_name': model_example_obj._meta.verbose_name, # 'isikud'
        'model_verbose_name_plural': model_example_obj._meta.verbose_name_plural, # "Isikud"
        'filter_to_model_name_lower': wiki_extras.to_model_name_lower(model_example_obj), # object.__class__.__name__.lower()
        'filter_get_model_name': wiki_extras.get_model_name(model_example_obj), # str(value.__class__.__name__)
        'simple_tag_model_name_isik': wiki_extras.model_name_isik(), # Isik._meta.verbose_name_plural
        'simple_tag_get_verbose_name': wiki_extras.get_verbose_name(model_example_obj), # object._meta.verbose_name.lower()
        'simple_tag_get_verbose_name_plural': wiki_extras.get_verbose_name_plural(model_example_obj), # object._meta.verbose_name_plural.lower()
    }

    context = {
        'andmebaasid': andmebaasid,
        'andmed': andmed,
        'artikleid_kuus': artikleid_kuus,
        'artikleid_kuus_max': artikleid_kuus_max,
        'session_data': request.session,
        'cookies': request.COOKIES,
        'python': sys.version,
        'env': env,
        'model_verbose_examples': model_verbose_examples,
        'a': a,
        'revision_data': revision_data, # TODO: Ajutine ümberkorraldamiseks
        'time_log': time_log,
    }

    return render(
        request,
        'wiki/info.html',
        context,
    )


#
# Avalehekülje otsing
#
def otsi(request):
    question = request.GET.get('q', '')
    return render(
        request,
        'wiki/wiki_otsi.html',
        {
            'question': question,
            'searchsmallwidgethidden': True,  # ei näita mobiiliotsinguvidinat
        }
    )

#
# Tagasiside vormi töötlemine
#
def feedback(request):
    http_referer = request.META.get('HTTP_REFERER', reverse('algus')) # mis objektilt tuli vihje
    # remote_addr = request.META['REMOTE_ADDR'] # kasutaja IP aadress
    remote_addr = request.META.get('HTTP_X_FORWARDED_FOR', request.META['REMOTE_ADDR']) # kasutaja IP aadress proxy taga
    http_user_agent = request.META.get('HTTP_USER_AGENT', 'unknown') # kasutaja veebilehitseja
    if request.method == 'POST' and check_recaptcha(request):
        # create a form instance and populate it with data from the request:
        form = VihjeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            vihje = {
                'kirjeldus': form.cleaned_data['kirjeldus'],
                'kontakt': form.cleaned_data['kontakt'],
                'http_referer': http_referer,
                'remote_addr': remote_addr,
                'http_user_agent': http_user_agent[:200],
                'django_version': get_version() # Django versioon
            }
            # Salvestame andmed andmebaasi
            v = Vihje(**vihje)
            v.save()
            vihje['inp_date'] = v.inp_date
            # Näitame brauseris
            messages.add_message(request, messages.INFO, 'Tagasiside saadetud.')
            # Saadame meili adminile

            subject = f'Message from valgalinn.ee {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
            message = str(vihje)

            # from django.core.mail import send_mail
            # send_mail(
            #     subject,
            #     message,
            #     'noreply@valgalinn.ee',
            #     ['kalevhark@gmail.com'],
            #     fail_silently=False,
            # )

            from_email, to = f'valgalinn.ee <{settings.DEFAULT_FROM_EMAIL}>', 'kalevhark@gmail.com'
            merge_data = {
                'message': message
            }
            html_content = render_to_string('wiki/email/feedback2admin.html', merge_data)
            msg = EmailMultiAlternatives(subject, message, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            context = {
                'vihje': vihje,
                'searchsmallwidgethidden': True,  # ei näita mobiiliotsinguvidinat
            }
            return render(
                request,
                'wiki/wiki_feedback.html',
                context
            )
        else:
            # Kui on tühi vorm, siis laeme algse lehe
            messages.add_message(request, messages.WARNING, 'Tühja vormi ei saadetud.')
    return HttpResponseRedirect(http_referer)

# Andmebaas Artikkel andmed veebi
def _get_algus_artiklid(request, p2ev, kuu, aasta, artikkel_qs):
    a = dict()
    kirjeid = artikkel_qs.count()
    a['kirjeid'] = kirjeid
    artikleid_max_split = 9 # Kui mitmest artiklist alates teha splittimine (esimesed ... viimased)
    artikleid_max_split_half = artikleid_max_split//2
    a['artikleid_max_split'] = artikleid_max_split
    a['artikleid_max_split_half'] = artikleid_max_split_half
    if kirjeid > 0:
        a['viimane_lisatud'] = artikkel_qs.latest('inp_date')
        a['viimane_muudetud'] = artikkel_qs.latest('mod_date')
        # Samal kuupäeval erinevatel aastatel toimunud
        # sel_p2eval_exactly = artikkel_qs.filter( # hist_date == KKPP
        #     dob__day = p2ev,
        #     dob__month = kuu
        # )
        sel_p2eval = inrange_dates_artikkel(artikkel_qs, p2ev, kuu) # hist_date < KKPP <= hist_enddate
        sel_p2eval_kirjeid = len(sel_p2eval)
        if sel_p2eval_kirjeid > artikleid_max_split: # Kui leiti palju artikleid, teeme splitid
            a['sel_p2eval'] = (
                sel_p2eval[:artikleid_max_split_half] +
                sel_p2eval[int(sel_p2eval_kirjeid/2-1):int(sel_p2eval_kirjeid/2)] +
                sel_p2eval[sel_p2eval_kirjeid-artikleid_max_split_half:]
            )
        else:
            a['sel_p2eval'] = sel_p2eval
        a['sel_p2eval_kirjeid'] = sel_p2eval_kirjeid
        # Samal kuul toimunud TODO: probleem kui dob__month ja doe__month ei ole järjest
        # sel_kuul = artikkel_qs.filter(Q(dob__month=kuu) | Q(hist_month=kuu) | Q(doe__month=kuu))
        # sel_kuul_dob = artikkel_qs.filter(dob__month=kuu). \
        #             values_list('id', flat=True)
        # sel_kuul_mob = artikkel_qs.exclude(dob__isnull=True). \
        #             filter(dob__month=kuu). \
        #             values_list('id', flat=True)
        # sel_kuul_doe = artikkel_qs.filter(doe__month=kuu). \
        #             values_list('id', flat=True)
        # model_ids = reduce(or_, [sel_kuul_dob, sel_kuul_mob, sel_kuul_doe])
        # sel_kuul = artikkel_qs.filter(id__in=model_ids)
        sel_kuul = Artikkel.objects.sel_kuul(request, kuu)
        sel_kuul_kirjeid = len(sel_kuul)
        if sel_kuul_kirjeid > artikleid_max_split: # Kui leiti rohkem kui 9 kirjet võetakse 4 algusest + 1 keskelt + 4 lõpust
            a['sel_kuul'] = (
                sel_kuul[:artikleid_max_split_half] +
                sel_kuul[int(sel_kuul_kirjeid/2-1):int(sel_kuul_kirjeid/2)] +
                sel_kuul[sel_kuul_kirjeid-artikleid_max_split_half:]
            )
        else:
            a['sel_kuul'] = sel_kuul
        a['sel_kuul_kirjeid'] = sel_kuul_kirjeid
        # sada aastat tagasi toimunud
        # a['sada_aastat_tagasi'] = sel_p2eval_exactly.filter(dob__year = (aasta-100))
        a['sada_aastat_tagasi'] = sel_p2eval.filter(dob__year=(aasta - 100))
        a['loetumad'] = artikkel_qs.order_by('-total_accessed')[:40] # 40 loetumat artiklit
        # Koondnäitajad aastate ja kuude kaupa
        artikleid_aasta_kaupa = artikkel_qs.\
            values('hist_year').\
            annotate(Count('hist_year')).\
            order_by('hist_year')
        a['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa
        artikleid_kuu_kaupa = artikkel_qs.\
            values('hist_year', 'hist_month').\
            annotate(Count('hist_month')).\
            order_by('hist_year', 'hist_month')
        a['artikleid_kuu_kaupa'] = artikleid_kuu_kaupa
    return a

# Andmebaas Isik andmed veebi
def _get_algus_isikud(request, p2ev, kuu, aasta):
    a = dict()
    isik_qs = Isik.objects.daatumitega(request)
    kirjeid = isik_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = isik_qs.latest('inp_date')
        a['viimane_muudetud'] = isik_qs.latest('mod_date')
        a['sada_aastat_tagasi'] = isik_qs.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        a['sel_p2eval'] = isik_qs.filter(
            dob__day=p2ev,
            dob__month=kuu
        ).order_by('hist_year')
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        # a['sel_kuul'] = isik_qs. \
        #     filter(dob__month=kuu). \
        #     order_by(ExtractDay('dob'))
        a['sel_kuul'] = Isik.objects.sel_kuul(request, kuu)
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        a['sel_p2eval_surnud'] = isik_qs.filter(
            doe__day=p2ev,
            doe__month=kuu
        )
        a['sel_p2eval_surnud_kirjeid'] = len(a['sel_p2eval_surnud'])
        a['sel_kuul_surnud'] = isik_qs. \
            filter(doe__month=kuu). \
            order_by(ExtractDay('doe'))
        a['sel_kuul_surnud_kirjeid'] = len(a['sel_kuul_surnud'])
        juubilarid = get_juubilarid(isik_qs)
        a['juubilarid'] = juubilarid
    return a

# Andmebaas Organisatsioon andmed veebi
def _get_algus_organisatsioonid(request, p2ev, kuu, aasta):
    a = dict()
    organisatsioon_qs = Organisatsioon.objects.daatumitega(request)
    kirjeid = organisatsioon_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = organisatsioon_qs.latest('inp_date')
        a['viimane_muudetud'] = organisatsioon_qs.latest('mod_date')
        a['sada_aastat_tagasi'] = organisatsioon_qs.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        a['sel_p2eval'] = organisatsioon_qs.filter(
            dob__day=p2ev,
            dob__month=kuu
        ).order_by('hist_year')
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        # a['sel_kuul'] = organisatsioon_qs. \
        #     filter(dob__month=kuu). \
        #     order_by(ExtractDay('dob'))
        # sel_kuul_dob = organisatsioon_qs.filter(dob__month=kuu). \
        #             values_list('id', flat=True)
        # sel_kuul_mob = organisatsioon_qs.exclude(dob__isnull=True). \
        #             filter(dob__month=kuu). \
        #             values_list('id', flat=True)
        # sel_kuul_doe = organisatsioon_qs.filter(doe__month=kuu). \
        #             values_list('id', flat=True)
        # model_ids = reduce(or_, [sel_kuul_dob, sel_kuul_mob, sel_kuul_doe])
        # a['sel_kuul'] = organisatsioon_qs.filter(id__in=model_ids)
        a['sel_kuul'] = Organisatsioon.objects.sel_kuul(request, kuu)
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = get_juubilarid(organisatsioon_qs)
        a['juubilarid'] = juubilarid
    return a

# Andmebaas Objekt andmed veebi
def _get_algus_objektid(request, p2ev, kuu, aasta):
    a = dict()
    objekt_qs = Objekt.objects.daatumitega(request)
    kirjeid = objekt_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = objekt_qs.latest('inp_date')
        a['viimane_muudetud'] = objekt_qs.latest('mod_date')
        a['sada_aastat_tagasi'] = objekt_qs.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        a['sel_p2eval'] = objekt_qs.filter(
            dob__day = p2ev,
            dob__month = kuu
        ).order_by('hist_year')
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        # a['sel_kuul'] = objekt_qs.\
        #     filter(dob__month = kuu).\
        #     order_by(ExtractDay('dob'))
        # sel_kuul_dob = objekt_qs.filter(dob__month=kuu). \
        #             values_list('id', flat=True)
        # sel_kuul_mob = objekt_qs.exclude(dob__isnull=True). \
        #             filter(dob__month=kuu). \
        #             values_list('id', flat=True)
        # sel_kuul_doe = objekt_qs.filter(doe__month=kuu). \
        #             values_list('id', flat=True)
        # model_ids = reduce(or_, [sel_kuul_dob, sel_kuul_mob, sel_kuul_doe])
        # a['sel_kuul'] = objekt_qs.filter(id__in=model_ids)
        a['sel_kuul'] = Objekt.objects.sel_kuul(request, kuu)
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = get_juubilarid(objekt_qs)
        a['juubilarid'] = juubilarid
    return a

# Andmebaas Kaart andmed veebi
def _get_algus_kaart(request):
    a = dict()
    z, x, y = 15, 18753, 9907  # näitamiseks valitud kaarditükk
    qs = Kaart.objects \
        .filter(tiles__contains='tiles') \
        .annotate(sample_tile=F('tiles')) \
        .order_by('aasta')
    qs = qs.annotate(
        sample_tile=Func(
            F('sample_tile'),
            Value('{z}'), Value(str(z)),
            function='replace',
        )
    )
    qs = qs.annotate(
        sample_tile=Func(
            F('sample_tile'),
            Value('{x}'), Value(str(x)),
            function='replace',
        )
    )
    qs = qs.annotate(
        sample_tile=Func(
            F('sample_tile'),
            Value('{y}'), Value(str(y)),
            function='replace',
        )
    )
    kirjeid = qs.count()
    a['kirjeid'] = kirjeid
    a['kaardid'] = qs
    return a

# Millistel kuude kohta valitud aastal on kirjeid
def get_algus_kalender(request, artikkel_qs):
    years_with_events_set = set(
        artikkel_qs. \
            exclude(hist_date__isnull=True). \
            values_list('hist_year', flat=True)
    )
    years_with_events = [day for day in years_with_events_set]
    kalender = {
        'calendar_days_with_events_in_month_url': reverse('wiki:calendar_days_with_events_in_month'),
        'years_with_events': years_with_events
    }
    return kalender

#
# Avakuva rendertamine
#
def _get_algus(request):
    # Filtreerime artiklite hulga kasutaja järgi
    artikkel_qs = Artikkel.objects.daatumitega(request)
    andmed = {} # Selle muutuja saadame veebi
    p2ev = date.today().day # str(p2ev).zfill(2) -> PP
    kuu = date.today().month # str(kuu).zfill(2) -> KK
    aasta = date.today().year

    andmed['artikkel'] = _get_algus_artiklid(request, p2ev, kuu, aasta, artikkel_qs)
    andmed['isik'] = _get_algus_isikud(request, p2ev, kuu, aasta)
    andmed['organisatsioon'] = _get_algus_organisatsioonid(request, p2ev, kuu, aasta)
    andmed['objekt'] = _get_algus_objektid(request, p2ev, kuu, aasta)
    andmed['kaart'] = _get_algus_kaart(request)

    kalender = get_algus_kalender(request, artikkel_qs)

    # Kas on sada aastat tagasi toimunud asju?
    andmed['sada_aastat_tagasi'] = any(
        [
            andmed['artikkel']['sada_aastat_tagasi'],
            andmed['isik']['sada_aastat_tagasi'],
            andmed['organisatsioon']['sada_aastat_tagasi'],
            andmed['objekt']['sada_aastat_tagasi'],
        ]
    )

    # response = render(
    #     request, 'wiki/algus.html',
    #     {
    #         'kalender': kalender,
    #         'andmed': andmed,
    #     }
    # )
    response_content = render_to_string(
        'wiki/algus.html',
        {
            'kalender': kalender,
            'andmed': andmed,
            'j6ul2024': settings.J6UL2024
        },
        request,
    )
    if settings.TMP_ALGUSKUVA_CACHE and isinstance(request.user, AnonymousUser):
        with open(TMP_ALGUSKUVA, 'w', encoding='utf-8') as f:
            f.write(response_content)
    # Lisame kylastuste loenduri
    # visits = int(request.COOKIES.get('visits', '0'))
    # if request.COOKIES.get('last_visit'):
    #     last_visit = request.COOKIES['last_visit']
    #     # the cookie is a string - convert back to a datetime type
    #     last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")
    #     curr_time = datetime.now()
    #     if (curr_time - last_visit_time).days > 0:
    #         # if at least one day has gone by then inc the visit count.
    #         response.set_cookie('visits', visits + 1)
    #         response.set_cookie('last_visit', datetime.now())
    # else:
    #     response.set_cookie('last_visit', datetime.now())
    return response_content

# Avakuva
def algus(request):
    # salvestame valitud kalendrisysteemi j2rgi
    calendar_system = request.session.get("calendar_system")
    tmpfile = f'{calendar_system}_{TMP_ALGUSKUVA}'

    if all(
        [
            settings.TMP_ALGUSKUVA_CACHE,
            os.path.isfile(tmpfile),
            isinstance(request.user, AnonymousUser)
        ]
    ):
        filestat = os.stat(tmpfile)
        now = datetime.now()
        if now.timestamp() - filestat.st_mtime < 60: # vähem kui minut vana avakuva salvestus
            with open(tmpfile, 'r', encoding='utf-8') as f:
                response_content = f.read()
            return HttpResponse(response_content)

    response_content = _get_algus(request)
    return HttpResponse(response_content)

#
# Tagastab kõik artiklid, kus hist_date < KKPP <= hist_enddate vahemikus
#
def inrange_dates_artikkel(qs, p2ev, kuu):
    q = qs.filter(hist_date__isnull=False) # Vaatleme ainult algusajaga ridasid
    kkpp_string = str(kuu).zfill(2)+str(p2ev).zfill(2)
    id_list = [art.id for art in q if kkpp_string in art.hist_dates_string]
    return qs.filter(id__in=id_list) # queryset

def user_is_staff_check(user):
    return user.is_staff

#
# Objectide v6rdlemiseks
#
@login_required
@user_passes_test(user_is_staff_check)
def v6rdle(request, model='isik'):
    if model not in ['isik', 'objekt']:
        raise Http404('Sellist lehte ei ole')
    vasak_object = request.GET.get('vasak_object')
    parem_object = request.GET.get('parem_object')
    initial_dict = {
        "vasak_object": vasak_object,
        "parem_object": parem_object,
    }
    if model == 'isik':
        form = V6rdleFormIsik(request.GET, initial=initial_dict)
    elif model == 'objekt':
        form = V6rdleFormObjekt(request.GET, initial=initial_dict)
    else:
        raise Http404('Sellist lehte ei ole')

    return render(
        request,
        'wiki/wiki_v6rdle.html',
        {
            'form': form,
            'model': model,
            'vasak_object_id': vasak_object,
            'parem_object_id': parem_object
        }
    )

# objectide nimel hiirega peatudes infoakna kuvamiseks
def get_v6rdle_object(request):
    model_name = request.GET.get('model_name')
    id = request.GET.get('obj_id')
    model = apps.get_model('wiki', model_name)
    object = model.objects.daatumitega(request).get(id=id)

    # Objectiga seotud artiklid
    artikkel_qs = Artikkel.objects.daatumitega(request)
    model_filters = {
        'isik':           'isikud__id',
        'organisatsioon': 'organisatsioonid__id',
        'objekt':         'objektid__id'
    }
    filter = {
        model_filters[model_name]: id
    }
    seotud_artiklid = artikkel_qs.filter(**filter)

    return render(
        request,
        f'wiki/wiki_v6rdle_{model_name.lower()}.html',
        {
            'object': object,
            'seotud_artiklid': seotud_artiklid
        }
    )


#
# Funktsioon duplikaatkirjete koondamiseks
# Kasutamine:
# python manage.py shell
# from wiki.views import update_object_with_object as join
# join('andmebaas', kirje_id_kust_kopeerida, kirje_id_kuhu_kopeerida)
#
def update_object_with_object(model_name='', source_id='', dest_id=''):
    model = apps.get_model('wiki', model_name)

    # Doonorobjekt
    old = model.objects.get(id=source_id)
    print(f'Doonorobjekt: {old.id} {old}')

    # Sihtobjekt
    new = model.objects.get(id=dest_id)
    print(f'Sihtobjekt: {new.id} {new}')

    # Kirjeldus
    sep = '\n\n+++\n\n'
    if old.kirjeldus:
        if new.kirjeldus:
            uus_kirjeldus = sep.join([new.kirjeldus, old.kirjeldus])
        else:
            uus_kirjeldus = old.kirjeldus
        new.kirjeldus = uus_kirjeldus

    # Daatumid
    if old.hist_date:
        if new.hist_date == None:
            new.hist_date = old.hist_date
    else:
        if old.hist_year:
            if not new.hist_year:
                new.hist_year = old.hist_year
    if old.hist_enddate:
        if not new.hist_enddate:
            new.hist_enddate = old.hist_enddate
    else:
        if old.hist_endyear:
            if not new.hist_endyear:
                new.hist_endyear = old.hist_endyear

    # Seotud viited
    viited = old.viited.all()
    print('Viited:')
    for viide in viited:
        print(viide.id, viide)
        new.viited.add(viide)

    # Seotud eellased
    eellased = old.eellased.all()
    print('Eellased:')
    for eellane in eellased:
        print(eellane.id, eellane)
        new.eellased.add(eellane)

    # Surnud/Likvideeritud
    if model in [Isik, Organisatsioon, Objekt]:
        if old.gone:
            new.gone = old.gone
    # Seotud andmebaasid ja parameetrid
    if model == Isik:
        if old.synd_koht:
            if not new.synd_koht:
                print(old.synd_koht)
                new.synd_koht = old.synd_koht
        if old.surm_koht:
            if not new.surm_koht:
                print(old.surm_koht)
                new.surm_koht = old.surm_koht
        if old.maetud:
            if not new.maetud:
                print(old.maetud)
                new.maetud = old.maetud

        print('Artiklid:')
        artiklid = Artikkel.objects.filter(isikud=old)
        for art in artiklid:
            print(art.id, art)
            art.isikud.add(new)
            # art.isikud.remove(old)
        print('Organisatsioonid:')
        organisatsioonid = old.organisatsioonid.all()
        for organisatsioon in organisatsioonid:
            print(organisatsioon.id, organisatsioon)
            new.organisatsioonid.add(organisatsioon)
        print('Objektid:')
        objektid = old.objektid.all()
        for objekt in objektid:
            print(objekt.id, objekt)
            new.objektid.add(objekt)
        print('Pildid:')
        pildid = Pilt.objects.filter(isikud=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.isikud.add(new)
            # pilt.isikud.remove(old)
        print('Profiilipildid:')
        pildid = Pilt.objects.filter(profiilipilt_isikud=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.profiilipilt_isikud.add(new)
    elif model == Organisatsioon:
        if not old.hist_date:
            if old.hist_month:
                if not new.month:
                    print(old.month)
                    new.month = old.month
        print('Artiklid:')
        artiklid = Artikkel.objects.filter(organisatsioonid=old)
        for art in artiklid:
            print(art.id, art)
            art.organisatsioonid.add(new)
        print('Objektid:')
        objektid = old.objektid.all()
        for objekt in objektid:
            print(objekt.id, objekt)
            new.objektid.add(objekt)
        print('Pildid:')
        pildid = Pilt.objects.filter(organisatsioonid=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.organisatsioonid.add(new)
        print('Profiilipildid:')
        pildid = Pilt.objects.filter(profiilipilt_organisatsioonid=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.profiilipilt_organisatsioonid.add(new)
    elif model == Objekt:
        if not old.hist_date:
            if old.hist_month:
                if not new.month:
                    print(old.month)
                    new.month = old.month
        if old.asukoht:
            print(old.asukoht)
            if new.asukoht:
                uus_asukoht = ' +++ '.join([new.asukoht, old.asukoht])
            else:
                uus_asukoht = old.asukoht
            new.asukoht = uus_asukoht
        print('Artiklid:')
        artiklid = Artikkel.objects.filter(objektid=old)
        for art in artiklid:
            print(art.id, art)
            art.objektid.add(new)
        print('Objektid:')
        objektid = old.objektid.all()
        for objekt in objektid:
            if objekt != old:
                print(objekt.id, objekt)
                new.objektid.add(objekt)
        print('Pildid:')
        pildid = Pilt.objects.filter(objektid=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.objektid.add(new)
        print('Pildid:')
        pildid = Pilt.objects.filter(profiilipilt_objektid=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.profiilipilt_objektid.add(new)
        print('Kaardiobjektid:')
        kaardiobjektid = Kaardiobjekt.objects.filter(objekt=old)
        for kaardiobjekt in kaardiobjektid:
            print(kaardiobjekt.id, kaardiobjekt)
            kaardiobjekt.objekt = new
            kaardiobjekt.save(update_fields=['objekt'])
    # Salvestame muudatused
    new.save()
    print(f'Uuendati objecti: {new} (id={new.id})')
    return new.id

def get_update_object_with_object(request):
    if request and request.user.is_authenticated and request.user.is_staff:
        model_name = request.GET.get('model_name')
        source_id = request.GET.get('src_id')
        dest_id = request.GET.get('dst_id')
        # print(model_name, source_id, dest_id)
        updated_object = update_object_with_object(
            model_name=model_name,
            source_id=source_id,
            dest_id=dest_id
        )
        return JsonResponse(updated_object, safe=False)
    else:
        raise PermissionDenied

#
# Kuupäeva väljalt võetud andmete põhjal suunatakse kuupäevavaatesse
#
def mine_krono_kp(request):
    if request.method == 'POST' and check_recaptcha(request):
        try:
            kuup2ev = request.POST.get('kuup2ev').split('-')
            return HttpResponseRedirect(
                reverse(
                    'wiki:artikkel_day_archive',
                    kwargs={'year': kuup2ev[0], 'month': kuup2ev[1], 'day': kuup2ev[2]})
                )
        except:
            pass
    return HttpResponseBadRequest("Kuupäev valimata.")
#
# Kuupäeva väljalt võetud andmete põhjal suunatakse kuuvaatesse
#
def mine_krono_kuu(request):
    # http_referer = request.META['HTTP_REFERER']  # mis objektilt tuli päring
    if request.method == 'POST' and check_recaptcha(request):
        try:
            year = request.POST.get('year')
            month = request.POST.get('month')
            return HttpResponseRedirect(
                reverse(
                    'wiki:artikkel_month_archive',
                    kwargs={
                        'year': year,
                        'month': month
                    }
                )
            )
        except:
            pass
    return HttpResponseBadRequest("Aasta ja kuu valimata.")

#
# Kuupäeva väljalt võetud andmete põhjal suunatakse aastavaatesse
#
# def mine_krono_aasta(request):
#     url = request.META['HTTP_REFERER']  # mis objektilt tuli päring
#     if request.method == 'POST': # and check_recaptcha(request):
#         year = request.POST.get('year')
#         month = request.POST.get('month')
#         url = reverse(
#             'wiki:artikkel_year_archive',
#             kwargs={
#                 'year': year,
#                 # 'month': month
#             }
#         )
#     return HttpResponseRedirect(url)

def mis_kuul(kuu, l6pp='s'):
    kuud = ['jaanuari',
            'veebruari',
            'märtsi',
            'aprilli',
            'mai',
            'juuni',
            'juuli',
            'augusti',
            'septembri',
            'oktoobri',
            'novembri',
            'detsembri'
            ]
    return kuud[kuu - 1] + l6pp

def get_mainitud_aastatel(qs, model, obj):
    # Artiklites mainimine läbi aastate
    if model == 'Isik':
        qs = qs.filter(isikud__id=obj.id)
    elif model == 'Objekt':
        qs = qs.filter(objektid__id=obj.id)
    elif model == 'Organisatsioon':
        qs = qs.filter(organisatsioonid__id=obj.id)

    aastad = list(qs.values_list('hist_year', flat=True).distinct())
    synniaasta = obj.dob.year if obj.dob else obj.hist_year
    if synniaasta:
        aastad.append(synniaasta)
    surmaaasta = obj.doe.year if obj.doe else obj.hist_endyear
    if surmaaasta:
        aastad.append(surmaaasta)
    aastad = Counter(aastad)  # loetleme kõik aastad ja mainimised

    return dict(
        OrderedDict(
            sorted(
                aastad.items(), key=lambda t: t[0]
            )
        )
    )

def get_mainitud_aastatel_chart(mainitud_aastatel_data):
    graph = ''
    if len(mainitud_aastatel_data) > 0:
        plt.switch_backend('AGG')
        font_ttf_file = settings.DEFAULT_FONT # "wiki/css/fonts/Raleway/Raleway-Regular.ttf"
        fpath = Path(settings.STATIC_ROOT / font_ttf_file)
        if not fpath.is_file(): # kui on DEV versioon
            stores = finders.AppDirectoriesFinder(app_names={'wiki'}).storages
            fpath = Path(stores["wiki"].path(font_ttf_file))
        fig, ax = plt.subplots(figsize=(5, 2))
        # ax.set_title(f'This is a special font: {fpath.name}', font=fpath)
        # ax.set_xlabel('This is the default font')
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        plt.bar(
            list(mainitud_aastatel_data.keys()), mainitud_aastatel_data.values(),
            color='g'
        )
        mainitud_aastatel = [int(aasta) for aasta in mainitud_aastatel_data.keys()]
        max_aasta = max(mainitud_aastatel)
        min_aasta = min(mainitud_aastatel)
        if max_aasta-min_aasta < 3:
            plt.xticks(range(min_aasta-2, max_aasta+3, 1), font=fpath)
        else:
            plt.xticks(font=fpath)
        max_mainimisi = max(mainitud_aastatel_data.values()) + 1
        step_mainimisi = math.ceil(max_mainimisi / 10)
        plt.yticks(range(1, max_mainimisi, step_mainimisi), font=fpath)
        # Pildi salvestamine baidijadana
        buffer = BytesIO()
        plt.savefig(buffer, format='png', transparent=True, bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        graph = base64.b64encode(image_png)
        graph = graph.decode('utf-8')
        buffer.close()
    return graph

def seotud_artiklikaudu(request, model, seotud_artiklid, object_self):
    queryset = model.objects.daatumitega(request)
    objects = queryset. \
        filter(artikkel__pk__in=seotud_artiklid). \
        distinct(). \
        exclude(pk=object_self)
    andmed = {}
    for seotud_object in objects:
        kirje = {}
        kirje['id'] = seotud_object.id
        kirje['slug'] = seotud_object.slug
        kirje['nimi'] = seotud_object
        # kirje['perenimi'] = seotud_isik.perenimi
        # kirje['eesnimi'] = seotud_isik.eesnimi
        if model.__name__ == 'Isik':
            filter_map = {'isikud': seotud_object}
        if model.__name__ == 'Organisatsioon':
            filter_map = {'organisatsioonid': seotud_object}
        if model.__name__ == 'Objekt':
            filter_map = {'objektid': seotud_object}
        kirje['artiklid'] = seotud_artiklid. \
            filter(**filter_map). \
            values(
            'id', 'slug',
            'kirjeldus',
            'hist_date', 'dob', 'hist_year', 'hist_month',
            'hist_enddate', 'doe'
        )
        andmed[seotud_object.id] = kirje
    return andmed

from wiki.models import PREDECESSOR_DESCENDANT_NAMES
# Lisame detailview jaoks contexti eellase ja j2rglase info
# sisendiks on object
def add_eellased_j2rglane2context(object, context):
    qs = object.get_queryset()
    model_name = str(qs.model.__name__)
    eellased = object.object.eellased.all()
    eellased_qs = qs.filter(id__in=[obj.id for obj in eellased])
    if len(eellased_qs) > 1:
        eellased_label = PREDECESSOR_DESCENDANT_NAMES[model_name]['predecessor_name_plural']
    else:
        eellased_label = PREDECESSOR_DESCENDANT_NAMES[model_name]['predecessor_name']
    j2rglane = object.object.j2rglane.all()
    j2rglane_qs = qs.filter(id__in=[obj.id for obj in j2rglane])
    if len(j2rglane_qs) > 1:
        j2rglane_label = PREDECESSOR_DESCENDANT_NAMES[model_name]['descendant_name_plural']
    else:
        j2rglane_label = PREDECESSOR_DESCENDANT_NAMES[model_name]['descendant_name']
    context['eellased'] = {
        'qs': eellased_qs,
        'label': eellased_label
    }
    context['j2rglane'] = {
        'qs': j2rglane_qs,
        'label': j2rglane_label
    }
    return context

#
# Artikli vaatamiseks
#
class ArtikkelDetailView(generic.DetailView):
    model = Artikkel
    query_pk_and_slug = True
    template_name = 'wiki/artikkel_detail.html'

    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

    def get_object(self, **kwargs):
        obj = super().get_object()
        # Record the last accessed date
        obj.last_accessed = timezone.now()
        obj.total_accessed += 1
        obj.save(update_fields=['last_accessed', 'total_accessed'])
        return obj

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)

        # Kas artiklile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.\
            filter(profiilipilt_artiklid__in=[self.object]).\
            first()
        # Seotud objectid
        seotud_isikud = Isik.objects.daatumitega(self.request).filter(
            artikkel=self.object
        )
        context['seotud_isikud'] = seotud_isikud
        seotud_organisatsioonid = Organisatsioon.objects.daatumitega(self.request).filter(
            artikkel=self.object
        )
        context['seotud_organisatsioonid'] = seotud_organisatsioonid
        seotud_objektid = Objekt.objects.daatumitega(self.request).filter(
            artikkel=self.object
        )
        context['seotud_objektid'] = seotud_objektid
        seotud_pildid = Pilt.objects.sorted(). \
            filter(artiklid=self.object)
        context['seotud_pildid'] = seotud_pildid

        # Kas artiklit klikitakse mingi objecti vaatest
        # queryprms = self.request.GET.dict()
        # filter_isik_id = queryprms.get('isik')
        # filter_organisatsioon_id = queryprms.get('organisatsioon')
        # filter_objekt_id = queryprms.get('objekt')
        # print(filter_isik_id, filter_organisatsioon_id, filter_objekt_id)
        queryparams = QueryDict(mutable=True)
        for query_object in ['isik', 'organisatsioon', 'objekt']:
            filter_object_id = self.request.GET.get(query_object)
            if filter_object_id:
                model = apps.get_model('wiki', query_object)
                try:
                    filter_object = model.objects.daatumitega(self.request).get(id=filter_object_id)
                    if model == Isik and filter_object in seotud_isikud:
                        artikkel_qs = artikkel_qs.filter(isikud__in=[filter_object])
                        context[f'filter_{query_object}'] = filter_object
                        queryparams[query_object] = filter_object_id
                    if model == Organisatsioon and filter_object in seotud_organisatsioonid:
                        artikkel_qs = artikkel_qs.filter(organisatsioonid__in=[filter_object])
                        context[f'filter_{query_object}'] = filter_object
                        queryparams[query_object] = filter_object_id
                    if model == Objekt and filter_object in seotud_objektid:
                        artikkel_qs = artikkel_qs.filter(objektid__in=[filter_object])
                        context[f'filter_{query_object}'] = filter_object
                        queryparams[query_object] = filter_object_id
                except:
                    pass
        if queryparams:
            context['queryparams'] = '?'+queryparams.urlencode()

        # Järjestame artiklid kronoloogiliselt
        loend = list(artikkel_qs.values_list('id', flat=True))
        # Leiame valitud artikli järjekorranumbri
        n = loend.index(self.object.id)
        context['n'] = n
        if n > -1:
            # Leiame ajaliselt järgneva artikli
            if n < (len(loend) - 1):
                context['next_obj'] = artikkel_qs.get(id=loend[n + 1])
            # Leiame ajaliselt eelneva artikli
            if n > 0:
                context['prev_obj'] = artikkel_qs.get(id=loend[n - 1])

        # Sarnased lood
        if any([seotud_isikud, seotud_organisatsioonid, seotud_objektid]):
            sarnased_artiklid = artikkel_qs.exclude(id=self.object.id)
            if seotud_isikud:
                sarnased_artiklid = sarnased_artiklid.filter(isikud__in=seotud_isikud)
            if seotud_organisatsioonid:
                sarnased_artiklid = sarnased_artiklid.filter(organisatsioonid__in=seotud_organisatsioonid)
            if seotud_objektid:
                sarnased_artiklid = sarnased_artiklid.filter(objektid__in=seotud_objektid)
        else:
            sarnased_artiklid = artikkel_qs.none()
        context['sarnased_artiklid'] = sarnased_artiklid.distinct()[:10]

        return context



#
# superklass Artikkel, Isik, Organisatsioon, Objekt objectide muutmiseks
#
class ObjectUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    redirect_field_name = 'next'
    pk_url_kwarg = 'pk'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        autoselect_fields_check_can_add(context['form'], self.model, self.request.user)
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        model = obj._meta.model.__name__.lower()
        # Lisaja/muutja andmed
        if not obj.id:
            obj.created_by = self.request.user
        else:
            obj.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if obj.hist_date:
            obj.hist_year = obj.hist_date.year
            obj.hist_month = obj.hist_date.month
        if obj.hist_enddate:
            obj.hist_endyear = obj.hist_enddate.year
        if model == 'artikkel':
            if obj.hist_date:
                obj.hist_searchdate = obj.hist_date
            else:
                if obj.hist_month:
                    obj.hist_searchdate = datetime(obj.hist_year, obj.hist_month, 1)
                else:
                    obj.hist_searchdate = datetime(obj.hist_year, 1, 1)
        obj.save()
        form.save_m2m()
        messages.success(self.request, f"{obj} andmed muudetud.")

        return redirect(f'wiki:wiki_{model}_detail', pk=self.object.id, slug=self.object.slug)


class ArtikkelUpdate(ObjectUpdate):
    model = Artikkel
    form_class = ArtikkelForm

#
# Artikli muutmiseks
#
# class ArtikkelUpdate(LoginRequiredMixin, UpdateView):
#     redirect_field_name = 'next'
#     model = Artikkel
#     pk_url_kwarg = 'pk'
#     form_class = ArtikkelForm
#
#     def form_valid(self, form):
#         objekt = form.save(commit=False)
#         # Lisaja/muutja andmed
#         if not objekt.id:
#             objekt.created_by = self.request.user
#         else:
#             objekt.updated_by = self.request.user
#         # Täidame tühjad kuupäevaväljad olemasolevate põhjal
#         if objekt.hist_date:
#             objekt.hist_year = objekt.hist_date.year
#             objekt.hist_month = objekt.hist_date.month
#             objekt.hist_searchdate = objekt.hist_date
#         else:
#             if objekt.hist_year:
#                 y = objekt.hist_year
#                 if objekt.hist_month:
#                     m = objekt.hist_month
#                 else:
#                     m = 1
#                 objekt.hist_searchdate = datetime(y, m, 1)
#             else:
#                 objekt.hist_searchdate = None
#         objekt.save()
#         form.save_m2m()
#         return redirect('wiki:wiki_artikkel_detail', pk=self.object.id, slug=self.object.slug)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         autoselect_fields_check_can_add(context['form'], self.model, self.request.user)
#         return context


class IsikUpdate(ObjectUpdate):
    model = Isik
    form_class = IsikForm


# class IsikUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
#     redirect_field_name = 'next'
#     model = Isik
#     form_class = IsikForm
#     pk_url_kwarg = 'pk'
#
#     def test_func(self):
#         return self.request.user.is_staff
#
#     def form_valid(self, form):
#         objekt = form.save(commit=False)
#         # Lisaja/muutja andmed
#         if not objekt.id:
#             objekt.created_by = self.request.user
#         else:
#             objekt.updated_by = self.request.user
#         # Täidame tühjad kuupäevaväljad olemasolevate põhjal
#         if objekt.hist_date:
#             objekt.hist_year = objekt.hist_date.year
#         if objekt.hist_enddate:
#             objekt.hist_endyear = objekt.hist_enddate.year
#         objekt.save()
#         form.save_m2m()
#         return redirect('wiki:wiki_isik_detail', pk=self.object.id, slug=self.object.slug)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         autoselect_fields_check_can_add(context['form'], self.model, self.request.user)
#         return context


class OrganisatsioonUpdate(ObjectUpdate):
    model = Organisatsioon
    form_class = OrganisatsioonForm


# class OrganisatsioonUpdate(LoginRequiredMixin, UpdateView):
#     redirect_field_name = 'next'
#     model = Organisatsioon
#     form_class = OrganisatsioonForm
#     pk_url_kwarg = 'pk'
#
#     def form_valid(self, form):
#         objekt = form.save(commit=False)
#         # Lisaja/muutja andmed
#         if not objekt.id:
#             objekt.created_by = self.request.user
#         else:
#             objekt.updated_by = self.request.user
#         # Täidame tühjad kuupäevaväljad olemasolevate põhjal
#         if objekt.hist_date:
#             objekt.hist_year = objekt.hist_date.year
#             objekt.hist_month = objekt.hist_date.month
#             objekt.hist_searchdate = objekt.hist_date
#         else:
#             if objekt.hist_year:
#                 y = objekt.hist_year
#                 if objekt.hist_month:
#                     m = objekt.hist_month
#                 else:
#                     m = 1
#                 objekt.hist_searchdate = datetime(y, m, 1)
#             else:
#                 objekt.hist_searchdate = None
#         if objekt.hist_enddate:
#             objekt.hist_endyear = objekt.hist_enddate.year
#         objekt.save()
#         form.save_m2m()
#         return redirect('wiki:wiki_organisatsioon_detail', pk=self.object.id, slug=self.object.slug)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         autoselect_fields_check_can_add(context['form'], self.model, self.request.user)
#         return context


class ObjektUpdate(ObjectUpdate):
    model = Objekt
    form_class = ObjektForm


# class ObjektUpdate(LoginRequiredMixin, UpdateView):
#     redirect_field_name = 'next'
#     model = Objekt
#     form_class = ObjektForm
#     pk_url_kwarg = 'pk'
#
#     def form_valid(self, form):
#         objekt = form.save(commit=False)
#         # Lisaja/muutja andmed
#         if not objekt.id:
#             objekt.created_by = self.request.user
#         else:
#             objekt.updated_by = self.request.user
#         # Täidame tühjad kuupäevaväljad olemasolevate põhjal
#         if objekt.hist_date:
#             objekt.hist_year = objekt.hist_date.year
#             objekt.hist_month = objekt.hist_date.month
#             objekt.hist_searchdate = objekt.hist_date
#         else:
#             if objekt.hist_year:
#                 y = objekt.hist_year
#                 if objekt.hist_month:
#                     m = objekt.hist_month
#                 else:
#                     m = 1
#                 objekt.hist_searchdate = datetime(y, m, 1)
#             else:
#                 objekt.hist_searchdate = None
#         if objekt.hist_enddate:
#             objekt.hist_endyear = objekt.hist_enddate.year
#         objekt.save()
#         form.save_m2m()
#         return redirect('wiki:wiki_objekt_detail', pk=self.object.id, slug=self.object.slug)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         autoselect_fields_check_can_add(context['form'], self.model, self.request.user)
#         return context


# class OrganisatsioonUpdate(LoginRequiredMixin, UpdateView):
#     redirect_field_name = 'next'
#     model = Organisatsioon
#     form_class = OrganisatsioonForm
#     pk_url_kwarg = 'pk'
#
#     def form_valid(self, form):
#         objekt = form.save(commit=False)
#         # Lisaja/muutja andmed
#         if not objekt.id:
#             objekt.created_by = self.request.user
#         else:
#             objekt.updated_by = self.request.user
#         # Täidame tühjad kuupäevaväljad olemasolevate põhjal
#         if objekt.hist_date:
#             objekt.hist_year = objekt.hist_date.year
#             objekt.hist_month = objekt.hist_date.month
#             objekt.hist_searchdate = objekt.hist_date
#         else:
#             if objekt.hist_year:
#                 y = objekt.hist_year
#                 if objekt.hist_month:
#                     m = objekt.hist_month
#                 else:
#                     m = 1
#                 objekt.hist_searchdate = datetime(y, m, 1)
#             else:
#                 objekt.hist_searchdate = None
#         if objekt.hist_enddate:
#             objekt.hist_endyear = objekt.hist_enddate.year
#         objekt.save()
#         form.save_m2m()
#         return redirect('wiki:wiki_organisatsioon_detail', pk=self.object.id, slug=self.object.slug)


class KaardiobjektUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    redirect_field_name = 'next'
    model = Kaardiobjekt
    form_class = KaardiobjektForm

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        kaardiobjekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not kaardiobjekt.id:
            kaardiobjekt.created_by = self.request.user
        else:
            kaardiobjekt.updated_by = self.request.user
        kaardiobjekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_kaardiobjekt_detail', pk=self.object.id)


#
# Artiklite otsimise/filtreerimise seaded
#
class ArtikkelFilter(django_filters.FilterSet):
    nimi_sisaldab = django_filters.CharFilter(method='nimi_sisaldab_filter')
    artikkel_sisaldab = django_filters.CharFilter(method='artikkel_sisaldab_filter')

    class Meta:
        model = Artikkel
        fields = {
            'hist_year': ['exact'],
            # 'kirjeldus': ['icontains'],
            # 'isikud__perenimi': ['icontains'],
            }

    def __init__(self, *args, **kwargs):
        super(ArtikkelFilter, self).__init__(*args, **kwargs)
        # at startup user doesn't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()

    def nimi_sisaldab_filter(self, queryset, name, value):
        # päritud fraas nimes
        if self.data.get('nimi_sisaldab'):
            queryset = queryset.annotate(t2isnimi=Concat('isikud__eesnimi', Value(' '), 'isikud__perenimi'))
            fraasid = self.data.get('nimi_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    t2isnimi__icontains=fraas
                )
        return queryset

    def artikkel_sisaldab_filter(self, queryset, name, value):
        # päritud fraas(id) tekstis
        fraasid = self.data.get('artikkel_sisaldab', '').split(' ')
        if len(fraasid) > 0:
            for fraas in fraasid:
                queryset = queryset.filter(
                    kirjeldus__icontains=fraas
                )
        return queryset


#
# Artiklite otsimise/filtreerimise vaade
#
class ArtikkelFilterView(FilterView):
    model = Artikkel
    paginate_by = 20
    template_name = 'wiki/artikkel_filter.html'
    # filterset_fields = {
    #         'hist_year',
    #         'kirjeldus',
    #         'isikud__perenimi',
    #         }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # filtreerime artiklid vastavalt kasutajatüübile
        # queryset = artikkel_qs_userfilter(self.request.user)
        queryset = Artikkel.objects.daatumitega(self.request)
        # filtreerime artiklid vastavalt filtrile
        filter = ArtikkelFilter(self.request.GET, queryset=queryset)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            artiklid = paginator.page(page)
        except PageNotAnInteger:
            artiklid = paginator.page(1)
        except EmptyPage:
            artiklid = paginator.page(paginator.num_pages)
        context['object_list'] = artiklid
        context['filter'] = filter
        context['searchsmallwidgethidden'] = True # ei näita mobiiliotsinguvidinat
        return context


#
# Kronoloogia
#
class ArtikkelArchiveIndexView(ArchiveIndexView):
    date_field = "hist_searchdate"
    # make_object_list = True
    context_object_name = 'artiklid'
    allow_future = True
    paginate_by = 20

    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

def artikkel_index_archive_infinite(request):
    artikkel_qs = Artikkel.objects.daatumitega(request)
    page = request.GET.get('page', 1)
    paginator = Paginator(artikkel_qs, 10)
    try:
        artiklid = paginator.page(page)
    except PageNotAnInteger:
        artiklid = paginator.page(1)
    except EmptyPage:
        artiklid = paginator.page(paginator.num_pages)
    return render(request, 'wiki/artikkel_archive_infinite.html', {'artiklid': artiklid})

class ArtikkelYearArchiveView(YearArchiveView):
    date_field = "hist_searchdate"
    context_object_name = 'artiklid'
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            session_key = request.session.session_key
            url_v6ti = request.GET.get('v6ti')
            ip = get_client_ip(request)
            path = request.path
            if session_key != url_v6ti:
                logger.warning(f'{session_key} != {url_v6ti}: {ip} {path}')
                base_url = reverse('wiki:confirm_with_recaptcha')  # 1 /confirm_with_recaptcha/
                query_string =  urlencode(
                    {
                        'edasi': reverse(
                            'wiki:artikkel_year_archive',
                            kwargs={
                                'year': self.get_year(),
                            }
                        )
                    }
                )  # 2 edasi=/wiki/kroonika/1918/
                url = '{}?{}'.format(base_url, query_string)  # 3 /confirm_with_recaptcha/?edasi=/wiki/kroonika/1918/
                return redirect(url)  # 4
                # return HttpResponseForbidden("You do not have permission to view this resource.")

        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # context['artikkel_qs'] = artikkel_qs

        aasta = context['year'].year
        # Eelnev ja järgnev artikleid sisaldav aasta
        context['aasta_eelmine'] = artikkel_qs.filter(hist_year__lt=aasta).aggregate(Max('hist_year'))['hist_year__max']
        context['aasta_j2rgmine'] = artikkel_qs.filter(hist_year__gt=aasta).aggregate(Min('hist_year'))['hist_year__min']

        # Leiame samal aastal sündinud isikud
        isik_qs = Isik.objects.daatumitega(self.request)
        # syndinud_isikud = isik_qs.\
        #     filter(dob__year = aasta).\
        #     annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())).\
        #     order_by(ExtractMonth('dob'), ExtractDay('dob'))
        syndinud_isikud = isik_qs.\
            filter(yob = aasta).\
            annotate(vanus_gen=ExpressionWrapper(aasta - F('yob'), output_field=IntegerField())).\
            order_by(ExtractMonth('dob'), ExtractDay('dob'))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. aastal sündinud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame selle aasta juubilarid
        juubilarid_isikud = get_juubilarid(isik_qs, aasta=aasta)
        context['juubilarid_isikud'] = juubilarid_isikud
        context['juubilarid_isikud_pealkiri'] = '{0}. aasta juubilarid {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal surnud isikud
        surnud_isikud = isik_qs.\
            filter(doe__year = aasta).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField())). \
            order_by(ExtractMonth('doe'), ExtractDay('doe'))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. aastal surnud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal loodud organisatsioonid
        organisatsioon_qs = Organisatsioon.objects.daatumitega(self.request)
        # loodud_organisatsioonid = organisatsioon_qs. \
        #     filter(Q(dob__year = aasta) | Q(hist_year = aasta)).\
        #     annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField())). \
        #     order_by(ExtractMonth('dob'), ExtractDay('dob'))
        loodud_organisatsioonid = organisatsioon_qs. \
            filter(yob = aasta).\
            annotate(vanus_gen=ExpressionWrapper(aasta - F('yob'), output_field=IntegerField())). \
            order_by(ExtractMonth('dob'), ExtractDay('dob'))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. aastal loodud {1}'.format(
            aasta,
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame selle aasta juubilarid organisatsioonid
        juubilarid_organisatsioonid = get_juubilarid(organisatsioon_qs, aasta=aasta)
        context['juubilarid_organisatsioonid'] = juubilarid_organisatsioonid
        context['juubilarid_organisatsioonid_pealkiri'] = '{0}. aasta juubilarid {1}'.format(
            aasta,
            Organisatsioon._meta.verbose_name_plural.lower()
        )

        # Leiame samal aastal avatud objektid
        objekt_qs = Objekt.objects.daatumitega(self.request)
        # valminud_objektid = objekt_qs. \
        #     filter(Q(dob__year = aasta) | Q(hist_year = aasta)). \
        #     annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField())). \
        #     order_by(ExtractMonth('dob'), ExtractDay('dob'))
        valminud_objektid = objekt_qs. \
            filter(yob = aasta). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('yob'), output_field=IntegerField())). \
            order_by(ExtractMonth('dob'), ExtractDay('dob'))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. aastal valminud {1}'.format(
            aasta,
            Objekt._meta.verbose_name_plural.lower()
        )
        # Leiame selle aasta juubilarid objektid
        juubilarid_objektid = get_juubilarid(objekt_qs, aasta=aasta)
        context['juubilarid_objektid'] = juubilarid_objektid
        context['juubilarid_objektid_pealkiri'] = '{0}. aasta juubilarid {1}'.format(
            aasta,
            Objekt._meta.verbose_name_plural.lower()
        )
        return context

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
       ip = x_forwarded_for.split(',')[0]
    else:
       ip = request.META.get('REMOTE_ADDR')
    return ip

from urllib.parse import urlencode

class ArtikkelMonthArchiveView(MonthArchiveView):
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            session_key = request.session.session_key
            url_v6ti = request.GET.get('v6ti')
            ip = get_client_ip(request)
            path = request.path
            if session_key != url_v6ti:
                logger.warning(f'{session_key} != {url_v6ti}: {ip} {path}')
                base_url = reverse('wiki:confirm_with_recaptcha')  # 1 /confirm_with_recaptcha/
                query_string =  urlencode(
                    {
                        'edasi': reverse(
                            'wiki:artikkel_month_archive',
                            kwargs={
                                'year': self.get_year(),
                                'month': self.get_month()
                            }
                        )
                    }
                )  # 2 edasi=/wiki/kroonika/1918/2/
                url = '{}?{}'.format(base_url, query_string)  # 3 /confirm_with_recaptcha/?edasi=/wiki/kroonika/1918/2/
                return redirect(url)  # 4
                # return HttpResponseForbidden("You do not have permission to view this resource.")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # context['artikkel_qs'] = artikkel_qs

        aasta = context['month'].year
        kuu = context['month'].month
        p2ev = context['month']
        # Salvestame kasutaja viimase kuupäevavaliku
        self.request.session['user_calendar_view_last'] = f'{aasta}-{kuu}'
        # Samal kuul toimunud
        # context['object_list'] = artikkel_qs.\
        #     filter(hist_year=aasta).\
        #     filter(Q(dob__month=kuu) | Q(doe__month=kuu) | Q(hist_month=kuu))
        # context['object_list'] = Artikkel.objects.sel_kuul(self.request, kuu).filter(hist_year=aasta)
        context['object_list'] = \
                Artikkel.objects.sel_kuul(self.request, kuu). \
                intersection(Artikkel.objects.sel_aastal(self.request, aasta))
        # Leiame samal kuul teistel aastatel märgitud artiklid
        # TODO: 1) hist_year != dob.year ja 2) kui dob ja doe ei ole samal kuul
        # sel_kuul = artikkel_qs.\
        #     exclude(hist_year=aasta).\
        #     filter(Q(dob__month=kuu)| Q(doe__month=kuu) | Q(hist_month=kuu))
        # context['sel_kuul'] = sel_kuul
        context['sel_kuul'] = Artikkel.objects.sel_kuul(self.request, kuu)
        # Leiame samal kuul sündinud isikud
        isik_qs = Isik.objects.daatumitega(self.request)
        syndinud_isikud = isik_qs.\
            filter(dob__month = kuu).\
            annotate(vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractDay('dob'))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud'] = Isik.objects.sel_kuul(self.request, kuu)
        context['syndinud_isikud_pealkiri'] = '{0} sündinud {1}'.format(
            mis_kuul(kuu),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul surnud isikud
        surnud_isikud = isik_qs.\
            filter(doe__month = kuu).\
            annotate(vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractDay('doe'))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0} surnud {1}'.format(
            mis_kuul(kuu),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul loodud organisatsioonid
        # organisatsioon_qs = Organisatsioon.objects.daatumitega(self.request)
        # loodud_organisatsioonid = organisatsioon_qs.\
        #     filter(dob__month = kuu).\
        #     annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())). \
        #     order_by(ExtractDay('dob'))
        # context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid'] = Organisatsioon.objects.sel_kuul(self.request, kuu)
        context['loodud_organisatsioonid_pealkiri'] = '{0} loodud {1}'.format(
            mis_kuul(kuu),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul avatud objektid
        # objekt_qs = Objekt.objects.daatumitega(self.request)
        # valminud_objektid = objekt_qs.\
        #     filter(dob__month = kuu).\
        #     annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())). \
        #     order_by(ExtractDay('dob'))
        # context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid'] = Objekt.objects.sel_kuul(self.request, kuu)
        context['valminud_objektid_pealkiri'] = '{0} valminud {1}'.format(
            mis_kuul(kuu),
            Objekt._meta.verbose_name_plural.lower()
        )
        return context

def artikkel_month_archive_otheryears(request, year, month):
    start = int(request.GET.get('start', 0))
    kirjeid = 50
    # artikkel_qs = Artikkel.objects.daatumitega(request)
    # sel_kuul = artikkel_qs. \
    #     exclude(hist_year=year). \
    #     filter(Q(dob__month=month) | Q(doe__month=month) | Q(hist_month=month))
    # sel_kuul_bydate_ids_list = artikkel_qs.filter(Q(dob__month=month) | Q(doe__month=month)).values_list('id', flat=True)
    # sel_kuul_bymonth_ids_list = artikkel_qs.filter(dob__isnull=True, hist_month=month).values_list('id', flat=True)
    # sel_kuul_ids = [*sel_kuul_bydate_ids_list, *sel_kuul_bymonth_ids_list]
    # sel_kuul_ids = (*sel_kuul_bydate_ids_list, *sel_kuul_bymonth_ids_list)
    # kirjeid_kokku = len(sel_kuul_ids)
    # if start > kirjeid_kokku: # kui kysitakse rohkem, kui kirjeid on
    #     start = 0
    # qs = artikkel_qs.filter(id__in=sel_kuul_ids)
    qs = Artikkel.objects.sel_kuul(request, month)
    kirjeid_kokku = len(qs)
    if qs.exists():
        sel_kuul = qs[start:start+kirjeid]
    else:
        sel_kuul = qs
    l6puni = kirjeid_kokku - start - kirjeid
    return render(
        request,
        'wiki/includes/object_list.html',
        {
            'object_list': sel_kuul,
            'kirjeid_kokku': kirjeid_kokku,
            'start': start+kirjeid,
            'kirjeid': kirjeid if l6puni>kirjeid else l6puni
        }
    )

class ArtikkelDayArchiveView(DayArchiveView):
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True

    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            session_key = request.session.session_key
            url_v6ti = request.GET.get('v6ti')
            ip = get_client_ip(request)
            path = request.path
            if session_key != url_v6ti:
                logger.warning(f'{session_key} != {url_v6ti}: {ip} {path}')
                base_url = reverse('wiki:confirm_with_recaptcha')  # 1 /confirm_with_recaptcha/
                query_string =  urlencode(
                    {
                        'edasi': reverse(
                            'wiki:artikkel_day_archive',
                            kwargs={
                                'year': self.get_year(),
                                'month': self.get_month(),
                                'day': self.get_day()
                            }
                        )
                    }
                )  # 2 edasi=/wiki/kroonika/1918/2/12/
                url = '{}?{}'.format(base_url, query_string)  # 3 /confirm_with_recaptcha/?edasi=/wiki/kroonika/1918/2/12/
                return redirect(url)  # 4
                # return HttpResponseForbidden("You do not have permission to view this resource.")

        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # context['artikkel_qs'] = artikkel_qs

        # Milline kuupäevavalik tehti
        context_day = context['day']
        aasta = context_day.year
        kuu = context_day.month
        p2ev = context_day.day
        # Salvestame kasutaja viimase kuupäevavaliku
        self.request.session['user_calendar_view_last'] = f'{aasta}-{kuu}'
        # Samal kuupäeval toimunud
        context['object_list'] = inrange_dates_artikkel(
            artikkel_qs.filter(dob__year=aasta), p2ev, kuu
        )
        # Leiame samal kuupäeval teistel aastatel märgitud artiklid
        context['sel_p2eval'] = inrange_dates_artikkel(
            artikkel_qs, p2ev, kuu
        )  # hist_date < KKPP <= hist_enddate
        # sel_p2eval = sel_p2eval_inrange
        # context['sel_p2eval'] = sel_p2eval
        # Leiame samal kuupäeval sündinud isikud
        isik_qs = Isik.objects.daatumitega(self.request)
        syndinud_isikud = isik_qs.\
            filter(dob__month = kuu, dob__day = p2ev).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())).\
            order_by(ExtractYear('dob'))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. {1} sündinud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval surnud isikud
        surnud_isikud = isik_qs.\
            filter(doe__month = kuu, doe__day = p2ev).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField())). \
            order_by(ExtractYear('doe'))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. {1} surnud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval loodud organisatsioonid
        organisatsioon_qs = Organisatsioon.objects.daatumitega(self.request)
        loodud_organisatsioonid = organisatsioon_qs.\
            filter(dob__month = kuu, dob__day = p2ev).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractYear('dob'))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. {1} loodud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval loodud objektid
        objekt_qs = Objekt.objects.daatumitega(self.request)
        valminud_objektid = objekt_qs.\
            filter(dob__month = kuu, dob__day = p2ev).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractYear('dob'))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. {1} valminud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Objekt._meta.verbose_name_plural.lower()
        )
        return context


def get_juubilarid(qs, aasta=timezone.now().year):
    # Leiame selle aasta juubilarid
    juubilarid_ids = [
        object.id
        for object
        in qs
        if (object.vanus(datetime(aasta, 1, 1)) and (object.vanus(datetime(aasta, 1, 1)) % 5 == 0))
    ]
    # juubilarid = qs. \
    #     filter(id__in=juubilarid_ids). \
    #     annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField())). \
    #     order_by('hist_year', 'dob')
    juubilarid = qs. \
        filter(id__in=juubilarid_ids). \
        annotate(vanus_gen=ExpressionWrapper(aasta - F('yob'), output_field=IntegerField())). \
        order_by('yob', 'dob')
    return juubilarid

#
# Isikute otsimiseks/filtreerimiseks
#
class IsikFilter(django_filters.FilterSet):
    nimi_sisaldab = django_filters.CharFilter(method='nimi_sisaldab_filter')

    class Meta:
        model = Isik
        fields = {
            'eesnimi': ['icontains'],
            'perenimi': ['icontains'],
            }

    # def __init__(self, *args, **kwargs):
    #     super(IsikFilter, self).__init__(*args, **kwargs)
    #     # at startup user doen't push Submit button, and QueryDict (in data) is empty
    #     if self.data == {}:
    #         self.queryset = self.queryset.none()

    def nimi_sisaldab_filter(self, queryset, name, value):
        # päritud fraas nimes
        if self.data.get('nimi_sisaldab'):
            queryset = queryset.annotate(nimi=Concat('eesnimi', Value(' '), 'perenimi'))
            fraasid = self.data.get('nimi_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    nimi__icontains=fraas
                )
        return queryset


class IsikFilterView(FilterView):
    model = Isik
    paginate_by = 20
    template_name = 'wiki/isik_filter.html'
    filterset_fields = {
            'eesnimi',
            'perenimi',
            }

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        # queryset = Isik.objects.all() # .order_by('perenimi')
        queryset = Isik.objects.daatumitega(self.request)
        filter = IsikFilter(self.request.GET, queryset=queryset)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            isikud = paginator.page(page)
        except PageNotAnInteger:
            isikud = paginator.page(1)
        except EmptyPage:
            isikud = paginator.page(paginator.num_pages)
        context['object_list'] = isikud
        context['filter'] = filter
        context['searchsmallwidgethidden'] = True  # ei näita mobiiliotsinguvidinat
        return context


class IsikDetailView(generic.DetailView):
    model = Isik
    query_pk_and_slug = True

    def get_queryset(self):
        return Isik.objects.daatumitega(self.request)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        special_objects = [  # TODO: Vajalik p2ring teha andmebaasist
            62,  # Johan Müllerson
        ]
        if pk and pk in special_objects:
            object = self.get_queryset().get(pk=pk)
        else:
            object = super().get_object(**kwargs)
        return object

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)

        # Kas isikule on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects. \
            filter(profiilipilt_isikud__in=[self.object]). \
            first()
        # Mainimine läbi aastate
        mainitud_aastatel_data = get_mainitud_aastatel(artikkel_qs, 'Isik', self.object)
        # context['mainitud_aastatel'] = mainitud_aastatel_data
        context['mainitud_aastatel_chart'] = get_mainitud_aastatel_chart(mainitud_aastatel_data)
        # Otseseosed objektidega
        context['seotud_organisatsioonid'] = Organisatsioon.objects.daatumitega(self.request).\
            filter(isik=self.object)
        context['seotud_objektid'] = Objekt.objects.daatumitega(self.request).\
            filter(isik=self.object)
        context['seotud_pildid'] = Pilt.objects.sorted(). \
            exists()
            # filter(isikud=self.object)
        
        # Lisame eellaste ja j2rglaste andmed
        context = add_eellased_j2rglane2context(self, context)

        # Artikli kaudu seotud objects lisab ajax func object_detail_seotud()
        return context


#
# object detailvaates ajax seotud objectide kuvamiseks
#
def object_detail_seotud(request, model, id):
    queryparams = QueryDict(mutable=True)
    queryparams.update(
        {model: id}
    )
    context = {
        'model': model,
        'id': id,
        'queryparams': '?' + queryparams.urlencode()
    }

    artikkel_qs = Artikkel.objects.daatumitega(request)
    model_filters = {
        'isik':           'isikud__id',
        'organisatsioon': 'organisatsioonid__id',
        'objekt':         'objektid__id'
    }
    # Objectiga seotud artiklid
    filter = {
        model_filters[model]: id
    }
    seotud_artiklid = artikkel_qs.filter(**filter)
    context['seotud_artiklid'] = seotud_artiklid
    seotud_artiklid_kokku = len(seotud_artiklid)
    context['seotud_artiklid_kokku'] = seotud_artiklid_kokku

    context['seotud_isikud_artiklikaudu'] = seotud_artiklikaudu(
        request,
        Isik,
        seotud_artiklid,
        id
    )
    context['seotud_organisatsioonid_artiklikaudu'] = seotud_artiklikaudu(
        request,
        Organisatsioon,
        seotud_artiklid,
        id
    )
    context['seotud_objektid_artiklikaudu'] = seotud_artiklikaudu(
        request,
        Objekt,
        seotud_artiklid,
        id
    )
    return render(request, 'wiki/includes/seotud_artiklikaudu.html', context)

#
# object detailvaates ajax seotud pildirida kuvamiseks
#
def object_detail_seotud_pildirida(request, model, id):
    # queryparams = QueryDict(mutable=True)
    # queryparams.update(
    #     {model: id}
    # )
    # context = {
    #     'model': model,
    #     'id': id,
    #     'queryparams': '?' + queryparams.urlencode()
    # }

    model_filters = {
        'isik':           'isikud__id',
        'organisatsioon': 'organisatsioonid__id',
        'objekt':         'objektid__id'
    }
    # Objectiga seotud pildid
    filter = {
        model_filters[model]: id
    }
    seotud_pildid = Pilt.objects.sorted().filter(**filter)
    context = {
        'seotud_pildid': seotud_pildid
    }
    return render(request, 'wiki/includes/seotud_pildid_pildirida.html', context)
    
#
# Organisatsioonide otsimiseks/filtreerimiseks
#
class OrganisatsioonFilter(django_filters.FilterSet):
    nimi_sisaldab = django_filters.CharFilter(method='nimi_sisaldab_filter')

    class Meta:
        model = Organisatsioon
        fields = {
            # 'nimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(OrganisatsioonFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()

    def nimi_sisaldab_filter(self, queryset, name, value):
        # päritud fraas nimes
        if self.data.get('nimi_sisaldab'):
            fraasid = self.data.get('nimi_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    nimi__icontains=fraas
                )
        return queryset

class OrganisatsioonFilterView(FilterView):
    model = Organisatsioon
    paginate_by = 20
    template_name = 'wiki/organisatsioon_filter.html'
    filterset_fields = {
            'nimi',
            }

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        queryset = Organisatsioon.objects.daatumitega(self.request). \
            annotate(nulliga=ExpressionWrapper((date.today().year - F('hist_year'))%5, output_field=IntegerField()))
        filter = OrganisatsioonFilter(self.request.GET, queryset=queryset)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            organisatsioonid = paginator.page(page)
        except PageNotAnInteger:
            organisatsioonid = paginator.page(1)
        except EmptyPage:
            organisatsioonid = paginator.page(paginator.num_pages)
        context['object_list'] = organisatsioonid
        context['filter'] = filter
        context['searchsmallwidgethidden'] = True  # ei näita mobiiliotsinguvidinat
        return context


class OrganisatsioonDetailView(generic.DetailView):
    model = Organisatsioon
    query_pk_and_slug = True

    def get_queryset(self):
        return Organisatsioon.objects.daatumitega(self.request)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        special_objects = [  # TODO: Vajalik p2ring teha andmebaasist
            13,  # Säde selts
        ]
        if pk and pk in special_objects:
            object = self.get_queryset().get(pk=pk)
        else:
            object = super().get_object(**kwargs)
        return object

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas organisatsioonile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects. \
            filter(profiilipilt_organisatsioonid__in=[self.object]). \
            first()

        # Mainimine läbi aastate
        # context['mainitud_aastatel'] = get_mainitud_aastatel(artikkel_qs, 'Organisatsioon', self.object)
        mainitud_aastatel_data = get_mainitud_aastatel(artikkel_qs, 'Organisatsioon', self.object)
        # context['mainitud_aastatel'] = mainitud_aastatel_data
        context['mainitud_aastatel_chart'] = get_mainitud_aastatel_chart(mainitud_aastatel_data)
        # Otseseosed objectidega
        context['seotud_isikud'] = Isik.objects.daatumitega(self.request).\
            filter(organisatsioonid=self.object)
        context['seotud_objektid'] = Objekt.objects.daatumitega(self.request).\
            filter(organisatsioon__id=self.object.id)
        context['seotud_pildid'] = Pilt.objects.sorted(). \
            exists()
            # filter(organisatsioonid=self.object)

        # Lisame eellaste ja j2rglaste andmed
        context = add_eellased_j2rglane2context(self, context)

        # Artikli kaudu seotud objects lisab ajax func object_detail_seotud()
        return context


#
# Objektide otsimiseks/filtreerimiseks
#
class ObjektFilter(django_filters.FilterSet):
    nimi_sisaldab = django_filters.CharFilter(method='nimi_sisaldab_filter')
    # t2nav_sisaldab = django_filters.CharFilter(method='t2nav_sisaldab_filter')

    class Meta:
        model = Objekt
        fields = {
            # 'nimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(ObjektFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()

    # def nimi_sisaldab_filter(self, queryset, name, value):
    #     # päritud fraas nimes
    #     fraas = self.data.get('nimi_sisaldab')
    #     if fraas:
    #         fragmendid = fraas.split(' ')
    #         regex_fill = r'\w*\s+\w*'
    #         otsi_fraas = regex_fill.join([r'({})'.format(fragment) for fragment in fragmendid])
    #         queryset = queryset.filter(nimi__iregex=r'{}'.format(otsi_fraas))
    #     return queryset

    # def nimi_sisaldab_filter(self, queryset, name, value):
    #     # päritud fraas nimes
    #     if self.data.get('nimi_sisaldab'):
    #         fraasid = self.data.get('nimi_sisaldab', '').split(' ')
    #         for fraas in fraasid:
    #             queryset = queryset.filter(
    #                 nimi__icontains=fraas
    #             )
    #     return queryset

    def nimi_sisaldab_filter(self, queryset, name, value):
        # päritud fraas nimes
        if self.data.get('nimi_sisaldab'):
            queryset = queryset.annotate(nimi_asukoht=Concat('nimi', Value(' '), 'asukoht'))
            fraasid = self.data.get('nimi_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    nimi_asukoht__icontains=fraas
                )
        return queryset

    # def t2nav_sisaldab_filter(self, queryset, name, value):
    #     queryset = queryset.filter(
    #         objektid__nimi__icontains=self.data['t2nav_sisaldab'],
    #         objektid__tyyp='T'
    #     ).distinct()
    #     return queryset


class ObjektFilterView(FilterView):
    model = Objekt
    paginate_by = 20
    template_name = 'wiki/objekt_filter.html'
    filterset_fields = {
            'nimi',
            }

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        queryset = Objekt.objects.daatumitega(self.request).\
            annotate(nulliga=ExpressionWrapper(
                (date.today().year - F('hist_year'))%5, output_field=IntegerField()
            ))
        filter = ObjektFilter(self.request.GET, queryset=queryset)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            objektid = paginator.page(page)
        except PageNotAnInteger:
            objektid = paginator.page(1)
        except EmptyPage:
            objektid = paginator.page(paginator.num_pages)
        context['object_list'] = objektid
        context['filter'] = filter
        context['searchsmallwidgethidden'] = True  # ei näita mobiiliotsinguvidinat
        return context

class ObjektDetailView(generic.DetailView):
    model = Objekt
    query_pk_and_slug = True

    def get_queryset(self):
        return Objekt.objects.daatumitega(self.request)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        special_objects = [  # TODO: Vajalik p2ring teha andmebaasist
            13, # Kesk 21, Jaani kirik
            23, # Kesk 11, raekoda
            24, # Riia 5
            29, # Tartu 2, vesiveski
            81, # J. Kuperjanovi 9, Moreli maja
            102, # Kesk 22, linnakooli hoone
            187, # Kesk 19, Klasmanni maja
            256, # Aia 12, Zenckeri villa
            354, # J. Kuperjanovi 12, lõvidega maja
        ]
        if pk and pk in special_objects:
            object = self.get_queryset().get(pk=pk)
        else:
            object = super().get_object(**kwargs)
        return object

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas objektile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects. \
            filter(profiilipilt_objektid__in=[self.object]). \
            first()
        # Kas objektil on kaardivaateid
        if self.request.user.is_authenticated and self.request.user.is_staff:
            context['seotud_kaardiobjektid'] = Kaardiobjekt.objects. \
                filter(objekt__id=self.object.id). \
                all()
        else:
            context['seotud_kaardiobjektid'] = Kaardiobjekt.objects.\
                filter(objekt__id=self.object.id).\
                exists()
        # Mainimine läbi aastate
        # context['mainitud_aastatel'] = get_mainitud_aastatel(artikkel_qs, 'Objekt', self.object)
        mainitud_aastatel_data = get_mainitud_aastatel(artikkel_qs, 'Objekt', self.object)
        # context['mainitud_aastatel'] = mainitud_aastatel_data
        context['mainitud_aastatel_chart'] = get_mainitud_aastatel_chart(mainitud_aastatel_data)
        # Otseseosed objektidega
        context['seotud_isikud'] = Isik.objects.\
            daatumitega(self.request).\
            filter(objektid=self.object)
        context['seotud_organisatsioonid'] = Organisatsioon.objects.\
            daatumitega(self.request).\
            filter(objektid=self.object)
        context['seotud_objektid'] = Objekt.objects.\
            daatumitega(self.request).\
            filter(objektid=self.object)
        context['seotud_pildid'] = Pilt.objects.sorted(). \
            exists()
            # filter(objektid=self.object)
        
        # Lisame eellaste ja j2rglaste andmed
        context = add_eellased_j2rglane2context(self, context)

        # Artikli kaudu seotud objects lisab ajax func object_detail_seotud()
        # Artikli kaudu seotud pildid lisab ajax func object_detail_pildirida()
        return context


# objectide nimel hiirega peatudes infoakna kuvamiseks
def get_object_data4tooltip(request):
    model_name = request.GET.get('model')
    id = request.GET.get('obj_id')

    try:
        model = apps.get_model('wiki', model_name)
        obj = model.objects.get(id=id)
        content = str(obj)
    except:
        print(f'vigane tooltip päring model={model_name}; id={id}')
        model = None
        obj = None
        content = ''
    if model in [Isik, Objekt, Organisatsioon]:
        if obj.kirjeldus:
            heading = f'{obj}'
            if obj.profiilipildid.exists():
                profiilipilt = obj.profiilipildid.first()
                img = settings.MEDIA_URL + profiilipilt.pilt_thumbnail.name
                img = f'<img class="tooltip-content-img" src="{img}" alt="{profiilipilt}">'
            else:
                img = ''
            content = f'<div>{heading}<p>{img}<small>{obj.kirjeldus_lyhike}</small><p></div>'
    elif model == Artikkel:
        if obj.hist_date:
            dob = obj.hist_date.strftime('%d.%m.%Y')
        elif obj.hist_month:
            dob = f'{obj.get_hist_month_display()} {obj.hist_year}'
        else:
            dob = str(obj.hist_year)
        if obj.hist_enddate:
            doe = obj.hist_enddate.strftime('%d.%m.%Y')
        else:
            doe = None
        if all([dob, doe]):
            heading = f'<strong>{dob}-{doe}</strong>'
        else:
            heading = f'<strong>{dob}</strong>'
        content = f'<div>{heading}<p><small>{obj.formatted_markdown}</small><p></div>'
    return HttpResponse(content)

def join_kaardiobjekt_with_objekt(request, kaardiobjekt_id, objekt_id):
    if request.user.is_authenticated and request.user.is_staff:
        try:
            kaardiobjekt = Kaardiobjekt.objects.get(id=kaardiobjekt_id)
            objekt = Objekt.objects.get(id=objekt_id)
            kaardiobjekt.objekt = objekt
            kaardiobjekt.save()
            return HttpResponse(f'Seotud: {kaardiobjekt} -> <strong>{objekt}</strong>')
        except:
            return HttpResponse('Sidumise viga!')
    else:
        raise PermissionDenied


# Loetleb kõik sisse logitud kasutajad
def get_all_logged_in_users():
    # Query all non-expired sessions
    # use timezone.now() instead of datetime.now() in latest versions of Django
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = []

    # Build a list of user ids from that query
    for session in sessions:
        data = session.get_decoded()
        uid_list.append(data.get('_auth_user_id', None))

    # Query all logged in users based on id list
    return User.objects.filter(id__in=uid_list)


#
# JSON-vormis põhiobjektide lingid, et kontrollida kas töötavad
#
# def test(request):
#     valik = request.META['QUERY_STRING']
#     data = dict()
#     # Artiklite testandmed
#     artikkel_qs = Artikkel.objects.daatumitega(request)
#     data['test_url_artiklid_id'] = [
#         reverse('wiki:wiki_artikkel_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
#         for obj
#         in artikkel_qs
#     ]
#     queryset = (kr
#         artikkel_qs.dates('hist_searchdate', 'year')
#     )
#     aastad = list(el.year for el in queryset)
#     data['test_url_artiklid_aasta'] = [
#         reverse('wiki:artikkel_year_archive', kwargs={'year': aasta})
#         for aasta
#         in aastad
#     ]
#     queryset = (
#         artikkel_qs.dates('hist_searchdate', 'month')
#     )
#     kuud = list((el.year, el.month) for el in queryset)
#     data['test_url_artiklid_kuu'] = [
#         reverse('wiki:artikkel_month_archive', kwargs={'year': kuu[0], 'month': kuu[1]})
#         for kuu
#         in kuud
#     ]
#     # Isikute testandmed
#     queryset = Isik.objects.all()
#     data['test_url_isikud_id'] = [
#         reverse('wiki:wiki_isik_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
#         for obj
#         in queryset
#     ]
#     # Organisatsioonide testandmed
#     queryset = Organisatsioon.objects.all()
#     data['test_url_organisatsioonid_id'] = [
#         reverse('wiki:wiki_organisatsioon_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
#         for obj
#         in queryset
#     ]
#     # Objektide testandmed
#     queryset = Objekt.objects.all()
#     data['test_url_objektid_id'] = [
#         reverse('wiki:wiki_objekt_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
#         for obj
#         in queryset
#     ]
#     # Viidete testandmed
#     queryset = Viide.objects.all()
#     data['test_url_viited_id'] = [
#         obj.url for obj in queryset if obj.url
#     ]
#     # Piltide testandmed
#     queryset = Pilt.objects.all()
#     # Pildifailid, millel puuduvad thumbnailid
#     data['test_url_pildid'] = [
#         obj.pilt.url
#         for obj
#         in queryset
#         # if len(obj.pilt_thumbnail.name)==0
#     ]
#     try:
#         urls = data[valik]
#     except:
#         urls = data
#     return JsonResponse(urls, safe=False)

def switch_vkj_ukj(request, calendar_system):
    # print('switch2:', calendar_system)
    # print('before switch', request.session.get('calendar_system'))
    request.session['calendar_system'] = calendar_system
    # print('after switch', request.session.get('calendar_system'))

    kalender_nimetus = 'vana (Juliuse)'
    if calendar_system == 'ukj':
        kalender_nimetus = 'uue (Gregoriuse)'
    messages.success(request, f"Kuupäevi näidatakse {kalender_nimetus} kalendri järgi.")

    return HttpResponse(calendar_system)


class KaardiobjektFilter(django_filters.FilterSet):
    kaardiobjekt_sisaldab = django_filters.CharFilter(method='kaardiobjekt_sisaldab_filter')

    class Meta:
        model = Kaardiobjekt
        fields = {
            'kaart__aasta': ['exact'],
        }

    def __init__(self, *args, **kwargs):
        super(KaardiobjektFilter, self).__init__(*args, **kwargs)
        # at startup user doesn't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()

    def kaardiobjekt_sisaldab_filter(self, queryset, name, value):
        # päritud fraas nimes
        if self.data.get('kaardiobjekt_sisaldab'):
            queryset = queryset.annotate(nimi=Concat('tn', Value(' '), 'nr', Value(' '), 'lisainfo'))
            fraasid = self.data.get('kaardiobjekt_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    nimi__icontains=fraas
                )
        return queryset


#
# Artiklite otsimise/filtreerimise vaade
#
class KaardiobjektFilterView(FilterView):
    model = Artikkel
    paginate_by = 50
    template_name = 'wiki/kaardiobjekt_filter.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Kaardiobjekt.objects.all()
        # filtreerime artiklid vastavalt filtrile
        filter = KaardiobjektFilter(self.request.GET, queryset=queryset)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            objects = paginator.page(page)
        except PageNotAnInteger:
            objects = paginator.page(1)
        except EmptyPage:
            objects = paginator.page(paginator.num_pages)
        context['object_list'] = objects
        context['filter'] = filter
        context['searchsmallwidgethidden'] = True  # ei näita mobiiliotsinguvidinat
        return context


class KaardiobjektDetailView(generic.DetailView):
    model = Kaardiobjekt

    def get_queryset(self):
        return Kaardiobjekt.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Kas on kattuvaid objekte teistel kaartidel
        context['kaardiobjekt_match'] = kaardiobjekt_match_db(self.object.id)
        return context


# Kalendris näidatakse ainult neid lugusid, millel hist_date olemas
def calendar_days_with_events_in_month(request):
    t2na = timezone.now()

    # Kasutaja kuuvalik ja selle loogikakontroll
    try:
        year = int(request.GET.get('year'))
        month = int(request.GET.get('month'))
        user_calendar_choice = date(int(year), int(month), 1)
    except:
        year = t2na.year-100
        month = t2na.month
        user_calendar_choice = date(year, month, 1)

    user_calendar_view_last = user_calendar_choice.strftime("%Y-%m")

    # Salvestame kasutaja kuuvaliku
    request.session['user_calendar_view_last'] = user_calendar_view_last

    artikkel_qs = Artikkel.objects.daatumitega(request).exclude(hist_date__isnull=True)

    # Millistel päevade kohta valitud kuu ja aasta on kirjeid
    days_with_events_set = set(
        artikkel_qs.
            filter(dob__year=year, dob__month=month).
            annotate(day=Extract('dob', 'day')).
            values_list('day', flat=True)
    )
    days_with_events = [day for day in days_with_events_set]

    # Millistel kuude kohta valitud aastal on kirjeid
    months_with_events_set = set(
        artikkel_qs.
            filter(dob__year=year).
            annotate(month=Extract('dob', 'month')).
            values_list('month', flat=True)
    )
    months_with_events = [month for month in months_with_events_set]

    return JsonResponse(
        {
            'days_with_events': days_with_events,
            'months_with_events': months_with_events
        },
        safe=False
    )

def get_big_leaflet_map(request):
    aasta = request.GET.get('aasta')
    objekt = request.GET.get('objekt')
    map_html = make_big_maps_leaflet(aasta, objekt=objekt)
    return HttpResponse(map_html)

def kaart(request, aasta=None):
    objekt = request.GET.get('objekt')
    return render(
        request,
        'wiki/kaart.html',
        {
            'aasta': aasta,
            'objekt': objekt,
            'searchsmallwidgethidden': True,  # ei näita mobiiliotsinguvidinat
        },
    )

# Tagastab objekti kõigi olemasolevate aastate kaardid
def get_objekt_leaflet_combo(request, objekt_id):
    map_html = make_objekt_leaflet_combo(objekt_id)
    return HttpResponse(map_html)

def get_kaardiobjekt_leaflet(request, kaardiobjekt_id):
    map_html = make_kaardiobjekt_leaflet(kaardiobjekt_id)
    return HttpResponse(map_html)

def add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im

def get_qrcode_from_uri(request):
    uri = request.GET.get('uri')
    # taking image which user wants
    # in the QR code center
    Logo_link = settings.BASE_DIR / 'wiki/static/wiki/img/android-chrome-192x192.png'

    logo = Image.open(Logo_link)
    new_image = Image.new("RGBA", logo.size, "WHITE")  # Create a white rgba background
    new_image.paste(logo, (0, 0), logo)  # Paste the image on the background. Go to the links given below for details.
    # new_image.convert('RGB').save('test.jpg', "JPEG")  # Save as JPEG
    logo = new_image

    # taking base width
    basewidth = 100

    # adjust image size
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth - 30, hsize - 30), Image.LANCZOS)
    logo = ImageOps.expand(logo, border=10, fill='white')
    QRcode = qrcode.QRCode(
        box_size=10,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )

    # adding URL or text to QRcode
    QRcode.add_data(uri)

    # generating QR code
    QRcode.make()

    # taking color name from user
    QRcolor = '#00985F'

    # adding color to QR code
    QRimg = QRcode.make_image(
        fill_color=QRcolor,
        back_color="white"
    ).convert('RGB')

    # set size of QR code
    pos = ((QRimg.size[0] - logo.size[0]) // 2,
           (QRimg.size[1] - logo.size[1]) // 2)
    QRimg.paste(logo, pos)

    # round corners
    QRimg = add_corners(QRimg, 50)

    # save the QR code generated
    # QRimg.save('gfg_QR.png')

    # print('QR code generated!')
    stream = BytesIO()
    QRimg.save(stream, "PNG")

    image_data = base64.b64encode(stream.getvalue()).decode('utf-8')

    # return HttpResponse(f'<img id="plt" src="data:image/png;base64, {image_data}"></img>')
    # qrcode_image = f'<img id="qrcode" src="data:image/png;base64, {image_data}"></img>'
    qrcode_image = f'data:image/png;base64, {image_data}'
    return HttpResponse(qrcode_image)

from wiki.forms import ConfirmForm

def confirm_with_recaptcha(request):
    # if this is a POST request we need to process the form data
    if request.method == "POST":
        form = ConfirmForm(request.POST)
        # create a form instance and populate it with data from the request:
        # check whether it's valid:
        if form.is_valid():
            base_url = form.cleaned_data['edasi']
            session_key = request.session.session_key
            url = f'{base_url}?v6ti={session_key}'
            return redirect(url)

    # if a GET (or any other method) we'll create a blank form
    else:
        edasi = request.GET.get('edasi')
        form = ConfirmForm()


    return render(
        request, 
        "wiki/confirm_with_recaptcha.html", 
        {
            "form": form,
            'edasi': edasi
        }
    )