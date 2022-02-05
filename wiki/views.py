from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta
# from functools import reduce
# from operator import or_
import pkg_resources
from typing import Dict, Any

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
# from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import \
    Count, Max, Min, \
    Case, F, Func, Q, When, \
    Value, BooleanField, DateField, DecimalField, IntegerField, \
    ExpressionWrapper
from django.db.models import Count, Max, Min
from django.db.models.functions import Concat, Extract, ExtractYear, ExtractMonth, ExtractDay
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
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
from wiki.forms import VihjeForm, V6rdleForm

from wiki.utils.shp_util import (
    make_objekt_leaflet_combo,
    make_kaardiobjekt_leaflet,
    kaardiobjekt_match_db,
    make_big_maps_leaflet
)

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
        print('recaptcha:', ip, result_json)
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
                f'pildiga {artikkel_qs.filter(pilt__isnull=False).distinct().count()} '
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
                f'pildiga {isik_qs.filter(pilt__isnull=False).distinct().count()} '
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
                f'pildiga {objekt_qs.filter(pilt__isnull=False).distinct().count()} ',
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
                f'pildiga {organisatsioon_qs.filter(pilt__isnull=False).distinct().count()} '
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

    context = {
        'andmebaasid': andmebaasid,
        'andmed': andmed,
        'artikleid_kuus': artikleid_kuus,
        'artikleid_kuus_max': artikleid_kuus_max,
        'session_data': request.session,
        'cookies': request.COOKIES,
        'env': env,
        'a': a,
        'revision_data': revision_data, # TODO: Ajutine ümberkorraldamiseks
        'time_log': time_log,
    }

    return render(
        request,
        'wiki/wiki_info.html',
        context,
    )


#
# Avalehekülje otsing
#
def otsi(request):
    try: # TODO:ei tööta
        question = request.GET['search']
    except:
        question = ''

    return render(
        request,
        'wiki/wiki_otsi.html',
        {
            'question': question
        }
    )

#
# Tagasiside vormi töötlemine
#
def feedback(request):
    # if this is a POST request we need to process the form data
    a = request.META
    http_referer = request.META.get('HTTP_REFERER', reverse('algus')) # mis objektilt tuli vihje
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
                'vihje': vihje
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

#
# Avakuva
#
def algus(request):
    # Filtreerime artiklite hulga kasutaja järgi
    artikkel_qs = Artikkel.objects.daatumitega(request)
    andmed = {} # Selle muutuja saadame veebi
    p2ev = date.today().day # str(p2ev).zfill(2) -> PP
    kuu = date.today().month # str(kuu).zfill(2) -> KK
    aasta = date.today().year

    # Andmebaas Artikkel andmed veebi
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
        sel_p2eval_exactly = artikkel_qs.filter( # hist_date == KKPP
            dob__day = p2ev,
            dob__month = kuu
        )
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
        sel_kuul = artikkel_qs.filter(Q(dob__month=kuu) | Q(hist_month=kuu) | Q(doe__month=kuu))
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
        # 100 aastat tagasi toimunud
        a['100_aastat_tagasi'] = sel_p2eval_exactly.filter(dob__year = (aasta-100))
        a['loetumad'] = artikkel_qs.order_by('-total_accessed')[:20] # 20 loetumat artiklit
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
    andmed['artikkel'] = a

    # Andmebaas Isik andmed veebi
    a = dict()
    isik_qs = Isik.objects.daatumitega(request)
    kirjeid = isik_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = isik_qs.latest('inp_date')
        a['viimane_muudetud'] = isik_qs.latest('mod_date')
        a['100_aastat_tagasi'] = isik_qs.filter(
            dob__day = p2ev,
            dob__month = kuu,
            dob__year = (aasta-100)
        )
        a['sel_p2eval'] = isik_qs.filter(
            dob__day = p2ev,
            dob__month = kuu
        )
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = isik_qs.\
            filter(dob__month = kuu).\
            order_by(ExtractDay('dob'))
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        a['sel_p2eval_surnud'] = isik_qs.filter(
            doe__day = p2ev,
            doe__month = kuu
        )
        a['sel_p2eval_surnud_kirjeid'] = len(a['sel_p2eval_surnud'])
        a['sel_kuul_surnud'] = isik_qs.\
            filter(doe__month = kuu).\
            order_by(ExtractDay('doe'))
        a['sel_kuul_surnud_kirjeid'] = len(a['sel_kuul_surnud'])
        juubilarid = [
            isik.id
            for isik
            in isik_qs
            if (isik.vanus() and (isik.vanus()%5==0))
        ]
        a['juubilarid'] = isik_qs.\
            filter(id__in=juubilarid).\
            order_by('hist_year', 'dob')
    andmed['isik'] = a

    # Andmebaas Organisatsioon andmed veebi
    a = dict()
    organisatsioon_qs = Organisatsioon.objects.daatumitega(request)
    kirjeid = organisatsioon_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = organisatsioon_qs.latest('inp_date')
        a['viimane_muudetud'] = organisatsioon_qs.latest('mod_date')
        a['100_aastat_tagasi'] = organisatsioon_qs.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        a['sel_p2eval'] = organisatsioon_qs.filter(
            dob__day = p2ev,
            dob__month = kuu
        )
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = organisatsioon_qs.\
            filter(dob__month = kuu).\
            order_by(ExtractDay('dob'))
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = [
            organisatsioon.id
            for organisatsioon
            in organisatsioon_qs
            if (organisatsioon.vanus() and (organisatsioon.vanus() % 5 == 0))
        ]
        a['juubilarid'] = organisatsioon_qs.\
            filter(id__in=juubilarid).\
            order_by('hist_year', 'dob')
    andmed['organisatsioon'] = a

    # Andmebaas Objekt andmed veebi
    a = dict()
    objekt_qs = Objekt.objects.daatumitega(request)
    kirjeid = objekt_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        a['viimane_lisatud'] = objekt_qs.latest('inp_date')
        a['viimane_muudetud'] = objekt_qs.latest('mod_date')
        a['100_aastat_tagasi'] = objekt_qs.filter(
            dob__day=p2ev,
            dob__month=kuu,
            dob__year=(aasta - 100)
        )
        a['sel_p2eval'] = objekt_qs.filter(
            dob__day = p2ev,
            dob__month = kuu
        )
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = objekt_qs.\
            filter(dob__month = kuu).\
            order_by(ExtractDay('dob'))
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = [
            objekt.id
            for objekt
            in objekt_qs
            if (objekt.vanus() and (objekt.vanus() % 5 == 0))
        ]
        a['juubilarid'] = objekt_qs.\
            filter(id__in=juubilarid).\
            order_by('hist_year', 'dob')
    andmed['objekt'] = a

    # Andmebaas Kaart andmed veebi
    a = dict()
    z, x, y = 15, 18753, 9907 # näitamiseks valitud kaarditükk
    qs = Kaart.objects\
        .filter(tiles__startswith='http')\
        .annotate(sample_tile=F('tiles'))\
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
    andmed['kaart'] = a

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
    artikleid_aasta_kaupa = artikkel_qs.\
        filter(hist_searchdate__isnull=False).\
        values('hist_year').\
        annotate(Count('hist_year')).\
        order_by('-hist_year')
    andmed['artikleid_aasta_kaupa'] = artikleid_aasta_kaupa

    # Kalendriandmed
    user_calendar_view_last = request.session.get('user_calendar_view_last')
    if not user_calendar_view_last:
        t2na = timezone.now()
        user_calendar_view_last = date(t2na.year - 100, t2na.month, t2na.day).strftime("%Y-%m")
        request.session['user_calendar_view_last'] = user_calendar_view_last

    # Millistel kuude kohta valitud aastal on kirjeid
    years_with_events_set = set(
        artikkel_qs.\
            exclude(hist_date__isnull=True).\
            values_list('hist_year', flat=True)
    )
    years_with_events = [day for day in years_with_events_set]

    kalender = {
        'user_calendar_view_last': user_calendar_view_last,
        'calendar_days_with_events_in_month_url': reverse('wiki:calendar_days_with_events_in_month'),
        'years_with_events': years_with_events
    }

    return render(
        request, 'wiki/wiki.html', {
            'kalender': kalender,
            'andmed': andmed,
        }
    )


#
# Tagastab kõik artiklid, kus hist_date < KKPP <= hist_enddate vahemikus
#
def inrange_dates_artikkel(qs, p2ev, kuu):
    q = qs.filter(hist_date__isnull=False) # Vaatleme ainult algusajaga ridasid
    kkpp_string = str(kuu).zfill(2)+str(p2ev).zfill(2)
    id_list = [art.id for art in q if kkpp_string in art.hist_dates_string]
    return qs.filter(id__in=id_list) # queryset

#
# Avalehekülje otsing
#
from django.contrib.auth.decorators import login_required

@login_required
def v6rdle(request):
    vasak_object = request.GET.get('vasak_object')
    parem_object = request.GET.get('parem_object')
    initial_dict = {
        "vasak_object": vasak_object,
        "parem_object": parem_object,
    }
    form = V6rdleForm(request.GET, initial=initial_dict)

    return render(
        request,
        'wiki/wiki_v6rdle.html',
        {
            'form': form,
            'vasak_object_id': vasak_object,
            'parem_object_id': parem_object
        }
    )

# objectide nimel hiirega peatudes infoakna kuvamiseks
def get_v6rdle_object(request):
    model_name = request.GET.get('model')
    id = request.GET.get('obj_id')
    model = apps.get_model('wiki', model_name)
    object = model.objects.daatumitega(request).get(id=id)

    # Objectiga seotud artiklid
    artikkel_qs = Artikkel.objects.daatumitega(request)
    model_filters = {
        'Isik':           'isikud__id',
        'Organisatsioon': 'organisatsioonid__id',
        'Objekt':         'objektid__id'
    }
    filter = {
        model_filters[model_name]: id
    }
    seotud_artiklid = artikkel_qs.filter(**filter)

    return render(
        request,
        'wiki/wiki_v6rdle_isik.html',
        {
            'object': object,
            'seotud_artiklid': seotud_artiklid
        }
    )


#
# Funktsioon duplikaatkirjete koondamiseks
# Kasutamine:
# python manage.py shell
# import tools
# update_object_with_object('andmebaas', kirje_id_kust_kopeerida, kirje_id_kuhu_kopeerida)
#
def update_object_with_object(model_name='', source_id='', dest_id=''):
    if model_name == 'isik':
        model = Isik
    elif model_name == 'organisatsioon':
        model = Organisatsioon
    elif model_name == 'objekt':
        model = Objekt
    else:
        return

    # Doonorobjekt
    old = model.objects.get(id=source_id)
    print(f'Doonorobjekt: {old.id} {old}')

    # Sihtobjekt
    new = model.objects.get(id=dest_id)
    print(f'Sihtobjekt: {new.id} {new}')

    # Kirjeldus
    sep = '\n\n+++\n\n'
    if old.kirjeldus:
        uus_kirjeldus = sep.join([new.kirjeldus, old.kirjeldus])
        new.kirjeldus = uus_kirjeldus

    # Daatumid
    if old.hist_date:
        if new.hist_date == None:
            new.hist_date = old.hist_date
    else:
        if old.hist_year:
            if new.hist_year == None:
                new.hist_year = old.hist_year
    if old.hist_enddate:
        if new.hist_enddate == None:
            new.hist_enddate = old.hist_enddate
    else:
        if old.hist_endyear:
            if new.hist_endyear == None:
                new.hist_endyear = old.hist_endyear

    # Seotud viited
    viited = old.viited.all()
    print('Viited:')
    for viide in viited:
        print(viide.id, viide)
        new.viited.add(viide)

    # Seotud andmebaasid ja parameetrid
    if model_name == 'isik':
        if old.synd_koht:
            if new.synd_koht == None:
                print(old.synd_koht)
                new.synd_koht = old.synd_koht
        if old.surm_koht:
            if new.surm_koht == None:
                print(old.surm_koht)
                new.surm_koht = old.surm_koht
        if old.maetud:
            if new.maetud == None:
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
    elif model_name == 'organisatsioon':
        if old.hist_date == None:
            if old.hist_month:
                if new.month == None:
                    print(old.month)
                    new.month = old.month
        print('Artiklid:')
        artiklid = Artikkel.objects.filter(organisatsioonid=old)
        for art in artiklid:
            print(art.id, art)
            art.organisatsioonid.add(new)
            # art.organisatsioonid.remove(old)
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
            # pilt.organisatsioonid.remove(old)
    elif model_name == 'objekt':
        if old.hist_date == None:
            if old.hist_month:
                if new.month == None:
                    print(old.month)
                    new.month = old.month
        if old.asukoht:
            if new.asukoht == None:
                print(old.asukoht)
                new.asukoht = old.asukoht
        print('Artiklid:')
        artiklid = Artikkel.objects.filter(objektid=old)
        for art in artiklid:
            print(art.id, art)
            art.objektid.add(new)
            # art.objektid.remove(old)
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
            # pilt.objektid.remove(old)
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
    if not (request.method == 'POST' and check_recaptcha(request)):
        return redirect('wiki:info')

    kuup2ev = request.POST.get('kuup2ev').split('-')

    return HttpResponseRedirect(
        reverse(
            'wiki:artikkel_day_archive',
            kwargs={'year': kuup2ev[0], 'month': kuup2ev[1], 'day': kuup2ev[2]})
        )

#
# Kuupäeva väljalt võetud andmete põhjal suunatakse kuuvaatesse
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

def mainitud_aastatel(qs, model, obj):
    # Artiklites mainimine läbi aastate
    if model == 'Isik':
        filter = qs.filter(isikud__id=obj.id)
    elif model == 'Objekt':
        filter = qs.filter(objektid__id=obj.id)
    elif model == 'Organisatsioon':
        filter = qs.filter(organisatsioonid__id=obj.id)

    aastad = list(filter.all().values_list('hist_year', flat=True).distinct())
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
            'body_text',
            'hist_date', 'dob', 'hist_year', 'hist_month',
            'hist_enddate', 'doe'
        )
        andmed[seotud_object.id] = kirje
    return andmed

#
# Artikli vaatamiseks
#
class ArtikkelDetailView(generic.DetailView):
    model = Artikkel
    query_pk_and_slug = True
    template_name = 'wiki/artikkel_detail.html'

    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)


    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas artiklile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            artiklid__id=self.object.id).filter(profiilipilt_artikkel=True).first()

        # Seotud objectid
        context['seotud_isikud'] = Isik.objects.daatumitega(self.request).filter(
            artikkel=self.object
        )
        context['seotud_organisatsioonid'] = Organisatsioon.objects.daatumitega(self.request).filter(
            artikkel=self.object
        )
        context['seotud_objektid'] = Objekt.objects.daatumitega(self.request).filter(
            artikkel=self.object
        )

        # Järjestame artiklid kronoloogiliselt
        # obj_id = context['artikkel'].id
        # obj = super().get_object()
        # obj_id = self.object.id
        loend = list(artikkel_qs.values_list('id', flat=True))
        # Leiame valitud artikli järjekorranumbri
        n = loend.index(self.object.id)
        # print(n, loend[n-1], loend[n], loend[n+1])
        context['n'] = n
        if n > -1:
            # Leiame ajaliselt järgneva artikli
            if n < (len(loend) - 1):
                context['next_obj'] = artikkel_qs.get(id=loend[n + 1])
            # Leiame ajaliselt eelneva artikli
            if n > 0:
                context['prev_obj'] = artikkel_qs.get(id=loend[n - 1])
        return context

    def get_object(self, **kwargs):
        obj = super().get_object()
        # Record the last accessed date
        obj.last_accessed = timezone.now()
        obj.total_accessed += 1
        obj.save(update_fields=['last_accessed', 'total_accessed'])
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


class KaardiobjektUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Kaardiobjekt
    form_class = KaardiobjektForm

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
            queryset = queryset.annotate(nimi=Concat('isikud__eesnimi', Value(' '), 'isikud__perenimi'))
            fraasid = self.data.get('nimi_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    nimi__icontains=fraas
                )
        return queryset

    def artikkel_sisaldab_filter(self, queryset, name, value):
        # päritud fraas(id) tekstis
        fraasid = self.data.get('artikkel_sisaldab', '').split(' ')
        if len(fraasid) > 0:
            for fraas in fraasid:
                queryset = queryset.filter(
                    body_text__icontains=fraas
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

    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        aasta = context['year'].year
        # Eelnev ja järgnev artikleid sisaldav aasta
        context['aasta_eelmine'] = artikkel_qs.filter(hist_year__lt=aasta).aggregate(Max('hist_year'))['hist_year__max']
        context['aasta_j2rgmine'] = artikkel_qs.filter(hist_year__gt=aasta).aggregate(Min('hist_year'))['hist_year__min']
        
        # Leiame samal aastal sündinud isikud
        isik_qs = Isik.objects.daatumitega(self.request)
        syndinud_isikud = isik_qs.\
            filter(dob__year = aasta).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())).\
            order_by(ExtractMonth('dob'), ExtractDay('dob'))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. aastal sündinud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame selle aasta juubilarid
        syndinud_isikud_date = isik_qs. \
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField()))
        juubilarid_isikud_ids_date = [
            isik.id
            for isik
            in syndinud_isikud_date
            if (isik.dob and isik.vanus_gen > 0 and isik.vanus_gen % 5 == 0)
        ]
        syndinud_isikud_year = isik_qs. \
            filter(hist_date__isnull=True). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        juubilarid_isikud_ids_year = [
            isik.id
            for isik
            in syndinud_isikud_year
            if (isik.hist_year and isik.vanus_gen > 0 and isik.vanus_gen % 5 == 0)
        ]
        juubilarid_isikud_ids = juubilarid_isikud_ids_date + juubilarid_isikud_ids_year
        juubilarid_isikud = isik_qs. \
            filter(id__in=juubilarid_isikud_ids). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField())). \
            order_by('-vanus_gen', ExtractMonth('dob'), ExtractDay('dob'))
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
        loodud_organisatsioonid = organisatsioon_qs. \
            filter(Q(dob__year = aasta) | Q(hist_year = aasta)).\
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField())). \
            order_by(ExtractMonth('dob'), ExtractDay('dob'))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. aastal loodud {1}'.format(
            aasta,
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame selle aasta juubilarid organisatsioonid
        syndinud_organisatsioonid_date = organisatsioon_qs. \
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField()))
        juubilarid_organisatsioonid_ids_date = [
            organisatsioon.id
            for organisatsioon
            in syndinud_organisatsioonid_date
            if (organisatsioon.dob and organisatsioon.vanus_gen > 0 and organisatsioon.vanus_gen % 5 == 0)
        ]
        syndinud_organisatsioonid_year = organisatsioon_qs. \
            filter(hist_date__isnull=True). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        juubilarid_organisatsioonid_ids_year = [
            organisatsioon.id
            for organisatsioon
            in syndinud_organisatsioonid_year
            if (organisatsioon.hist_year and organisatsioon.vanus_gen > 0 and organisatsioon.vanus_gen % 5 == 0)
        ]
        juubilarid_organisatsioonid_ids = juubilarid_organisatsioonid_ids_date + juubilarid_organisatsioonid_ids_year
        juubilarid_organisatsioonid = organisatsioon_qs. \
            filter(id__in=juubilarid_organisatsioonid_ids). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField())). \
            order_by('-vanus_gen', ExtractMonth('dob'), ExtractDay('dob'))
        context['juubilarid_organisatsioonid'] = juubilarid_organisatsioonid
        context['juubilarid_organisatsioonid_pealkiri'] = '{0}. aasta juubilarid {1}'.format(
            aasta,
            Organisatsioon._meta.verbose_name_plural.lower()
        )

        # Leiame samal aastal avatud objektid
        objekt_qs = Objekt.objects.daatumitega(self.request)
        valminud_objektid = objekt_qs. \
            filter(Q(dob__year = aasta) | Q(hist_year = aasta)). \
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField())). \
            order_by(ExtractMonth('dob'), ExtractDay('dob'))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. aastal valminud {1}'.format(
            aasta,
            Objekt._meta.verbose_name_plural.lower()
        )
        # Leiame selle aasta juubilarid objektid
        syndinud_objektid_date = objekt_qs. \
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField()))
        juubilarid_objektid_ids_date = [
            objekt.id
            for objekt
            in syndinud_objektid_date
            if (objekt.dob and objekt.vanus_gen > 0 and objekt.vanus_gen % 5 == 0)
        ]
        syndinud_objektid_year = objekt_qs. \
            filter(hist_date__isnull=True). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        juubilarid_objektid_ids_year = [
            objekt.id
            for objekt
            in syndinud_objektid_year
            if (objekt.hist_year and objekt.vanus_gen > 0 and objekt.vanus_gen % 5 == 0)
        ]
        juubilarid_objektid_ids = juubilarid_objektid_ids_date + juubilarid_objektid_ids_year
        juubilarid_objektid = objekt_qs. \
            filter(id__in=juubilarid_objektid_ids). \
            annotate(vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField())). \
            order_by('-vanus_gen', ExtractMonth('dob'), ExtractDay('dob'))
        context['juubilarid_objektid'] = juubilarid_objektid
        context['juubilarid_objektid_pealkiri'] = '{0}. aasta juubilarid {1}'.format(
            aasta,
            Objekt._meta.verbose_name_plural.lower()
        )
        return context


class ArtikkelMonthArchiveView(MonthArchiveView):
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        return Artikkel.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        aasta = context['month'].year
        kuu = context['month'].month
        p2ev = context['month']
        # Salvestame kasutaja viimase kuupäevavaliku
        self.request.session['user_calendar_view_last'] = f'{aasta}-{kuu}'
        # Samal kuul toimunud
        context['object_list'] = artikkel_qs.\
            filter(hist_year=aasta).\
            filter(Q(dob__month=kuu) | Q(doe__month=kuu) | Q(hist_month=kuu))
        # Leiame samal kuul teistel aastatel märgitud artiklid
        # TODO: 1) hist_year != dob.year ja 2) kui dob ja doe ei ole samal kuul
        sel_kuul = artikkel_qs.\
            exclude(hist_year=aasta).\
            filter(Q(dob__month=kuu)| Q(doe__month=kuu) | Q(hist_month=kuu))
        context['sel_kuul'] = sel_kuul
        # Leiame samal kuul sündinud isikud
        isik_qs = Isik.objects.daatumitega(self.request)
        syndinud_isikud = isik_qs.\
            filter(dob__month = kuu).\
            annotate(vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractDay('dob'))
        context['syndinud_isikud'] = syndinud_isikud
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
        organisatsioon_qs = Organisatsioon.objects.daatumitega(self.request)
        loodud_organisatsioonid = organisatsioon_qs.\
            filter(dob__month = kuu).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractDay('dob'))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0} loodud {1}'.format(
            mis_kuul(kuu),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul avatud objektid
        objekt_qs = Objekt.objects.daatumitega(self.request)
        valminud_objektid = objekt_qs.\
            filter(dob__month = kuu).\
            annotate(vanus_gen=ExpressionWrapper(aasta - ExtractYear('dob'), output_field=IntegerField())). \
            order_by(ExtractDay('dob'))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0} valminud {1}'.format(
            mis_kuul(kuu),
            Objekt._meta.verbose_name_plural.lower()
        )
        return context

def artikkel_month_archive_otheryears(request, year, month):
    artikkel_qs = Artikkel.objects.daatumitega(request)
    sel_kuul = artikkel_qs. \
        exclude(hist_year=year). \
        filter(Q(dob__month=month) | Q(doe__month=month) | Q(hist_month=month))
    return render(request, 'wiki/includes/object_list.html', {'object_list': sel_kuul})

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
            # queryset = (
            #         queryset.filter(
            #             perenimi__icontains=self.data['nimi_sisaldab']
            #         ) |
            #         queryset.filter(
            #             eesnimi__icontains=self.data['nimi_sisaldab']
            #         )
            # )
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
        return context


class IsikDetailView(generic.DetailView):
    model = Isik
    query_pk_and_slug = True

    def get_queryset(self):
        return Isik.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)

        # Kas isikule on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.\
            filter(isikud__id=self.object.id).\
            filter(profiilipilt_isik=True).\
            first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel(artikkel_qs, 'Isik', self.object)
        # Otseseosed objektidega
        context['seotud_organisatsioonid'] = Organisatsioon.objects.daatumitega(self.request).filter(
            isik=self.object)
        context['seotud_objektid'] = Objekt.objects.daatumitega(self.request).filter(isik=self.object)
        # Artikli kaudu seotud objects lisab ajax func object_detail_seotud()
        return context

#
# object detailvaates ajax seotud objectide kuvamiseks
#
def object_detail_seotud(request, model, id):
    context = {
        'model': model
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
        return context


class OrganisatsioonDetailView(generic.DetailView):
    model = Organisatsioon
    query_pk_and_slug = True

    def get_queryset(self):
        return Organisatsioon.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas organisatsioonile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            organisatsioonid__id=self.object.id).filter(profiilipilt_organisatsioon=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel(artikkel_qs, 'Organisatsioon', self.object)
        # Otseseosed objectidega
        # isik_related = self.object.isik_set.all().values_list('id', flat=True)
        # context['seotud_isikud'] = Isik.objects.daatumitega(self.request).filter(id__in=isik_related)
        context['seotud_isikud'] = Isik.objects.daatumitega(self.request).filter(
            organisatsioonid=self.object
        )
        context['seotud_objektid'] = Objekt.objects.daatumitega(self.request).filter(organisatsioon__id=self.object.id)
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

    def nimi_sisaldab_filter(self, queryset, name, value):
        # päritud fraas nimes
        if self.data.get('nimi_sisaldab'):
            fraasid = self.data.get('nimi_sisaldab', '').split(' ')
            for fraas in fraasid:
                queryset = queryset.filter(
                    nimi__icontains=fraas
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
        return context

class ObjektDetailView(generic.DetailView):
    model = Objekt
    query_pk_and_slug = True

    def get_queryset(self):
        return Objekt.objects.daatumitega(self.request)

    def get_context_data(self, **kwargs):
        artikkel_qs = Artikkel.objects.daatumitega(self.request)
        context = super().get_context_data(**kwargs)
        # Kas objektile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.\
            filter(objektid__id=self.object.id).\
            filter(profiilipilt_objekt=True).\
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
        context['mainitud_aastatel'] = mainitud_aastatel(artikkel_qs, 'Objekt', self.object)
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
        # Artikli kaudu seotud objects lisab ajax func object_detail_seotud()
        return context


# objectide nimel hiirega peatudes infoakna kuvamiseks
def get_object_data4tooltip(request):
    model_name = request.GET.get('model')
    id = request.GET.get('obj_id')
    model = apps.get_model('wiki', model_name)
    # print(model, id)
    obj = model.objects.get(id=id)
    if obj.kirjeldus:
        heading = f'<strong>{obj}</strong>'
        if obj.profiilipilt():
            img = settings.MEDIA_URL + obj.profiilipilt().pilt_thumbnail.name
            img = f'<img class="tooltip-content-img" src="{img}" alt="{obj.profiilipilt()}">'
        else:
            img = ''
        content = f'<div><p>{heading}</p><p>{img}<small>{obj.kirjeldus_lyhike}</small><p></div>'
    else:
        content = str(obj)
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
def test(request):
    valik = request.META['QUERY_STRING']
    # TODO: Saata tühi vastus, kui pole konkreetset valikut
    data = dict()
    # Artiklite testandmed
    artikkel_qs = Artikkel.objects.daatumitega(request)
    data['test_url_artiklid_id'] = [
        reverse('wiki:wiki_artikkel_detail', kwargs={'pk': obj.id, 'slug': obj.slug})
        for obj
        in artikkel_qs
    ]
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

def switch_vkj_ukj(request, ukj):
    # print('switch2:', ukj)
    # print('before switch', request.session.get('ukj'))
    request.session['ukj'] = ukj
    # print('after switch', request.session.get('ukj'))
    return HttpResponse(ukj)

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
    artikkel_qs = Artikkel.objects.daatumitega(request).exclude(hist_date__isnull=True)
    t2na = timezone.now()

    # Kasutaja kuuvalik
    year = request.GET.get('year', t2na.year - 100)
    month = request.GET.get('month', t2na.month)

    # Salvestame kasutaja kuuvaliku
    user_calendar_view_last = date(int(year), int(month), 1).strftime("%Y-%m")
    request.session['user_calendar_view_last'] = user_calendar_view_last

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
            # annotate(day=Extract('hist_date', 'month')).
            # values_list('hist_month', flat=True)
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

def kaart(request, aasta=None):
    map_html = make_big_maps_leaflet(aasta)
    return render(
        request,
        'wiki/kaart.html',
        {'kaart': map_html},
    )

# Tagastab objekti kõigi olemasolevate aastate kaardid
def get_objekt_leaflet_combo(request, objekt_id):
    map_html = make_objekt_leaflet_combo(objekt_id)
    return HttpResponse(map_html)

def get_kaardiobjekt_leaflet(request, kaardiobjekt_id):
    map_html = make_kaardiobjekt_leaflet(kaardiobjekt_id)
    return HttpResponse(map_html)