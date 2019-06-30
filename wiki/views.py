from collections import Counter, OrderedDict
import datetime
import requests
from typing import Dict, Any

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, BooleanField, DecimalField, IntegerField, ExpressionWrapper
from django.db.models import Count, Max, Min
from django.db.models.functions import ExtractYear
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_list_or_404, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from django.views.generic.dates import ArchiveIndexView, YearArchiveView, MonthArchiveView, DayArchiveView
from django.views.generic.edit import UpdateView

import django_filters
from django_filters.views import FilterView

from .models import Allikas, Artikkel, Isik, Objekt, Organisatsioon, Pilt
from .forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm #, FeedBackForm
from .forms import VihjeForm
#
# reCAPTCHA kontrollifunktsioon
#
def check_recaptcha(request):
    data = request.POST

    # get the token submitted in the form
    recaptcha_response = data.get('g-recaptcha-response')
    print(settings.GOOGLE_RECAPTCHA_SECRET_KEY)
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
# Avalehekülg
#
def info(request):
    andmebaasid = []
    andmebaasid.append(' '.join(['Allikad: ', str(Allikas.objects.count()), 'kirjet']))
    andmebaasid.append(
        ' '.join(
            [
                'Artikkel: ',
                f'kirjeid {Artikkel.objects.count()} ',
                f'viidatud {Artikkel.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Artikkel.objects.filter(pilt__isnull=False).distinct().count()} '
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
    andmed = Artikkel.objects.aggregate(Count('id'), Min('hist_searchdate'), Max('hist_searchdate'))
    # TODO: Ajutine ümberkorraldamiseks
    revision_data: Dict[str, Any] = {}
    revision_data['kroonika'] = Artikkel.objects.filter(kroonika__isnull=False).count()
    revision_data['revised'] = Artikkel.objects.filter(kroonika__isnull=False).annotate(num_viited=Count('viited')).filter(num_viited__gt=1).count()
    revision_data['viiteta'] = list(Artikkel.objects.filter(viited__isnull=True).values_list('id', flat=True))

    return render(
        request,
        'wiki/wiki-info.html',
        {
            'andmebaasid': andmebaasid,
            'andmed': andmed,
            # 'recaptcha_key': settings.GOOGLE_RECAPTCHA_PUBLIC_KEY,
            'revision_data': revision_data, # TODO: Ajutine ümberkorraldamiseks
        }
    )

#
# Tagasiside vormi töötlemine
#
def feedback(request):
    # if this is a POST request we need to process the form data
    http_referer = request.META['HTTP_REFERER']
    if request.method == 'POST' and check_recaptcha(request):
        # create a form instance and populate it with data from the request:
        form = VihjeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            vihje = {
                'kirjeldus': form.cleaned_data['kirjeldus'],
                'kontakt': form.cleaned_data['kontakt']
            }
            from django.utils.version import get_version
            context = {
                'django_version': f'Django: {get_version()}',
                'meta': request.META,
                'vihje': vihje,
                'http_referer': http_referer
            }
            return render(
                request,
                'wiki/wiki_feedback.html',
                context
            )

    # Kui on GET või tühi vorm, siis laeme algse lehe
    return HttpResponseRedirect(http_referer)

#
# Avakuva
#
def algus(request):
    andmed = {} # Selle muutuja saadame veebi
    p2ev = datetime.date.today().day
    kuu = datetime.date.today().month
    aasta = datetime.date.today().year
    
    # Andmebaas Artikkel andmed veebi
    a = dict()
    kirjeid = Artikkel.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Artikkel.objects.all().\
            aggregate(
            max_inp_date=Max('inp_date'),
            max_mod_date=Max('mod_date')
        )
        a['viimane_lisatud'] = Artikkel.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Artikkel.objects.filter(mod_date=kp['max_mod_date'])[0]
        # Samal kuupäeval erinevatel aastatel toimunud
        sel_p2eval = Artikkel.objects.filter(
            hist_date__day = p2ev,
            hist_date__month = kuu
        )
        sel_p2eval_kirjeid = len(sel_p2eval)
        if sel_p2eval_kirjeid > 5: # Kui leiti rohkem kui viis kirjet võetakse 2 algusest + 1 keskelt + 2 lõpust
            a['sel_p2eval'] = sel_p2eval[:2] + sel_p2eval[int(sel_p2eval_kirjeid/2-1):int(sel_p2eval_kirjeid/2)] + sel_p2eval[sel_p2eval_kirjeid-2:]
        else:
            a['sel_p2eval'] = sel_p2eval
        a['sel_p2eval_kirjeid'] = sel_p2eval_kirjeid
        # Samal päeval ja kuul toimunud
        sel_kuul = Artikkel.objects.filter(hist_searchdate__month = kuu)
        sel_kuul_kirjeid = len(sel_kuul)
        if sel_kuul_kirjeid > 5: # Kui leiti rohkem kui viis kirjet võetakse 2 algusest + 1 keskelt + 2 lõpust
            a['sel_kuul'] = sel_kuul[:2] + sel_kuul[int(sel_kuul_kirjeid/2-1):int(sel_kuul_kirjeid/2)] + sel_kuul[sel_kuul_kirjeid-2:]
        else:
            a['sel_kuul'] = sel_kuul
        a['sel_kuul_kirjeid'] = sel_kuul_kirjeid
    andmed['artikkel'] = a

    # Andmebaas Isik andmed veebi
    a = dict()
    kirjeid = Isik.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Isik.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        a['viimane_lisatud'] = Isik.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Isik.objects.filter(mod_date=kp['max_mod_date'])[0]
        a['sel_p2eval'] = Isik.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Isik.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        a['sel_p2eval_surnud'] = Isik.objects.filter(hist_enddate__day = p2ev, hist_enddate__month = kuu)
        a['sel_p2eval_surnud_kirjeid'] = len(a['sel_p2eval_surnud'])
        a['sel_kuul_surnud'] = Isik.objects.filter(hist_enddate__month = kuu).order_by('hist_enddate__day')
        a['sel_kuul_surnud_kirjeid'] = len(a['sel_kuul_surnud'])
        juubilarid = Isik.objects.exclude(hist_date=None).annotate(
            nulliga=ExpressionWrapper(
                (datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
            vanus_gen=ExpressionWrapper(
                    datetime.date.today().year - ExtractYear('hist_date'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        a['juubilarid'] = juubilarid
    andmed['isik'] = a

    # Andmebaas Organisatsioon andmed veebi
    a = dict()
    kirjeid = Organisatsioon.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Organisatsioon.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        a['viimane_lisatud'] = Organisatsioon.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Organisatsioon.objects.filter(mod_date=kp['max_mod_date'])[0]
        a['sel_p2eval'] = Organisatsioon.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Organisatsioon.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = Organisatsioon.objects.exclude(hist_year=None).annotate(
            nulliga=ExpressionWrapper(
                (datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()), vanus_gen=ExpressionWrapper(
                    datetime.date.today().year - F('hist_year'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        a['juubilarid'] = juubilarid
    andmed['organisatsioon'] = a
    
    # Andmebaas Objekt andmed veebi
    a = dict()
    kirjeid = Objekt.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Objekt.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        a['viimane_lisatud'] = Objekt.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Objekt.objects.filter(mod_date=kp['max_mod_date'])[0]
        a['sel_p2eval'] = Objekt.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Objekt.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = Objekt.objects.exclude(hist_year=None).annotate(
            nulliga=ExpressionWrapper(
                (datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()), vanus_gen=ExpressionWrapper(
                    datetime.date.today().year - F('hist_year'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        a['juubilarid'] = juubilarid
    andmed['objekt'] = a
    
    return render(request, 'wiki/wiki.html', {'andmed': andmed})


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


def mainitud_aastatel(model, obj):
    # Artiklites mainimine läbi aastate
    if model == 'Isik':
        qs = Artikkel.objects.filter(isikud__id=obj.id)
    elif model == 'Objekt':
        qs = Artikkel.objects.filter(objektid__id=obj.id)
    elif model == 'Organisatsioon':
        qs = Artikkel.objects.filter(organisatsioonid__id=obj.id)

    aastad = list(qs.all().values_list('hist_year', flat=True).distinct())
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
    template_name = 'wiki/artikkel_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Kas artiklile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            artiklid__id=self.object.id).filter(profiilipilt_artikkel=True).first()
        kuup2ev = context['artikkel'].hist_searchdate
        obj_id = context['artikkel'].id
        # Järjestame artiklid kronoloogiliselt
        loend = Artikkel.objects.order_by('hist_searchdate', 'id').values('id')
        # Leiame valitud artikli järjekorranumbri
        n = next((i for i, x in enumerate(loend) if x['id'] == obj_id), -1)
        context['n'] = n
        if n > -1:
            # Leiame ajaliselt järgneva artikli
            if n < Artikkel.objects.count() - 1:
                context['next_obj'] = Artikkel.objects.get(id=loend[n+1]['id'])
            # Leiame ajaliselt eelneva artikli
            if n > 0:
                context['prev_obj'] = Artikkel.objects.get(id=loend[n-1]['id'])
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
        return redirect('wiki:wiki_artikkel_detail', pk=self.object.id)


class IsikUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Isik
    pk_url_kwarg = 'pk'
    form_class = IsikForm
    
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
        return redirect('wiki:wiki_isik_detail', pk=self.object.id)


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
        return redirect('wiki:wiki_organisatsioon_detail', pk=self.object.id)
    
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
        return redirect('wiki:wiki_objekt_detail', pk=self.object.id)

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
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()


#
# Artiklite otsimise/filtreerimise vaade
#
class ArtikkelFilterView(FilterView):
    model = Artikkel
    paginate_by = 10
    template_name = 'wiki/artikkel_filter.html'
    filterset_fields = {
            'hist_year',
            'body_text',
            'isikud__perenimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list = Artikkel.objects.all().order_by('hist_searchdate')
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
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
            

#
# Kronoloogia
#
class ArtikkelArchiveIndexView(ArchiveIndexView):
    queryset = Artikkel.objects.all()
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    paginate_by = 20
    ordering = ('hist_searchdate', 'id')

class ArtikkelYearArchiveView(YearArchiveView):
    queryset = Artikkel.objects.all()
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    ordering = ('hist_searchdate', 'id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aasta = context['year'].year
        # Eelnev ja järgnev artikleid sisaldav aasta
        context['aasta_eelmine'] = Artikkel.objects.filter(hist_year__lt=aasta).aggregate(Max('hist_year'))['hist_year__max']
        context['aasta_j2rgmine'] = Artikkel.objects.filter(hist_year__gt=aasta).aggregate(Min('hist_year'))['hist_year__min']
        
        # Leiame samal aastal sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__year = aasta).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. aastal sündinud isikud'.format(aasta)
        # Leiame samal aastal surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__year = aasta).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. aastal surnud isikud'.format(aasta)
        # Leiame samal aastal loodud organisatsioonid
        loodud_organisatsioonid = (
            Organisatsioon.objects.filter(hist_date__year = aasta) | Organisatsioon.objects.filter(hist_year = aasta)).distinct().annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. aastal loodud organisatsioonid'.format(aasta)
        # Leiame samal aastal avatud objektid
        valminud_objektid = (
            Objekt.objects.filter(hist_date__year = aasta) | Objekt.objects.filter(hist_year = aasta)).distinct().annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. aastal valminud objektid'.format(aasta)
        
        return context


class ArtikkelMonthArchiveView(MonthArchiveView):
    queryset = Artikkel.objects.all()
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 10
    ordering = ('hist_searchdate', 'id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aasta = context['month'].year
        kuu = context['month'].month
        p2ev = context['month']
        # Leiame samal kuul teistel aastatel märgitud artiklid
        sel_kuul = Artikkel.objects.exclude(hist_searchdate__year = aasta).filter(hist_searchdate__month = kuu)
        context['sel_kuul'] = sel_kuul
        # Leiame samal kuul sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0} sündinud isikud'.format(mis_kuul(kuu))
        # Leiame samal kuul surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0} surnud isikud'.format(mis_kuul(kuu))
        # Leiame samal kuul loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0} loodud organisatsioonid'.format(mis_kuul(kuu))
        # Leiame samal kuul avatud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0} valminud objektid'.format(mis_kuul(kuu))
        return context
    
class ArtikkelDayArchiveView(DayArchiveView):
    queryset = Artikkel.objects.all()
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aasta = context['day'].year
        kuu = context['day'].month
        p2ev = context['day'].day
        # Leiame samal kuupäeval teistel aastatel märgitud artiklid
        sel_p2eval = Artikkel.objects.exclude(hist_searchdate__year = aasta).filter(hist_date__month = kuu, hist_date__day = p2ev)
        context['sel_p2eval'] = sel_p2eval
        # Leiame samal kuupäeval sündinud isikud
        syndinud_isikud = Isik.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. {1} sündinud isikud'.format(p2ev, mis_kuul(kuu, 'l'))
        # Leiame samal kuupäeval surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu, hist_enddate__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. {1} surnud isikud'.format(p2ev, mis_kuul(kuu, 'l'))
        # Leiame samal kuupäeval loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. {1} loodud organisatsioonid'.format(p2ev, mis_kuul(kuu, 'l'))
        # Leiame samal kuupäeval loodud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. {1} valminud objektid'.format(p2ev, mis_kuul(kuu, 'l'))
        
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

##    def __init__(self, *args, **kwargs):
##        super(IsikFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()


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
        list = Isik.objects.all().annotate(
            nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField())).order_by('perenimi')
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
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
    

def seotud_isikud_artiklikaudu(seotud_artiklid, isik_ise):
    # Isikuga artiklite kaudu seotud teised isikud
    isikud = Isik.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().all().exclude(pk=isik_ise)
    andmed = {}
    for seotud_isik in isikud:
        kirje = {}
        kirje['id'] = seotud_isik.id
        kirje['perenimi'] = seotud_isik.perenimi
        kirje['eesnimi'] = seotud_isik.eesnimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(isikud=seotud_isik).\
            order_by('hist_searchdate').\
            values('id', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_isik.id] = kirje
    return andmed
        

class IsikDetailView(generic.DetailView):
    model = Isik

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Kas isikule on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            isikud__id=self.object.id).filter(profiilipilt_isik=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel('Isik', self.object)

        # Isikuga seotud artiklid
        seotud_artiklid = Artikkel.objects.filter(isikud__id=self.object.id)
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
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
    
def seotud_organisatsioonid_artiklikaudu(seotud_artiklid, organisatsiooni_ise):
    # Isikuga artiklite kaudu seotud organisatsioonid
    organisatsioonid = Organisatsioon.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().all().exclude(pk=organisatsiooni_ise)
    andmed = {}
    for seotud_organisatsioon in organisatsioonid:
        kirje = {}
        kirje['id'] = seotud_organisatsioon.id
        kirje['nimi'] = seotud_organisatsioon.nimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(organisatsioonid=seotud_organisatsioon).\
            order_by('hist_searchdate').\
            values('id', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_organisatsioon.id] = kirje
    return andmed


class OrganisatsioonDetailView(generic.DetailView):
    model = Organisatsioon

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Kas organisatsioonile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            organisatsioonid__id=self.object.id).filter(profiilipilt_organisatsioon=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel('Organisatsioon', self.object)

        # Organisatsiooniga seotud artiklid
        seotud_artiklid = Artikkel.objects.filter(organisatsioonid__id=self.object.id)

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
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
    
def seotud_objektid_artiklikaudu(seotud_artiklid, objekt_ise):
    # Objektiga artiklite kaudu seotud organisatsioonid
    objektid = Objekt.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().all().exclude(pk=objekt_ise)
    andmed = {}
    for seotud_objekt in objektid:
        kirje = {}
        kirje['id'] = seotud_objekt.id
        kirje['nimi'] = seotud_objekt.nimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(objektid=seotud_objekt).\
            order_by('hist_searchdate').\
            values('id', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_objekt.id] = kirje
    return andmed
    
class ObjektDetailView(generic.DetailView):
    model = Objekt

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Kas objektile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            objektid__id=self.object.id).filter(profiilipilt_objekt=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel('Objekt', self.object)

        # Objektiga seotud artiklid
        seotud_artiklid = Artikkel.objects.filter(objektid__id=self.object.id)
        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        context['feedbackform'] = VihjeForm()
        return context


# Loendab kõik sisse logitud kasutajad
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
