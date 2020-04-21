from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta
import shutil
from typing import Dict, Any

from django.conf import settings
from django.contrib import messages
from django.core import serializers
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import \
    Count, Max, Min, \
    Case, F, Q, When, \
    Value, BooleanField, DateField, DecimalField, IntegerField, \
    ExpressionWrapper
from django.db.models import Count, Max, Min
from django.db.models.functions import ExtractYear, ExtractDay
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_list_or_404, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from django.utils.version import get_version
from django.views.generic.dates import ArchiveIndexView, YearArchiveView, MonthArchiveView, DayArchiveView
from django.views.generic.edit import UpdateView

import django_filters
from django_filters.views import FilterView

import requests

from blog.models import Comment
from wiki.models import Allikas, Viide, Artikkel, Isik, Objekt, Organisatsioon, Pilt, Vihje
from wiki.forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm
from wiki.forms import VihjeForm

#
# reCAPTCHA kontrollifunktsioon
#
def check_recaptcha(request):
    data = request.POST

    # get the token submitted in the form
    recaptcha_response = data.get('g-recaptcha-response')
    # print(settings.GOOGLE_RECAPTCHA_SECRET_KEY)
    # captcha verification
    url = 'https://www.google.com/recaptcha/api/siteverify'
    payload = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    resp = requests.post(
        url,
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
            # print(ip)
        print(ip, result_json)
        return False

#
# Kontrollitakse kasutajat TODO: See on ülearune
#
def artikkel_qs_userfilter(user):
    if user.is_authenticated:
        if user.is_staff: # näita kõike
            return Artikkel.objects.all()
    else: # kasuta filtrit
        return Artikkel.objects.filter(kroonika__isnull=True)

#
# wiki_base info
#
def wiki_base_info(request):
    user = request.user
    data = {
        'feedbacks': 0,
        'comments': 0,
        # 'user': request.user.is_authenticated
    }
    if user.is_authenticated and user.is_staff:
        # Vaatame ainult viimase 24h kandeid
        tagasi24h = timezone.now() - timedelta(days=1)
        data['feedbacks'] = Vihje.objects.\
            exclude(end_date__isnull=False).\
            filter(inp_date__gt=tagasi24h).count()
        data['comments'] = Comment.objects.filter(created_on__gt=tagasi24h).count()
    # print(data)
    return JsonResponse(data)

#
# Avalehekülg
#
def info(request):
    # Filtreerime artiklite hulga kasutaja järgi
    # artikkel_qs = artikkel_qs_userfilter(request.user)
    artikkel_qs = Artikkel.objects.daatumitega(request)
    andmebaasid = []
    # Allikad ja viited
    tyhjad_viited = Viide.objects.annotate(
        num_art=Count('artikkel__id'),
        num_isik=Count('isik__id'),
        num_org=Count('organisatsioon__id'),
        num_obj=Count('objekt__id'),
        num_pilt=Count('pilt__id')
    ).filter(
        num_art=0,
        num_isik=0,
        num_org=0,
        num_obj=0,
        num_pilt=0
    ).count()
    andmebaasid.append(
        ' '.join(
            [
                'Allikad:',
                f'{Allikas.objects.count()} kirjet',
                f'millele viitab: {Viide.objects.count()} (kasutuid {tyhjad_viited}) kirjet',
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Artikkel: ',
                f'kirjeid {artikkel_qs.count()} ',
                f'viidatud {artikkel_qs.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {artikkel_qs.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Isik: ',
                f'kirjeid {Isik.objects.count()} ',
                f'viidatud {Isik.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Isik.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Objekt: ',
                f'kirjeid {Objekt.objects.count()} ',
                f'viidatud {Objekt.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Objekt.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Organisatsioon: ',
                f'kirjeid {Organisatsioon.objects.count()} ',
                f'viidatud {Organisatsioon.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Organisatsioon.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Pilt: ',
                f'kirjeid {Pilt.objects.count()} ',
                f'viidatud {Pilt.objects.filter(viited__isnull=False).distinct().count()} '
            ]
        )
    )
    # Artiklite ülevaade
    andmed = artikkel_qs.aggregate(Count('id'), Min('hist_searchdate'), Max('hist_searchdate'))
    perioodid = artikkel_qs. \
        filter(hist_searchdate__isnull=False). \
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
    # TODO: Ajutine ümberkorraldamiseks
    revision_data: Dict[str, Any] = {}
    revision_data['kroonika'] = artikkel_qs.\
        filter(kroonika__isnull=False).\
        count()
    revision_data['revised'] = artikkel_qs.\
        filter(kroonika__isnull=False).\
        annotate(num_viited=Count('viited')).\
        filter(num_viited__gt=1)

     # revision_data['viiteta'] = list(artikkel_qs.filter(viited__isnull=True).values_list('id', flat=True))
    revision_data['viiteta'] = artikkel_qs.filter(viited__isnull=True)
    # Koondnäitajad aastate ja kuude kaupa
    # import json
    a = dict()
    artikleid_aasta_kaupa = artikkel_qs.\
        filter(hist_searchdate__isnull=False).\
        values('hist_year').\
        annotate(Count('hist_year')).\
        order_by('-hist_year')
    a['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa

    # Andmed süsteemi olukorra kohta
    media_root = settings.MEDIA_ROOT
    stat = shutil.disk_usage(media_root)
    system_state = {
        'media_root': media_root,
        'disk_usage': stat[1]/stat[0]*100
    }

    # Number of visits to this view, as counted in the session variable.
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    context = {
        'andmebaasid': andmebaasid,
        'andmed': andmed,
        'artikleid_kuus': artikleid_kuus,
        'artikleid_kuus_max': artikleid_kuus_max,
        'meta_data': request.META,
        'session_data': request.session,
        'a': a,
        'system_state': system_state,
        'num_visits': num_visits,
        'revision_data': revision_data, # TODO: Ajutine ümberkorraldamiseks
    }

    return render(
        request,
        'wiki/wiki_info.html',
        context,
    )


#
# Avalehekülg
#
def otsi(request):
    try:
        question = request.GET['search']
    except:
        question = ''

    return render(
        request,
        'wiki/wiki_otsi.html',
        {
            'kroonika_url': settings.ROOT_URL,
            'question': question
        }
        # {'kroonika_url': request.META['SCRIPT_NAME']}
        # {'kroonika_url': request.META['HTTP_HOST'] + request.META['SCRIPT_NAME']}
    )

#
# Tagasiside vormi töötlemine
#
def feedback(request):
    # if this is a POST request we need to process the form data
    http_referer = request.META['HTTP_REFERER'] # mis objektilt tuli vihje
    remote_addr = request.META['REMOTE_ADDR'] # kasutaja IP aadress
    http_user_agent = request.META['HTTP_USER_AGENT'] # kasutaja veebilehitseja
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
            messages.add_message(request, messages.INFO, 'Tagasiside saadetud.')
            context = {
                'vihje': vihje
            }
            return render(
                request,
                'wiki/wiki_feedback.html',
                context
            )

    # Kui on GET või tühi vorm, siis laeme algse lehe
    messages.add_message(request, messages.WARNING, 'Tühja vormi ei saadetud.')
    return HttpResponseRedirect(http_referer)

#
# Avakuva
#
def algus(request):
    # Filtreerime artiklite hulga kasutaja järgi
    # artikkel_qs = artikkel_qs_userfilter(request.user)
    artikkel_qs = Artikkel.objects.daatumitega(request)
    andmed = {} # Selle muutuja saadame veebi
    p2ev = date.today().day # str(p2ev).zfill(2) -> PP
    kuu = date.today().month # str(kuu).zfill(2) -> KK
    aasta = date.today().year
    
    # Andmebaas Artikkel andmed veebi
    a = dict()
    kirjeid = artikkel_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = artikkel_qs.latest('inp_date')
        a['viimane_muudetud'] = artikkel_qs.latest('mod_date')
        # Samal kuupäeval erinevatel aastatel toimunud
        sel_p2eval_exactly = artikkel_qs.filter( # hist_date == KKPP
            hist_date__day = p2ev,
            hist_date__month = kuu
        )
        sel_p2eval_inrange = inrange_dates_artikkel(artikkel_qs, p2ev, kuu) # hist_date < KKPP <= hist_enddate
        sel_p2eval = sel_p2eval_exactly | sel_p2eval_inrange
        sel_p2eval_kirjeid = len(sel_p2eval)
        if sel_p2eval_kirjeid > 7: # Kui leiti rohkem kui 7 kirjet võetakse 3 algusest + 1 keskelt + 3 lõpust
            a['sel_p2eval'] = (
                sel_p2eval[:3] +
                sel_p2eval[int(sel_p2eval_kirjeid/2-1):int(sel_p2eval_kirjeid/2)] +
                sel_p2eval[sel_p2eval_kirjeid-3:]
            )
        else:
            a['sel_p2eval'] = sel_p2eval
        a['sel_p2eval_kirjeid'] = sel_p2eval_kirjeid
        # Samal kuul toimunud TODO: probleem kui hist_searchdate__month ja hist_enddate__month ei ole järjest
        sel_kuul = artikkel_qs.filter(Q(hist_searchdate__month = kuu) | Q(hist_enddate__month = kuu))
        sel_kuul_kirjeid = len(sel_kuul)
        if sel_kuul_kirjeid > 9: # Kui leiti rohkem kui 9 kirjet võetakse 4 algusest + 1 keskelt + 4 lõpust
            a['sel_kuul'] = (
                sel_kuul[:4] +
                sel_kuul[int(sel_kuul_kirjeid/2-1):int(sel_kuul_kirjeid/2)] +
                sel_kuul[sel_kuul_kirjeid-4:]
            )
        else:
            a['sel_kuul'] = sel_kuul
        a['sel_kuul_kirjeid'] = sel_kuul_kirjeid
        # 100 aastat tagasi toimunud
        a['100_aastat_tagasi'] = sel_p2eval_exactly.filter(hist_date__year = (aasta-100))
        a['loetumad'] = artikkel_qs.order_by('-total_accessed')[:20] # 20 loetumat artiklit
        # Koondnäitajad aastate ja kuude kaupa
        artikleid_aasta_kaupa = Artikkel.objects.values('hist_year').annotate(Count('hist_year')).order_by('hist_year')
        a['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa
        artikleid_kuu_kaupa = Artikkel.objects.values('hist_year', 'hist_month').annotate(Count('hist_month')).order_by('hist_year', 'hist_month')
        a['artikleid_kuu_kaupa'] = artikleid_kuu_kaupa
    andmed['artikkel'] = a

    # Andmebaas Isik andmed veebi
    a = dict()
    kirjeid = Isik.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = Isik.objects.latest('inp_date')
        a['viimane_muudetud'] = Isik.objects.latest('mod_date')
        # Filtreerime isikud, kelle sünniaeg teada
        isikud_synniajaga = Isik.objects.exclude(
            hist_date__isnull=True,
            hist_year__isnull=True
        )
        a['100_aastat_tagasi'] = isikud_synniajaga.filter(
            hist_date__day = p2ev,
            hist_date__month = kuu,
            hist_date__year = (aasta-100)
        )
        a['sel_p2eval'] = isikud_synniajaga.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = isikud_synniajaga.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        a['sel_p2eval_surnud'] = isikud_synniajaga.filter(hist_enddate__day = p2ev, hist_enddate__month = kuu)
        a['sel_p2eval_surnud_kirjeid'] = len(a['sel_p2eval_surnud'])
        a['sel_kuul_surnud'] = isikud_synniajaga.filter(hist_enddate__month = kuu).order_by('hist_enddate__day')
        a['sel_kuul_surnud_kirjeid'] = len(a['sel_kuul_surnud'])
        juubilarid = [
            isik.id for isik in isikud_synniajaga if isik.vanus()%5==0
        ]
        a['juubilarid'] = isikud_synniajaga.filter(id__in=juubilarid).order_by('hist_year', 'hist_date')
    andmed['isik'] = a

    # Andmebaas Organisatsioon andmed veebi
    a = dict()
    kirjeid = Organisatsioon.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        # kp = Organisatsioon.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        # a['viimane_lisatud'] = Organisatsioon.objects.filter(inp_date=kp['max_inp_date']).last()
        a['viimane_lisatud'] = Organisatsioon.objects.latest('inp_date')
        # a['viimane_muudetud'] = Organisatsioon.objects.filter(mod_date=kp['max_mod_date']).last()
        a['viimane_muudetud'] = Organisatsioon.objects.latest('mod_date')
        a['100_aastat_tagasi'] = Organisatsioon.objects.filter(
            hist_date__day=p2ev,
            hist_date__month=kuu,
            hist_date__year=(aasta - 100)
        )
        a['sel_p2eval'] = Organisatsioon.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Organisatsioon.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        # juubilarid = Organisatsioon.objects.exclude(hist_year=None).annotate(
        #     nulliga=ExpressionWrapper(
        #         (date.today().year - F('hist_year'))%5, output_field=IntegerField()), vanus_gen=ExpressionWrapper(
        #             date.today().year - F('hist_year'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        # a['juubilarid'] = juubilarid
        organisatsioonid_synniajaga = Organisatsioon.objects.exclude(
            hist_date__isnull=True,
            hist_year__isnull=True
        )
        juubilarid = [
            organisatsioon.id for organisatsioon in organisatsioonid_synniajaga if organisatsioon.vanus() % 5 == 0
        ]
        a['juubilarid'] = organisatsioonid_synniajaga.filter(id__in=juubilarid).order_by('hist_year', 'hist_date')
    andmed['organisatsioon'] = a
    
    # Andmebaas Objekt andmed veebi
    a = dict()
    kirjeid = Objekt.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        # kp = Objekt.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        # a['viimane_lisatud'] = Objekt.objects.filter(inp_date=kp['max_inp_date']).last()
        a['viimane_lisatud'] = Objekt.objects.latest('inp_date')
        # a['viimane_muudetud'] = Objekt.objects.filter(mod_date=kp['max_mod_date']).last()
        a['viimane_muudetud'] = Objekt.objects.latest('mod_date')
        a['100_aastat_tagasi'] = Objekt.objects.filter(
            hist_date__day=p2ev,
            hist_date__month=kuu,
            hist_date__year=(aasta - 100)
        )
        a['sel_p2eval'] = Objekt.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Objekt.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        # juubilarid = Objekt.objects.exclude(hist_year=None).annotate(
        #     nulliga=ExpressionWrapper(
        #         (date.today().year - F('hist_year'))%5, output_field=IntegerField()),
        #     vanus_gen=ExpressionWrapper(
        #             date.today().year - (ExtractYear('hist_date') if 'hist_date' else F('hist_year')), output_field=IntegerField())).filter(nulliga=0).order_by('hist_year')
        # a['juubilarid'] = juubilarid
        objektid_synniajaga = Objekt.objects.exclude(
            hist_date__isnull=True,
            hist_year__isnull=True
        )
        juubilarid = [
            objekt.id for objekt in objektid_synniajaga if objekt.vanus() % 5 == 0
        ]
        a['juubilarid'] = objektid_synniajaga.filter(id__in=juubilarid).order_by('hist_year', 'hist_date')
    andmed['objekt'] = a

    # Kas on 100 aastat tagasi toimunud asju?
    andmed['100_aastat_tagasi'] = any(
        [
            andmed['artikkel']['100_aastat_tagasi'],
            andmed['isik']['100_aastat_tagasi'],
            andmed['organisatsioon']['100_aastat_tagasi'],
            andmed['objekt']['100_aastat_tagasi'],
        ]
    )

    # Andmed aasta ja kuu rippvalikumenüü jaoks
    perioodid = artikkel_qs. \
        filter(hist_searchdate__isnull=False). \
        values('hist_searchdate__year', 'hist_searchdate__month'). \
        annotate(ct=Count('id')). \
        order_by('hist_searchdate__year', 'hist_searchdate__month')
    artikleid_kuu_kaupa = [
        [
            periood['hist_searchdate__year'],
            periood['hist_searchdate__month'],
            periood['ct']
        ] for periood in perioodid
    ]
    andmed['artikleid_kuu_kaupa'] = artikleid_kuu_kaupa
    artikleid_aasta_kaupa = artikkel_qs.filter(hist_searchdate__isnull=False).values('hist_year').annotate(
        Count('hist_year')).order_by('-hist_year')
    andmed['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa

    return render(
        request, 'wiki/wiki.html', {
            'andmed': andmed,
        }
    )


#
# Tagastab kõik artiklid, kus hist_date < KKPP <= hist_enddate vahemikus
#
def inrange_dates_artikkel(qs, p2ev, kuu):
    try:
        q = qs.filter(  # Vaatleme ainult algus ja lõpuajaga ridasid1
            dob__isnull=False,
            doe__isnull=False
        ).exclude(  # Jätame välja read, kus hist_date == KKPP
            dob__month=kuu,
            dob__day=p2ev
        )
    except:
        q = qs.filter( # Vaatleme ainult algus ja lõpuajaga ridasid1
            hist_date__isnull=False,
            hist_enddate__isnull=False
        ).exclude( # Jätame välja read, kus hist_date == KKPP
            hist_date__month=kuu,
            hist_date__day=p2ev
        )
    kkpp_string = str(kuu).zfill(2)+str(p2ev).zfill(2)
    id_list = [art.id for art in q if kkpp_string in art.hist_dates_string]
    return qs.filter(id__in=id_list) # queryset

#
# Kuupäeva väljalt võetud andmete põhjal suunatakse kuupäevavaatesse
#
def mine_krono_kp(request):
    if not (request.method == 'POST' and check_recaptcha(request)):
        return redirect('wiki:info')

    kuup2ev = request.POST.get('kuup2ev').split('-')

    return HttpResponseRedirect(
        reverse(
            'wiki:artikkel_day_archive',
            kwargs={'year': kuup2ev[0], 'month': kuup2ev[1], 'day': kuup2ev[2]})
        )

#
# Kuupäeva väljalt võetud andmete põhjal suunatakse kuupäevavaatesse
#
def mine_krono_kuu(request):
    http_referer = request.META['HTTP_REFERER']  # mis objektilt tuli päring
    if request.method == 'POST' and check_recaptcha(request):
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
    else:
        return HttpResponseRedirect(http_referer)


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

def mainitud_aastatel(qs, model, obj):
    # Artiklites mainimine läbi aastate
    if model == 'Isik':
        filter = qs.filter(isikud__id=obj.id)
    elif model == 'Objekt':
        filter = qs.filter(objektid__id=obj.id)
    elif model == 'Organisatsioon':
        filter = qs.filter(organisatsioonid__id=obj.id)

    aastad = list(filter.all().values_list('hist_year', flat=True).distinct())
    if obj.hist_date:
        synniaasta = obj.hist_date.year
    elif obj.hist_year:
        synniaasta = obj.hist_year
    else:
        synniaasta = None
    if synniaasta:
        aastad.append(synniaasta)
    if obj.hist_enddate:
        surmaaasta = obj.hist_enddate.year
    elif obj.hist_year:
        surmaaasta = obj.hist_endyear
    else:
        surmaaasta = None
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


#
# Artikli vaatamiseks
#
class ArtikkelDetailView(generic.DetailView):
    model = Artikkel
    query_pk_and_slug = True
    template_name = 'wiki/artikkel_detail.html'

    def get_queryset(self):
        # return artikkel_qs_userfilter(self.request.user)
        return Artikkel.objects.daatumitega(self.request)


    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas artiklile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            artiklid__id=self.object.id).filter(profiilipilt_artikkel=True).first()
        # kuup2ev = context['artikkel'].hist_searchdate
        obj_id = context['artikkel'].id
        # Järjestame artiklid kronoloogiliselt
        loend = list(artikkel_qs.values_list('id', flat=True))
        # Leiame valitud artikli järjekorranumbri
        n = loend.index(obj_id)
        context['n'] = n
        if n > -1:
            # Leiame ajaliselt järgneva artikli
            if n < (len(loend) - 1):
                context['next_obj'] = artikkel_qs.get(id=loend[n + 1])
            # Leiame ajaliselt eelneva artikli
            if n > 0:
                context['prev_obj'] = artikkel_qs.get(id=loend[n - 1])
        return context

    def get_object(self):
        obj = super().get_object()
        # Record the last accessed date
        obj.last_accessed = timezone.now()
        obj.total_accessed += 1
        obj.save()
        return obj

#
# Artikli muutmiseks
#
class ArtikkelUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Artikkel
    pk_url_kwarg = 'pk'
    form_class = ArtikkelForm

    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_artikkel_detail', pk=self.object.id, slug=self.object.slug)


class IsikUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Isik
    form_class = IsikForm
    pk_url_kwarg = 'pk'
    
    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_isik_detail', pk=self.object.id, slug=self.object.slug)


class OrganisatsioonUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Organisatsioon
    form_class = OrganisatsioonForm
    pk_url_kwarg = 'pk'

    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_organisatsioon_detail', pk=self.object.id, slug=self.object.slug)
    
class ObjektUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Objekt
    form_class = ObjektForm
    pk_url_kwarg = 'pk'

    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_objekt_detail', pk=self.object.id, slug=self.object.slug)

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
            # 'body_text': ['icontains'],
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
            modified_qs = (
                    queryset.filter(
                        isikud__perenimi__icontains=self.data['nimi_sisaldab']
                    ) |
                    queryset.filter(
                        isikud__eesnimi__icontains=self.data['nimi_sisaldab']
                    )
            )
        return modified_qs

    def artikkel_sisaldab_filter(self, queryset, name, value):
        # päritud fraas(id) tekstis
        fraasid = self.data.get('artikkel_sisaldab', '').split(' ')
        if len(fraasid) > 0:
            modified_qs = queryset
            # modified_qs = artikkel_qs_userfilter(self.request.user)
            for fraas in fraasid:
                print(fraas)
                modified_qs = modified_qs.filter(
                    body_text__icontains=fraas
                )
            return modified_qs
        else:
            return queryset


    # @property
    # def qs(self, *args, **kwargs):
    #     # küsime algse päringu
    #     # initial_qs = super(ArtikkelFilter, self).qs
    #     modified_qs = super(ArtikkelFilter, self).qs
    #     # päritud aasta
    #     if self.data.get('hist_year__exact'):
    #         modified_qs = modified_qs.filter(
    #             hist_year__exact=self.data['hist_year__exact']
    #         )
    #     # päritud fraas nimes
    #     # if self.data.get('isikud__perenimi__icontains'):
    #     #     modified_qs = (
    #     #             modified_qs.filter(
    #     #                 isikud__perenimi__icontains=self.data['isikud__perenimi__icontains']
    #     #             ) |
    #     #             modified_qs.filter(
    #     #                 isikud__eesnimi__icontains=self.data['isikud__perenimi__icontains']
    #     #             )
    #     #     )
    #     # päritud fraas(id) tekstis
    #     # fraasid = self.data.get('body_text__icontains', '').split(' ')
    #     # if len(fraasid) > 0:
    #     #     # modified_qs = artikkel_qs_userfilter(self.request.user)
    #     #     for fraas in fraasid:
    #     #         print(fraas)
    #     #         modified_qs = modified_qs.filter(
    #     #             body_text__icontains=fraas
    #     #         )
    #     # else:
    #     #    modified_qs = super(ArtikkelFilter, self).qs
    #     return modified_qs


#
# Artiklite otsimise/filtreerimise vaade
#
class ArtikkelFilterView(FilterView):
    model = Artikkel
    paginate_by = 20
    template_name = 'wiki/artikkel_filter.html'
    # filterset_fields = {
    #         'hist_year',
    #         'body_text',
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
        return context
            

#
# Kronoloogia
#
class ArtikkelArchiveIndexView(ArchiveIndexView):
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        # return artikkel_qs_userfilter(self.request.user)
        return Artikkel.objects.daatumitega(self.request)

class ArtikkelYearArchiveView(YearArchiveView):
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        # return artikkel_qs_userfilter(self.request.user)
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        aasta = context['year'].year
        # Eelnev ja järgnev artikleid sisaldav aasta
        context['aasta_eelmine'] = artikkel_qs.filter(hist_year__lt=aasta).aggregate(Max('hist_year'))['hist_year__max']
        context['aasta_j2rgmine'] = artikkel_qs.filter(hist_year__gt=aasta).aggregate(Min('hist_year'))['hist_year__min']
        
        # Leiame samal aastal sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__year = aasta).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. aastal sündinud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__year = aasta).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. aastal surnud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal loodud organisatsioonid
        loodud_organisatsioonid = (
            Organisatsioon.objects.filter(hist_date__year = aasta) | Organisatsioon.objects.filter(hist_year = aasta)).distinct().annotate(
                # nulliga=ExpressionWrapper((date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. aastal loodud {1}'.format(
            aasta,
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal avatud objektid
        valminud_objektid = (
            Objekt.objects.filter(hist_date__year = aasta) | Objekt.objects.filter(hist_year = aasta)).distinct().annotate(
                # nulliga=ExpressionWrapper((date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. aastal valminud {1}'.format(
            aasta,
            Objekt._meta.verbose_name_plural.lower()
        )
        
        return context


class ArtikkelMonthArchiveView(MonthArchiveView):
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    # paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        # return artikkel_qs_userfilter(self.request.user)
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        aasta = context['month'].year
        kuu = context['month'].month
        p2ev = context['month']
        # Leiame samal kuul teistel aastatel märgitud artiklid TODO: probleem kui hist_searchdate__month ja hist_enddate__month ei ole järjest
        # sel_kuul = artikkel_qs.exclude(hist_searchdate__year = aasta).filter(Q(hist_date__month = kuu) | Q(hist_enddate__month = kuu))
        sel_kuul = artikkel_qs.exclude(hist_searchdate__year=aasta).filter(
            Q(hist_searchdate__month=kuu) | Q(hist_enddate__month=kuu))
        context['sel_kuul'] = sel_kuul
        # Leiame samal kuul sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__month = kuu).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0} sündinud {1}'.format(
            mis_kuul(kuu),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0} surnud {1}'.format(
            mis_kuul(kuu),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0} loodud {1}'.format(
            mis_kuul(kuu),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul avatud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu).annotate(
                # nulliga=ExpressionWrapper((date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0} valminud {1}'.format(
            mis_kuul(kuu),
            Objekt._meta.verbose_name_plural.lower()
        )
        return context


class ArtikkelDayArchiveView(DayArchiveView):
    # queryset = Artikkel.objects.all()
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True

    def get_queryset(self):
        # return artikkel_qs_userfilter(self.request.user)
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        aasta = context['day'].year
        kuu = context['day'].month
        p2ev = context['day'].day
        # Leiame samal kuupäeval teistel aastatel märgitud artiklid
        sel_p2eval_exactly = artikkel_qs.exclude(hist_searchdate__year = aasta).filter(hist_date__month = kuu, hist_date__day = p2ev)
        sel_p2eval_inrange = inrange_dates_artikkel(artikkel_qs, p2ev, kuu)  # hist_date < KKPP <= hist_enddate
        sel_p2eval = sel_p2eval_exactly | sel_p2eval_inrange
        context['sel_p2eval'] = sel_p2eval
        # Leiame samal kuupäeval sündinud isikud
        syndinud_isikud = Isik.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. {1} sündinud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu, hist_enddate__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. {1} surnud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. {1} loodud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval loodud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. {1} valminud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Objekt._meta.verbose_name_plural.lower()
        )
        
        return context


#
# Isikute otsimiseks/filtreerimiseks
#
class IsikFilter(django_filters.FilterSet):
    
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
        queryset = Isik.objects.all().order_by('perenimi')
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
        # if isikud: # Kui leiti objekte, siis leitakse mainimised lugudes
        #     artikkel_qs = artikkel_qs_userfilter(self.request.user)
        #     artikkel_qs_dict = dict()
        #     for obj in isikud:
        #         artikkel_qs_dict[obj.id] = artikkel_qs.filter(isikud__in=[obj])
        #     context['artikkel_qs_dict'] = artikkel_qs_dict
        return context
    

def seotud_isikud_artiklikaudu(seotud_artiklid, isik_ise):
    # Isikuga artiklite kaudu seotud teised isikud
    isikud = Isik.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().exclude(pk=isik_ise)
    andmed = {}
    for seotud_isik in isikud:
        kirje = {}
        kirje['id'] = seotud_isik.id
        kirje['slug'] = seotud_isik.slug
        kirje['nimi'] = seotud_isik
        # kirje['perenimi'] = seotud_isik.perenimi
        # kirje['eesnimi'] = seotud_isik.eesnimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(isikud=seotud_isik).\
            order_by('hist_searchdate').\
            values('id', 'slug', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_isik.id] = kirje
    return andmed
        

class IsikDetailView(generic.DetailView):
    model = Isik
    query_pk_and_slug = True

    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)

        # Kas isikule on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            isikud__id=self.object.id).filter(profiilipilt_isik=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel(artikkel_qs, 'Isik', self.object)

        # Isikuga seotud artiklid
        seotud_artiklid = artikkel_qs.filter(isikud__id=self.object.id)
        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        # context['feedbackform'] = VihjeForm()
        return context


#
# Organisatsioonide otsimiseks/filtreerimiseks
#
class OrganisatsioonFilter(django_filters.FilterSet):
    
    class Meta:
        model = Organisatsioon
        fields = {
            'nimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(OrganisatsioonFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()


class OrganisatsioonFilterView(FilterView):
    model = Organisatsioon
    paginate_by = 20
    template_name = 'wiki/organisatsioon_filter.html'
    filterset_fields = {
            'nimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        queryset = Organisatsioon.objects.all().annotate(
            nulliga=ExpressionWrapper((date.today().year - F('hist_year'))%5, output_field=IntegerField())).order_by('nimi')
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
        # if organisatsioonid: # Kui leiti objekte, siis leitakse mainimised lugudes
        #     artikkel_qs = artikkel_qs_userfilter(self.request.user)
        #     artikkel_qs_dict = dict()
        #     for obj in organisatsioonid:
        #         artikkel_qs_dict[obj.id] = artikkel_qs.filter(organisatsioonid__in=[obj])
        #     context['artikkel_qs_dict'] = artikkel_qs_dict
        return context
    
def seotud_organisatsioonid_artiklikaudu(seotud_artiklid, organisatsiooni_ise):
    # Isikuga artiklite kaudu seotud organisatsioonid
    organisatsioonid = Organisatsioon.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().exclude(pk=organisatsiooni_ise)
    andmed = {}
    for seotud_organisatsioon in organisatsioonid:
        kirje = {}
        kirje['id'] = seotud_organisatsioon.id
        kirje['slug'] = seotud_organisatsioon.slug
        kirje['nimi'] = seotud_organisatsioon.nimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(organisatsioonid=seotud_organisatsioon).\
            order_by('hist_searchdate').\
            values('id', 'slug', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_organisatsioon.id] = kirje
    return andmed


class OrganisatsioonDetailView(generic.DetailView):
    model = Organisatsioon

    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas organisatsioonile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            organisatsioonid__id=self.object.id).filter(profiilipilt_organisatsioon=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel(artikkel_qs, 'Organisatsioon', self.object)

        # Organisatsiooniga seotud artiklid
        seotud_artiklid = artikkel_qs.filter(organisatsioonid__id=self.object.id)

        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        # context['feedbackform'] = VihjeForm()
        return context


#
# Objektide otsimiseks/filtreerimiseks
#
class ObjektFilter(django_filters.FilterSet):
    
    class Meta:
        model = Objekt
        fields = {
            'nimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(ObjektFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()


class ObjektFilterView(FilterView):
    model = Objekt
    paginate_by = 20
    template_name = 'wiki/objekt_filter.html'
    filterset_fields = {
            'nimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        queryset = Objekt.objects.all().annotate(
            nulliga=ExpressionWrapper(
                (date.today().year - F('hist_year'))%5, output_field=IntegerField()
            )).order_by('nimi')
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
        # if objektid: # Kui leiti objekte, siis leitakse mainimised lugudes
        #     artikkel_qs = artikkel_qs_userfilter(self.request.user)
        #     artikkel_qs_dict = dict()
        #     for obj in objektid:
        #         artikkel_qs_dict[obj.id] = artikkel_qs.filter(objektid__in=[obj])
        #     context['artikkel_qs_dict'] = artikkel_qs_dict
        return context
    
def seotud_objektid_artiklikaudu(seotud_artiklid, objekt_ise):
    # Objektiga artiklite kaudu seotud organisatsioonid
    objektid = Objekt.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().exclude(pk=objekt_ise)
    andmed = {}
    for seotud_objekt in objektid:
        kirje = {}
        kirje['id'] = seotud_objekt.id
        kirje['slug'] = seotud_objekt.slug
        kirje['nimi'] = seotud_objekt.nimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(objektid=seotud_objekt).\
            order_by('hist_searchdate').\
            values('id', 'slug', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_objekt.id] = kirje
    return andmed


class ObjektDetailView(generic.DetailView):
    model = Objekt

    def get_context_data(self, **kwargs):
        # artikkel_qs = artikkel_qs_userfilter(self.request.user)
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)

        # Kas objektile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            objektid__id=self.object.id).filter(profiilipilt_objekt=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel(artikkel_qs, 'Objekt', self.object)

        # Objektiga seotud artiklid
        seotud_artiklid = artikkel_qs.filter(objektid__id=self.object.id)
        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        # context['feedbackform'] = VihjeForm()
        return context


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
def test(request):
    valik = request.META['QUERY_STRING']
    # TODO: Saata tühi vastus, kui pole konkreetset valikut
    data = dict()
    # data['meta_server_addr'] = request.META['SERVER_ADDR']
    # Artiklite testandmed
    # artikkel_qs = artikkel_qs_userfilter(request.user)
    artikkel_qs = Artikkel.objects.daatumitega(request)
    data['test_url_artiklid_id'] = [
        reverse('wiki:wiki_artikkel_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
        for obj
        in artikkel_qs
    ]
    # queryset = (
    #     Artikkel.objects
    #         .filter(hist_searchdate__isnull=False)
    #         .annotate(year=ExtractYear('hist_searchdate'))
    #         .values('year')
    # )
    # aastad = list(set(el['year'] for el in queryset))
    queryset = (
        artikkel_qs.dates('hist_searchdate', 'year')
    )
    aastad = list(el.year for el in queryset)
    data['test_url_artiklid_aasta'] = [
        reverse('wiki:artikkel_year_archive', kwargs={'year': aasta})
        for aasta
        in aastad
    ]
    queryset = (
        artikkel_qs.dates('hist_searchdate', 'month')
    )
    kuud = list((el.year, el.month) for el in queryset)
    data['test_url_artiklid_kuu'] = [
        reverse('wiki:artikkel_month_archive', kwargs={'year': kuu[0], 'month': kuu[1]})
        for kuu
        in kuud
    ]
    # Isikute testandmed
    queryset = Isik.objects.all()
    data['test_url_isikud_id'] = [
        reverse('wiki:wiki_isik_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
        for obj
        in queryset
    ]
    # Organisatsioonide testandmed
    queryset = Organisatsioon.objects.all()
    data['test_url_organisatsioonid_id'] = [
        reverse('wiki:wiki_organisatsioon_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
        for obj
        in queryset
    ]
    # Objektide testandmed
    queryset = Objekt.objects.all()
    data['test_url_objektid_id'] = [
        reverse('wiki:wiki_objekt_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
        for obj
        in queryset
    ]
    # Viidete testandmed
    queryset = Viide.objects.all()
    data['test_url_viited_id'] = [
        obj.url for obj in queryset if obj.url
    ]
    # Piltide testandmed
    queryset = Pilt.objects.all()
    # Pildifailid, millel puuduvad thumbnailid
    data['test_url_pildid'] = [
        obj.pilt.url
        for obj
        in queryset
        # if len(obj.pilt_thumbnail.name)==0
    ]
    try:
        urls = data[valik]
    except:
        urls = data
    return JsonResponse(urls, safe=False)


# Arhiiv taaskasutamise jaoks:

#
# Jõulutervituse lehekülg
#
def special_j6ul2019(request):
    tervitaja = request.META['QUERY_STRING']
    # Kui tervituses on mitu osa
    tykid = tervitaja.split('&')
    # Filtreerime välja FB lisa
    tervitaja = '&'.join([tykk.replace('+', ' ') for tykk in tykid if 'fbclid=' not in tykk])
    if tervitaja:
        tervitaja = tervitaja[:30]
    else:
        tervitaja = 'valgalinn.ee'
    return render(
        request,
        'wiki/wiki_special_j6ul.html',
        {
            'tervitaja': tervitaja,
        }
    )

def switch_vkj_ukj(request, ukj):
    # print('switch2:', ukj)
    # print('before switch', request.session.get('ukj'))
    request.session['ukj'] = ukj
    # print('after switch', request.session.get('ukj'))
    return HttpResponse(ukj)

def ukj_test(request):
    # artikkel_qs = artikkel_qs_userfilter(request.user)
    artikkel_qs = Artikkel.objects.daatumitega(request)
    # andmed = {}  # Selle muutuja saadame veebi
    # p2ev = date.today().day  # str(p2ev).zfill(2) -> PP
    # kuu = date.today().month  # str(kuu).zfill(2) -> KK
    # aasta = date.today().year

    artikkel = dict()
    artikkel['kirjeid'] = artikkel_qs.count()
    artikkel['viimane_lisatud'] = artikkel_qs.latest('inp_date')
    artikkel['viimane_muudetud'] = artikkel_qs.latest('mod_date')

    isik = dict()
    isik['kirjeid'] = Isik.objects.count()
    isik['viimane_lisatud'] = Isik.objects.latest('inp_date')
    isik['viimane_muudetud'] = Isik.objects.latest('mod_date')

    organisatsioon = dict()
    organisatsioon['kirjeid'] = Organisatsioon.objects.count()
    organisatsioon['viimane_lisatud'] = Organisatsioon.objects.latest('inp_date')
    organisatsioon['viimane_muudetud'] = Organisatsioon.objects.latest('mod_date')

    objekt = dict()
    objekt['kirjeid'] = Objekt.objects.count()
    objekt['viimane_lisatud'] = Objekt.objects.latest('inp_date')
    objekt['viimane_muudetud'] = Objekt.objects.latest('mod_date')

    andmed = {
        'artikkel': artikkel,
        'isik': isik,
        'organisatsioon': organisatsioon,
        'objekt': objekt
    }

    return render(
        request,
        'wiki/ukj_test.html',
        {
            'andmed': andmed,
        }
    )

def ukj_test_artikkel_detail(request):
    # Filtreerime artiklite hulga kasutaja järgi
    artikkel_qs = Artikkel.objects.daatumitega(request)

    p2ev = date.today().day  # str(p2ev).zfill(2) -> PP
    kuu = date.today().month  # str(kuu).zfill(2) -> KK
    aasta = date.today().year

    # Andmebaas Artikkel andmed veebi
    a = dict()
    kirjeid = artikkel_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = artikkel_qs.latest('inp_date')
        a['viimane_muudetud'] = artikkel_qs.latest('mod_date')
        # Samal kuupäeval erinevatel aastatel toimunud
        sel_p2eval_exactly = artikkel_qs.filter(  # hist_date == KKPP
            dob__day=p2ev,
            dob__month=kuu
        )
        sel_p2eval_inrange = inrange_dates_artikkel(artikkel_qs, p2ev, kuu)  # hist_date < KKPP <= hist_enddate
        sel_p2eval = sel_p2eval_exactly | sel_p2eval_inrange
        sel_p2eval_kirjeid = len(sel_p2eval)
        if sel_p2eval_kirjeid > 5:  # Kui leiti rohkem kui viis kirjet võetakse 2 algusest + 1 keskelt + 2 lõpust
            a['sel_p2eval'] = sel_p2eval[:2] + sel_p2eval[int(sel_p2eval_kirjeid / 2 - 1):int(
                sel_p2eval_kirjeid / 2)] + sel_p2eval[sel_p2eval_kirjeid - 2:]
        else:
            a['sel_p2eval'] = sel_p2eval
        a['sel_p2eval_kirjeid'] = sel_p2eval_kirjeid
        # Samal kuul toimunud TODO: probleem kui hist_searchdate__month ja hist_enddate__month ei ole järjest
        sel_kuul = artikkel_qs.filter(Q(dob__month=kuu) | Q(doe__month=kuu))
        sel_kuul_kirjeid = len(sel_kuul)
        if sel_kuul_kirjeid > 9:  # Kui leiti rohkem kui 9 kirjet võetakse 4 algusest + 1 keskelt + 4 lõpust
            a['sel_kuul'] = (
                    sel_kuul[:4] +
                    sel_kuul[int(sel_kuul_kirjeid / 2 - 1):int(sel_kuul_kirjeid / 2)] +
                    sel_kuul[sel_kuul_kirjeid - 4:]
            )
        else:
            a['sel_kuul'] = sel_kuul
        a['sel_kuul_kirjeid'] = sel_kuul_kirjeid
        # 100 aastat tagasi toimunud
        a['100_aastat_tagasi'] = sel_p2eval_exactly.filter(dob__year=(aasta - 100))
        a['loetumad'] = artikkel_qs.order_by('-total_accessed')[:20]  # 20 loetumat artiklit
        # Koondnäitajad aastate ja kuude kaupa
        artikleid_aasta_kaupa = Artikkel.objects.values('hist_year').annotate(Count('hist_year')).order_by('hist_year')
        a['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa
        artikleid_kuu_kaupa = Artikkel.objects.values('hist_year', 'hist_month').annotate(Count('hist_month')).order_by(
            'hist_year', 'hist_month')
        a['artikleid_kuu_kaupa'] = artikleid_kuu_kaupa

    andmed = {
        'artikkel': a,
        'isik' : {
            '100_aastat_tagasi': Isik.objects.daatumitega(request).filter(
                dob__day=p2ev,
                dob__month=kuu,
                dob__year=(aasta - 100)
            )
        },
        'organisatsioon': {
            '100_aastat_tagasi': Organisatsioon.objects.daatumitega(request).filter(
                dob__day=p2ev,
                dob__month=kuu,
                dob__year=(aasta - 100)
            )
        },
        'objekt': {
            '100_aastat_tagasi': Objekt.objects.daatumitega(request).filter(
                dob__day=p2ev,
                dob__month=kuu,
                dob__year=(aasta - 100)
            )
        },
    }


    # Kas on 100 aastat tagasi toimunud asju?
    andmed['100_aastat_tagasi'] = any(
        [
            andmed['artikkel']['100_aastat_tagasi'],
            andmed['isik']['100_aastat_tagasi'],
            andmed['organisatsioon']['100_aastat_tagasi'],
            andmed['objekt']['100_aastat_tagasi'],
        ]
    )

    return render(
        request,
        'wiki/ukj_test_artikkel_detail.html',
        {
            'andmed': andmed,
        }
    )


def ukj_test_isik_detail(request):
    # ukj_state = request.session.get('ukj', 'false')
    p2ev = date.today().day  # str(p2ev).zfill(2) -> PP
    kuu = date.today().month  # str(kuu).zfill(2) -> KK
    aasta = date.today().year

    # Andmebaas Isik andmed veebi
    isik = dict()
    kirjeid = Isik.objects.count()
    isik['kirjeid'] = kirjeid

    if kirjeid > 0:
        isikud_daatumitega = Isik.objects.daatumitega(request)
        isik['viimane_lisatud'] = Isik.objects.latest('inp_date')
        isik['viimane_muudetud'] = Isik.objects.latest('mod_date')
        isikud_synniajaga = isikud_daatumitega. \
            exclude(
            hist_date__isnull=True,
            hist_year__isnull=True,
        )
        isikud_surmaajaga = isikud_daatumitega. \
            exclude(
            hist_enddate__isnull=True,
            hist_endyear__isnull=True,
        )
        isik['100_aastat_tagasi'] = isikud_synniajaga.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        isik['sel_p2eval'] = isikud_synniajaga.filter(dob__day=p2ev, dob__month=kuu)
        isik['sel_p2eval_kirjeid'] = len(isik['sel_p2eval'])
        isik['sel_kuul'] = isikud_synniajaga.filter(dob__month=kuu).order_by(ExtractDay('dob'))
        isik['sel_kuul_kirjeid'] = len(isik['sel_kuul'])
        isik['sel_p2eval_surnud'] = isikud_surmaajaga.filter(doe__day=p2ev, doe__month=kuu)
        isik['sel_p2eval_surnud_kirjeid'] = len(isik['sel_p2eval_surnud'])
        isik['sel_kuul_surnud'] = isikud_surmaajaga.filter(doe__month=kuu).order_by(ExtractDay('doe'))
        isik['sel_kuul_surnud_kirjeid'] = len(isik['sel_kuul_surnud'])
        juubilarid = [
            isik.id for isik in isikud_synniajaga if isik.vanus() % 5 == 0
        ]
        isik['juubilarid'] = isikud_synniajaga.filter(id__in=juubilarid).order_by('hist_year', 'dob')

    andmed = {
        'isik': isik
    }

    return render(
        request,
        'wiki/ukj_test_isik_detail.html',
        {
            'andmed': andmed,
        }
    )

def ukj_test_organisatsioon_detail(request):
    # ukj_state = request.session.get('ukj')
    p2ev = date.today().day  # str(p2ev).zfill(2) -> PP
    kuu = date.today().month  # str(kuu).zfill(2) -> KK
    aasta = date.today().year

    # Andmebaas Objekt andmed veebi
    organisatsioon = dict()
    kirjeid = Organisatsioon.objects.count()
    organisatsioon['kirjeid'] = kirjeid

    if kirjeid > 0:
        organisatsioon['viimane_lisatud'] = Organisatsioon.objects.latest('inp_date')
        organisatsioon['viimane_muudetud'] = Organisatsioon.objects.latest('mod_date')
        organisatsioonid_daatumitega = Organisatsioon.objects.daatumitega(request)
        organisatsioonid_synniajaga = organisatsioonid_daatumitega. \
            exclude(
            hist_date__isnull=True,
            hist_year__isnull=True,
        )
        organisatsioonid_surmaajaga = organisatsioonid_daatumitega. \
            exclude(
            hist_enddate__isnull=True,
            hist_endyear__isnull=True,
        )

        organisatsioon['100_aastat_tagasi'] = organisatsioonid_synniajaga.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        organisatsioon['sel_p2eval'] = organisatsioonid_synniajaga.filter(dob__day=p2ev, dob__month=kuu)
        organisatsioon['sel_p2eval_kirjeid'] = len(organisatsioon['sel_p2eval'])
        organisatsioon['sel_kuul'] = organisatsioonid_synniajaga.filter(dob__month=kuu).order_by(ExtractDay('dob'))
        organisatsioon['sel_kuul_kirjeid'] = len(organisatsioon['sel_kuul'])
        # isik['sel_p2eval_surnud'] = isikud_synniajaga.filter(dod__day=p2ev, dod__month=kuu)
        # isik['sel_p2eval_surnud_kirjeid'] = len(isik['sel_p2eval_surnud'])
        # isik['sel_kuul_surnud'] = isikud_synniajaga.filter(dod__month=kuu).order_by(ExtractDay('dod'))
        # isik['sel_kuul_surnud_kirjeid'] = len(isik['sel_kuul_surnud'])
        juubilarid = [
            organisatsioon.id for organisatsioon in organisatsioonid_synniajaga if organisatsioon.vanus() % 5 == 0
        ]
        organisatsioon['juubilarid'] = organisatsioonid_synniajaga.filter(id__in=juubilarid).order_by('hist_year', 'dob')

    andmed = {
        'organisatsioon': organisatsioon
    }

    return render(
        request,
        'wiki/ukj_test_organisatsioon_detail.html',
        {
            'andmed': andmed,
        }
    )

def ukj_test_objekt_detail(request):
    # ukj_state = request.session.get('ukj')
    p2ev = date.today().day  # str(p2ev).zfill(2) -> PP
    kuu = date.today().month  # str(kuu).zfill(2) -> KK
    aasta = date.today().year

    # Andmebaas Objekt andmed veebi
    objekt = dict()
    kirjeid = Objekt.objects.count()
    objekt['kirjeid'] = kirjeid

    if kirjeid > 0:
        objekt['viimane_lisatud'] = Objekt.objects.latest('inp_date')
        objekt['viimane_muudetud'] = Objekt.objects.latest('mod_date')
        objektid_daatumitega = Objekt.objects.daatumitega(request)
        objektid_synniajaga = objektid_daatumitega. \
            exclude(
            hist_date__isnull=True,
            hist_year__isnull=True,
        )
        objektid_surmaajaga = objektid_daatumitega. \
            exclude(
            hist_enddate__isnull=True,
            hist_endyear__isnull=True,
        )

        objekt['100_aastat_tagasi'] = objektid_synniajaga.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        objekt['sel_p2eval'] = objektid_synniajaga.filter(dob__day=p2ev, dob__month=kuu)
        objekt['sel_p2eval_kirjeid'] = len(objekt['sel_p2eval'])
        objekt['sel_kuul'] = objektid_synniajaga.filter(dob__month=kuu).order_by(ExtractDay('dob'))
        objekt['sel_kuul_kirjeid'] = len(objekt['sel_kuul'])
        # isik['sel_p2eval_surnud'] = isikud_synniajaga.filter(dod__day=p2ev, dod__month=kuu)
        # isik['sel_p2eval_surnud_kirjeid'] = len(isik['sel_p2eval_surnud'])
        # isik['sel_kuul_surnud'] = isikud_synniajaga.filter(dod__month=kuu).order_by(ExtractDay('dod'))
        # isik['sel_kuul_surnud_kirjeid'] = len(isik['sel_kuul_surnud'])
        juubilarid = [
            objekt.id for objekt in objektid_synniajaga if objekt.vanus() % 5 == 0
        ]
        objekt['juubilarid'] = objektid_synniajaga.filter(id__in=juubilarid).order_by('hist_year', 'dob')

    andmed = {
        'objekt': objekt
    }

    return render(
        request,
        'wiki/ukj_test_objekt_detail.html',
        {
            'andmed': andmed,
        }
    )

