from collections import Counter, OrderedDict
import datetime
import requests
from typing import Dict, Any

from django.conf import settings
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Q, Value, BooleanField, DecimalField, IntegerField, ExpressionWrapper
from django.db.models import Count, Max, Min
from django.db.models.functions import ExtractYear
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

from .models import Allikas, Viide, Artikkel, Isik, Objekt, Organisatsioon, Pilt, Vihje
from .forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm
from .forms import VihjeForm

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
# Kontrollitakse kasutajat
#
def artikkel_qs_userfilter(user):
    if user.is_authenticated:
        if user.is_staff: # näita kõike
            return Artikkel.objects.all()
    else: # kasuta filtrit
        return Artikkel.objects.filter(kroonika__isnull=True)


#
# Avalehekülg
#
def info(request):
    # Filtreerime artiklite hulga kasutaja järgi
    artikkel_qs = artikkel_qs_userfilter(request.user)
    andmebaasid = []
    # Allikad ja viited
    tyhjad_viited = Viide.objects.annotate(
        num_art=Count('artikkel__id'),
        num_isik=Count('isik__id'),
        num_org=Count('organisatsioon__id'),
        num_obj=Count('objekt__id'),
        num_pilt=Count('pilt__id')
    ).filter(
        num_art=0, num_isik=0, num_org=0, num_obj=0, num_pilt=0
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
        [periood['hist_searchdate__year'], periood['hist_searchdate__month'], periood['ct']] for periood in perioodid
    ]
    if artikleid_kuus:
        artikleid_kuus_max = max([kuu_andmed[2] for kuu_andmed in artikleid_kuus])
    else:
        artikleid_kuus_max = 1 # kui ei ole artikleid sisestatud
    # TODO: Ajutine ümberkorraldamiseks
    revision_data: Dict[str, Any] = {}
    revision_data['kroonika'] = artikkel_qs.filter(kroonika__isnull=False).count()
    revision_data['revised'] = [
        obj.id
        for obj
        in artikkel_qs.filter(kroonika__isnull=False).annotate(num_viited=Count('viited')).filter(num_viited__gt=1)
    ]
     # revision_data['viiteta'] = list(artikkel_qs.filter(viited__isnull=True).values_list('id', flat=True))
    revision_data['viiteta'] = artikkel_qs.filter(viited__isnull=True)

    return render(
        request,
        'wiki/wiki_info.html',
        {
            'andmebaasid': andmebaasid,
            'andmed': andmed,
            'artikleid_kuus': artikleid_kuus,
            'artikleid_kuus_max': artikleid_kuus_max,
            'meta_andmed': request.META,
            # 'recaptcha_key': settings.GOOGLE_RECAPTCHA_PUBLIC_KEY,
            'revision_data': revision_data, # TODO: Ajutine ümberkorraldamiseks
        }
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
    if request.method == 'POST': # TODO: and check_recaptcha(request):
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
    artikkel_qs = artikkel_qs_userfilter(request.user)
    andmed = {} # Selle muutuja saadame veebi
    p2ev = datetime.date.today().day # str(p2ev).zfill(2) -> PP
    kuu = datetime.date.today().month # str(kuu).zfill(2) -> KK
    aasta = datetime.date.today().year
    
    # Andmebaas Artikkel andmed veebi
    a = dict()
    kirjeid = artikkel_qs.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        # kp = Artikkel.objects.all().\
        #     aggregate(
        #     max_inp_date=Max('inp_date'),
        #     max_mod_date=Max('mod_date')
        # )
        # a['viimane_lisatud'] = Artikkel.objects.filter(inp_date=kp['max_inp_date']).last()
        a['viimane_lisatud'] = artikkel_qs.latest('inp_date')
        # a['viimane_muudetud'] = Artikkel.objects.filter(mod_date=kp['max_mod_date']).last()
        a['viimane_muudetud'] = artikkel_qs.latest('mod_date')
        # Samal kuupäeval erinevatel aastatel toimunud
        sel_p2eval_exactly = artikkel_qs.filter( # hist_date == KKPP
            hist_date__day = p2ev,
            hist_date__month = kuu
        )
        sel_p2eval_inrange = inrange_dates_artikkel(artikkel_qs, p2ev, kuu) # hist_date < KKPP <= hist_enddate
        sel_p2eval = sel_p2eval_exactly | sel_p2eval_inrange
        sel_p2eval_kirjeid = len(sel_p2eval)
        if sel_p2eval_kirjeid > 5: # Kui leiti rohkem kui viis kirjet võetakse 2 algusest + 1 keskelt + 2 lõpust
            a['sel_p2eval'] = sel_p2eval[:2] + sel_p2eval[int(sel_p2eval_kirjeid/2-1):int(sel_p2eval_kirjeid/2)] + sel_p2eval[sel_p2eval_kirjeid-2:]
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
    andmed['artikkel'] = a

    # Andmebaas Isik andmed veebi
    a = dict()
    kirjeid = Isik.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        # kp = Isik.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        # a['viimane_lisatud'] = Isik.objects.filter(inp_date=kp['max_inp_date']).last()
        a['viimane_lisatud'] = Isik.objects.latest('inp_date')
        # a['viimane_muudetud'] = Isik.objects.filter(mod_date=kp['max_mod_date']).last()
        a['viimane_muudetud'] = Isik.objects.latest('mod_date')
        a['100_aastat_tagasi'] = Isik.objects.filter(
            hist_date__day = p2ev,
            hist_date__month = kuu,
            hist_date__year = (aasta-100)
        )
        a['sel_p2eval'] = Isik.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Isik.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        a['sel_p2eval_surnud'] = Isik.objects.filter(hist_enddate__day = p2ev, hist_enddate__month = kuu)
        a['sel_p2eval_surnud_kirjeid'] = len(a['sel_p2eval_surnud'])
        a['sel_kuul_surnud'] = Isik.objects.filter(hist_enddate__month = kuu).order_by('hist_enddate__day')
        a['sel_kuul_surnud_kirjeid'] = len(a['sel_kuul_surnud'])
        # juubilarid = Isik.objects.exclude(hist_date=None).annotate(
        #     nulliga=ExpressionWrapper(
        #         (datetime.date.today().year - ExtractYear('hist_date'))%5,
        #         output_field=IntegerField()),
        #     vanus_gen=ExpressionWrapper(
        #         datetime.date.today().year - ExtractYear('hist_date'),
        #         output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        # isikud_synniajaga = Isik.objects.exclude(hist_date=None).annotate(
        #     vanus_gen=ExpressionWrapper(
        #         datetime.date.today().year - ExtractYear('hist_date'),
        #         output_field=IntegerField()
        #     )
        # )
        isikud_synniajaga = Isik.objects.exclude(
            hist_date__isnull=True,
            hist_year__isnull=True
        )
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
        #         (datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()), vanus_gen=ExpressionWrapper(
        #             datetime.date.today().year - F('hist_year'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
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
        #         (datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
        #     vanus_gen=ExpressionWrapper(
        #             datetime.date.today().year - (ExtractYear('hist_date') if 'hist_date' else F('hist_year')), output_field=IntegerField())).filter(nulliga=0).order_by('hist_year')
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
    return render(request, 'wiki/wiki.html', {'andmed': andmed})


#
# Tagastab kõik artiklid, kus hist_date < KKPP <= hist_enddate vahemikus
#
def inrange_dates_artikkel(qs, p2ev, kuu):
    # Vaatleme ainult algus ja lõpuajaga ridasid
    q = qs.filter(
        hist_date__isnull=False,
        hist_enddate__isnull=False
    )
    # Jätame välja read, kus hist_date == KKPP
    q = q.exclude(
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
        return artikkel_qs_userfilter(self.request.user)

    def get_context_data(self, **kwargs):
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
        context = super().get_context_data(**kwargs)
        # Kas artiklile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            artiklid__id=self.object.id).filter(profiilipilt_artikkel=True).first()
        # kuup2ev = context['artikkel'].hist_searchdate
        obj_id = context['artikkel'].id
        # Järjestame artiklid kronoloogiliselt
        loend = list(artikkel_qs.values_list('id', flat=True))
        # Leiame valitud artikli järjekorranumbri
        # n = next((i for i, x in enumerate(loend) if x['id'] == obj_id), -1)
        n = loend.index(obj_id)
        context['n'] = n
        if n > -1:
            # Leiame ajaliselt järgneva artikli
            if n < (len(loend) - 1):
                context['next_obj'] = artikkel_qs.get(id=loend[n + 1])
                # context['next_obj'] = artikkel_qs.get(id=loend[n+1]['id'])
            # Leiame ajaliselt eelneva artikli
            if n > 0:
                context['prev_obj'] = artikkel_qs.get(id=loend[n - 1])
                # context['prev_obj'] = artikkel_qs.get(id=loend[n-1]['id'])
        # Lisame vihjevormi
        context['feedbackform'] = VihjeForm()
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
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
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
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
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
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
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
    
    class Meta:
        model = Artikkel
        fields = {
            'hist_year': ['exact'],
            'body_text': ['icontains'],
            'isikud__perenimi': ['icontains'],
            }

    def __init__(self, *args, **kwargs):
        super(ArtikkelFilter, self).__init__(*args, **kwargs)
        # at startup user doesn't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()

    @property
    def qs(self, *args, **kwargs):
        # küsime algse päringu
        # initial_qs = super(ArtikkelFilter, self).qs
        # päringu parameetrid
        fraasid = self.data.get('body_text__icontains', '').split(' ')
        if len(fraasid) > 1:
            # modified_qs = Artikkel.objects.all()
            modified_qs = artikkel_qs_userfilter(self.request.user)
            if self.data.get('hist_year__exact'):
                modified_qs = modified_qs.filter(
                    hist_year__exact=self.data['hist_year__exact']
                )
            if self.data.get('isikud__perenimi__icontains'):
                modified_qs = modified_qs.filter(
                    isikud__perenimi__icontains=self.data['isikud__perenimi__icontains']
                )
            for fraas in fraasid:
                modified_qs = modified_qs.filter(
                    body_text__icontains=fraas
                )
        else:
            modified_qs = super(ArtikkelFilter, self).qs
        # author = getattr(self.request, 'user', None)
        return modified_qs


#
# Artiklite otsimise/filtreerimise vaade
#
class ArtikkelFilterView(FilterView):
    model = Artikkel
    paginate_by = 20
    template_name = 'wiki/artikkel_filter.html'
    filterset_fields = {
            'hist_year',
            'body_text',
            'isikud__perenimi',
            }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list = artikkel_qs_userfilter(self.request.user)
        filter = ArtikkelFilter(self.request.GET, queryset=list)
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
        # context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
            

#
# Kronoloogia
#
class ArtikkelArchiveIndexView(ArchiveIndexView):
    # queryset = Artikkel.objects.all()
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        return artikkel_qs_userfilter(self.request.user)

class ArtikkelYearArchiveView(YearArchiveView):
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        return artikkel_qs_userfilter(self.request.user)

    def get_context_data(self, **kwargs):
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
        context = super().get_context_data(**kwargs)
        aasta = context['year'].year
        # Eelnev ja järgnev artikleid sisaldav aasta
        context['aasta_eelmine'] = artikkel_qs.filter(hist_year__lt=aasta).aggregate(Max('hist_year'))['hist_year__max']
        context['aasta_j2rgmine'] = artikkel_qs.filter(hist_year__gt=aasta).aggregate(Min('hist_year'))['hist_year__min']
        
        # Leiame samal aastal sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__year = aasta).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. aastal sündinud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__year = aasta).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. aastal surnud {1}'.format(
            aasta,
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal loodud organisatsioonid
        loodud_organisatsioonid = (
            Organisatsioon.objects.filter(hist_date__year = aasta) | Organisatsioon.objects.filter(hist_year = aasta)).distinct().annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. aastal loodud {1}'.format(
            aasta,
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal aastal avatud objektid
        valminud_objektid = (
            Objekt.objects.filter(hist_date__year = aasta) | Objekt.objects.filter(hist_year = aasta)).distinct().annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. aastal valminud {1}'.format(
            aasta,
            Objekt._meta.verbose_name_plural.lower()
        )
        
        return context


class ArtikkelMonthArchiveView(MonthArchiveView):
    # queryset = Artikkel.objects.all()
    date_field = 'hist_date'
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    # ordering = ('hist_searchdate', 'id')

    def get_queryset(self):
        return artikkel_qs_userfilter(self.request.user)

    def get_context_data(self, **kwargs):
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
        context = super().get_context_data(**kwargs)
        aasta = context['month'].year
        kuu = context['month'].month
        p2ev = context['month']
        # Leiame samal kuul teistel aastatel märgitud artiklid TODO: probleem kui hist_searchdate__month ja hist_enddate__month ei ole järjest
        sel_kuul = artikkel_qs.exclude(hist_searchdate__year = aasta).filter(Q(hist_date__month = kuu) | Q(hist_enddate__month = kuu))
        context['sel_kuul'] = sel_kuul
        # Leiame samal kuul sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__month = kuu).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0} sündinud {1}'.format(
            mis_kuul(kuu),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0} surnud {1}'.format(
            mis_kuul(kuu),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0} loodud {1}'.format(
            mis_kuul(kuu),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuul avatud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
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
        return artikkel_qs_userfilter(self.request.user)

    def get_context_data(self, **kwargs):
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
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
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. {1} sündinud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu, hist_enddate__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. {1} surnud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Isik._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. {1} loodud {2}'.format(
            p2ev,
            mis_kuul(kuu, 'l'),
            Organisatsioon._meta.verbose_name_plural.lower()
        )
        # Leiame samal kuupäeval loodud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                # nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
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
        list = Isik.objects.all().order_by('perenimi')
        filter = IsikFilter(self.request.GET, queryset=list)
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
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
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
        context['feedbackform'] = VihjeForm()
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
        list = Organisatsioon.objects.all().annotate(
            nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField())).order_by('nimi')
        filter = OrganisatsioonFilter(self.request.GET, queryset=list)
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
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
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
        context['feedbackform'] = VihjeForm()
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
        list = Objekt.objects.all().annotate(
            nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField())).order_by('nimi')
        filter = ObjektFilter(self.request.GET, queryset=list)
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
        artikkel_qs = artikkel_qs_userfilter(self.request.user)
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
        context['feedbackform'] = VihjeForm()
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
    data = dict()
    data['meta_server_addr'] = request.META['SERVER_ADDR']
    # Artiklite testandmed
    artikkel_qs = artikkel_qs_userfilter(request.user)
    data['test_url_artiklid_id'] = [
        reverse('wiki:wiki_artikkel_detail', kwargs={'pk': obj.id})
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
    return JsonResponse(data, safe=False)
