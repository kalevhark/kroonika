from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
import glob
import json
import os
from pathlib import Path, PurePath
import shutil
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

if __name__ == "__main__":
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()

from django.conf import settings

MEDIA_DIR = settings.MEDIA_ROOT


from django.db.models import (
    Case, F, Q, Value, When,
    BooleanField, DateField, DateTimeField, DecimalField, IntegerField,
    ExpressionWrapper
)
from django.db.models.functions import Extract, Trunc, ExtractDay

from wiki.models import (
    Artikkel, Isik, Organisatsioon, Objekt, Pilt,
    Kaardiobjekt,
    Viide, Allikas
)

# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value.strip().replace(',', '.'))
    except:
        return None



# ühekordne fn lähteandmete korjamiseks massikande jaoks ariklitest
def get_data4massikanne():
    ids = [5080, 5268, 5273, 5277, 5274, 5278, 5399, 5400, 5402, 5545, 5546, 5609]
    with open(f'20200413_massikanne.txt', 'w', encoding = 'UTF-8') as f:
        for id in ids:
            art = Artikkel.objects.get(id=id)

            f.write(f'{art.hist_searchdate.year} {art.body_text}\n')
            f.write(f'art {art.id}\n')
            f.write(f'pil {[pilt.id for pilt in art.pilt_set.all()][0]}\n')
            f.write(f'org {[org.id for org in art.organisatsioonid.all()][0]}\n')
            f.write(f'vii {[viide.id for viide in art.viited.all()][0]}\n')
            f.write('\n')


# Isikukirjete tekitamiseks artikli juurde
# import tools
# tools.massikanne()
def massikanne_from_dict(andmed):
    # Millised isikud lisada artiklile
    isik_str = andmed['isikud']
    # Millise artikliga siduda isik
    art_id = andmed['art']
    art = Artikkel.objects.get(id=art_id)
    print(art)
    # Millise pildiga siduda isik
    pilt_id = andmed['pil']
    pilt = Pilt.objects.get(id=pilt_id)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org_id = andmed['org']
    org = Organisatsioon.objects.get(id=org_id) # 33=tüt gümn, 85=poeg gymn, 2736=vene gymn, saksa eragymn
    print(org)
    # Milline viide lisada isikule
    viited_ids = [int(viite_id.strip()) for viite_id in andmed['vii'].split(',')]
    viited = Viide.objects.filter(id__in=viited_ids)
    print(viited)
    # Isiku kirjeldus
    isik_kirjeldus = andmed['kir']
    isikud = isik_str.split(',')
    for isik in isikud:
        # Loome uue isiku
        isik_nimi = isik.strip().split(' ')
        isik_eesnimi = ' '.join(isik_nimi[:-1]).strip()
        isik_perenimi = isik_nimi[-1].strip()
        if isik_eesnimi or isik_perenimi:
            print(isik_eesnimi, isik_perenimi)
            uus_isik = Isik(
                perenimi = isik_perenimi,
                eesnimi = isik_eesnimi,
                kirjeldus = isik_kirjeldus
            )
            uus_isik.save()
            print(uus_isik)
            # Lisame isikule seotud organisatsiooni
            uus_isik.organisatsioonid.add(org)
            # Lisame isikule seotud viite(d)
            for viide in viited:
                uus_isik.viited.add(viide)
            # Lisame isiku artiklile
            art.isikud.add(uus_isik)
            # Lisame isiku pildile
            pilt.isikud.add(uus_isik)


# Võtab andmed xml failist ja teeb isikute masskande ja sidumise artikli, organisatsiooni, pildi ja viitega
# xml faili struktuur, mis asub samas kataloogis, kus tools.py
# <data>
# <kanne>
# <kir></kir><isikud></isikud><pil></pil><org></org><vii></vii>
# </kanne>
# </data>
def massikanne_from_xml():
    f = '20200605_massikanne.xml'
    import xml.etree.ElementTree as ET
    tree = ET.parse(f)
    root = tree.getroot()
    # with open(f, 'r', encoding = 'UTF-8') as f:
    #     data_as_string = f.read()
    # root = ET.fromstring(data_as_string)
    for kanne in root:
        andmed = dict()
        for el in kanne:
            andmed[el.tag] = el.text.strip()
        massikanne_from_dict(andmed)


# Isikukirjete tekitamiseks artikli juurde
# import tools
# tools.massikanne_from_data()
def massikanne_from_data():
    # Millised isikud lisada artiklile
    isik_str = """
Irina Elias, Marie Kubjas, Senta Karlson, Aleftina Kaska, Amalie Hanson, Wera Tints, Selma Kongo, Linda Pärk, Miili Püwi, Salme Puustus
    """
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=1436)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=9268)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org = Organisatsioon.objects.get(id=2768) # 2777=ühisgümn, 2768=naiskutsekool, 2736=vene gymn, 2770=läti kesk, 2743=tööstuskool, 19=6.algkool
    print(org)
    # Milline viide lisada isikule
    viited_ids = [12938]
    viited = Viide.objects.filter(id__in=viited_ids)
    print(viited)
    # Isiku kirjeldus
    isik_kirjeldus = 'Valga naiskutsekooli õmblemise osakonna lõpetaja 1933'
    isikud = isik_str.split(',')
    for isik in isikud:
        # Loome uue isiku
        isik_nimi = isik.strip().split(' ')
        isik_eesnimi = ' '.join(isik_nimi[:-1]).strip()
        isik_perenimi = isik_nimi[-1].strip()
        if isik_eesnimi or isik_perenimi:
            print(isik_eesnimi, isik_perenimi)
            uus_isik = Isik(
                perenimi = isik_perenimi,
                eesnimi = isik_eesnimi,
                kirjeldus = isik_kirjeldus
            )
            uus_isik.save()
            print(uus_isik)
            # Lisame isikule seotud organisatsiooni
            uus_isik.organisatsioonid.add(org)
            # Lisame isikule seotud viite(d)
            for viide in viited:
                uus_isik.viited.add(viide)
            # Lisame isiku artiklile
            art.isikud.add(uus_isik)
            # Lisame isiku pildile
            pilt.isikud.add(uus_isik)

# Ühe sisuga artiklite lisamiseks
def lisa_artikkel_20200321():
    hist_years = [1384, 1385, 1387, 1391, 1393, 1396, 1398, 1410, 1412]
    body_text = 'Valgas toimus Liivimaa linnade päev'
    viide = Viide.objects.get(id=7841)
    for hist_year in hist_years:
        uus_art = Artikkel(
            hist_year = hist_year,
            body_text = body_text
        )
        uus_art.save()
        uus_art.viited.add(viide)
        print(uus_art.id, uus_art)

# Topeltviidete korrastus TODO:Teha siis, kui kroonikaraamat on läbi
def tvk():
    from django.db.models import Count
    # Kasutud viited
    tyhjad_viited = Viide.objects.\
        annotate(
        num_art=Count('artikkel__id'),
        num_isik=Count('isik__id'),
        num_org=Count('organisatsioon__id'),
        num_obj=Count('objekt__id'),
        num_pilt=Count('pilt__id')
        ).\
        filter(
        num_art=0,
        num_isik=0,
        num_org=0,
        num_obj=0,
        num_pilt=0
        )
    tyhjad_viited_ids = [viide.id for viide in tyhjad_viited]
    print(len(tyhjad_viited_ids))
    # Kroonikaraamatu viited
    allikas = Allikas.objects.get(id=1)
    # K6ik viited v2lja arvatud kroonikaraamatust
    viited = Viide.objects.exclude(allikas=allikas).exclude(id__in=tyhjad_viited_ids)
    topelt_viited = viited.\
        values('allikas__id', 'peatykk', 'hist_date', 'kohaviit').\
        annotate(viited_num=Count('kohaviit')).\
        filter(viited_num__gt=1).\
        order_by('allikas__id', 'hist_date')
    with open('topelt_viited.txt', 'w', encoding = 'UTF-8') as f:
        for topelt_viide in topelt_viited:
            hist_date = topelt_viide['hist_date']
            kohaviit = topelt_viide['kohaviit']
            # Topeltviidete id
            topelt_viide_ids = [el.id for el in viited.filter(hist_date=hist_date, kohaviit=kohaviit)]
            print(topelt_viide_ids)
            for id in topelt_viide_ids:
                f.write(f'V{id}:{Viide.objects.get(id=id)}\n')
            viide_esmane = Viide.objects.get(id=topelt_viide_ids[0])
            for topelt_viide_id in topelt_viide_ids:
                viide_duplikaat = Viide.objects.get(id=topelt_viide_id)
                # objectid, mis viitavad duplikaadile
                artiklid = viide_duplikaat.artikkel_set.all()
                isikud = viide_duplikaat.isik_set.all()
                organisatsioonid = viide_duplikaat.organisatsioon_set.all()
                objektid = viide_duplikaat.objekt_set.all()
                pildid = viide_duplikaat.pilt_set.all()
                baasid = {
                    'art': artiklid,
                    'isik': isikud,
                    'org': organisatsioonid,
                    'obj': objektid,
                    'pilt': pildid
                }
                for baas in baasid:
                    for obj in baasid[baas]:
                        print(topelt_viide_id, f'{baas}{obj.id}', obj)
                        f.write(f'V{topelt_viide_id}  {baas}{obj.id} {obj}\n')
                        if topelt_viide_id != viide_esmane.id:
                            viide_kustutada = Viide.objects.get(id=topelt_viide_id)
                            f.write(f'Lisame: V{viide_esmane.id}\n')
                            # obj.viited.add(viide_esmane)
                            f.write(f'Kustutame: V{viide_kustutada.id}\n')
                            # obj.viited.remove(viide_kustutada)
                f.write('-\n')
            f.write('- - -\n')


# Viidetele geni ja vikipeedia peatykinimed
def update_peatykk_from_url():
    # import requests
    from django.db.models import Q
    from urllib.request import Request, urlopen
    from bs4 import BeautifulSoup
    allikas = Allikas.objects.get(id=17) # geni
    # div_id = ''
    peatykita_viited = Viide.objects.filter(allikas=allikas, url__isnull=False).filter(Q(peatykk__isnull=True) | Q(peatykk__exact=''))
    print(len(peatykita_viited))
    for viide in peatykita_viited:
        href = viide.url
        # r = requests.get(href)
        # print(href)
        req = Request(href, headers={'User-Agent': 'Mozilla/5.0'})
        webpage = urlopen(req).read()
        # Struktueerime
        soup = BeautifulSoup(webpage, 'html.parser')
        # div = soup.find(id=div_id)
        div = soup.find('h1')
        print(href, end=' ')
        if div:
            text = div.text.replace('*', '')
            print(text)
            if text:
                viide.peatykk = text
                # viide.save()
                pass
        else:
            print('-')

# Lisab artiklile lisatud pildile isikud ja objektid
def task_art9754():
    art = Artikkel.objects.get(id=9754)
    print(art)
    pil = Pilt.objects.get(id=6431)
    for isik in art.isikud.all():
        print(isik)
        pil.isikud.add(isik)
    # for obj in art.objektid.all():
        # print(obj)
        # pil.objektid.add(obj)

# Kannab object andmed obj -> org
# tools.obj2org(obj=xxx,[org=yyy])
def obj2org(**kwargs):
    src_obj = kwargs.get('obj', None)
    if src_obj:
        obj = Objekt.objects.get(id=src_obj)
        dst_org = kwargs.get('org', None)
        if dst_org:
            org = Organisatsioon.objects.get(id=dst_org)
        else:
            org = Organisatsioon.objects.create(
                nimi=obj.nimi,
                hist_date=obj.hist_date,
                hist_year=obj.hist_year,
                hist_month=obj.hist_month,
                hist_enddate=obj.hist_enddate,
                hist_endyear=obj.hist_endyear,
                gone=obj.gone,
                kirjeldus=obj.kirjeldus
            )
            org.save()
        print(f'{obj.id}:{obj}->{org.id}:{org}')
        # Objektid
        for objekt in obj.objektid.all():
            print(f'obj{objekt.id}:{objekt}')
            org.objektid.add(objekt)
        # Viited
        for viide in obj.viited.all():
            print(f'vii{viide.id}:{viide}')
            org.viited.add(viide)
        # Artiklid
        artiklid = Artikkel.objects.filter(objektid=obj)
        for artikkel in artiklid:
            print(f'art{artikkel.id}:{artikkel}')
            artikkel.organisatsioonid.add(org)
        # Pildid
        pildid = Pilt.objects.filter(objektid=obj)
        for pilt in pildid:
            print(f'pilt{pilt.id}:{pilt}')
            pilt.organisatsioonid.add(org)
        # Profiilipildid
        pildid = Pilt.objects.filter(profiilipilt_objektid=obj)
        for pilt in pildid:
            print(f'pilt{pilt.id}:{pilt}')
            pilt.profiilipilt_organisatsioonid.add(org)
        # Isikud
        isikud = Isik.objects.filter(objektid=obj)
        for isik in isikud:
            print(f'isik{isik.id}:{isik}')
            isik.organisatsioonid.add(org)

def db_test():
    for model in (Isik, Organisatsioon, Objekt):
        print(model.__name__)
        for i in range(1, 13):
            time = datetime.now()
            artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
            filtered_queryset = model.objects.filter(hist_date__month=i).filter(
                Q(viited__isnull=False) |
                Q(viited__isnull=True, artikkel__isnull=True) |
                Q(artikkel__in=artikkel_qs)
            ).distinct()
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
            ).count()
            print(
                i,
                filtered_queryset,
                f'{(datetime.now() - time).seconds}.{(datetime.now() - time).microseconds}'
            )

def fix(id):
    art_500 = Artikkel.objects.get(id=id)
    fixed = False
    print(art_500.inp_date, art_500.mod_date)

    if art_500.inp_date.hour == 3 and art_500.inp_date.weekday() == 6 and art_500.inp_date.month in [3,10]:
        fix_date = datetime(art_500.inp_date.year, art_500.inp_date.month, art_500.inp_date.day)
        print('Fix:', fix_date)
        art_500.inp_date = fix_date
        fixed = True

    if art_500.mod_date.hour == 3 and art_500.mod_date.weekday() == 6 and art_500.mod_date.month in [3,10]:
        fix_date = datetime(art_500.mod_date.year, art_500.mod_date.month, art_500.mod_date.day)
        print('Fix:', fix_date)
        art_500.mod_date = fix_date
        fixed = True

    if fixed:
        art_500.save()

def objekt_to_csv():
    objs = Objekt.objects.all()
    with open('objekt.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        for obj in objs:
            writer.writerow(
                [
                    obj.id,
                    obj.tyyp,
                    obj.nimi,
                    obj.asukoht,
                    str(len(obj.kirjeldus)),
                    str(len(obj.objektid.all()))
                ]
            )

def update_objekt_from_csv():
    with open('objekt.csv', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile, fieldnames=['id', 'tyyp', 'nimi', 'asukoht', 'kir', 'objs', 'muuta'], delimiter=';')
        for row in reader:
            if row['muuta'] == 'X':
                obj = Objekt.objects.filter(id=row['id']).first()
                if obj:
                    print(row['asukoht'], '->', obj.asukoht)

def task_20211121():
    art =  Artikkel.objects.get(id=9738)
    isikud = art.isikud.all()
    org = Organisatsioon.objects.get(id=2782)
    pilt = Pilt.objects.get(id=6561)
    viide = Viide.objects.get(id=10917)

    print(art, pilt, org, viide, isikud.count())

    for isik in isikud:
        print(f'isik{isik.id}:{isik}')
        isik.organisatsioonid.add(org)
        isik.viited.add(viide)
        pilt.isikud.add(isik)

def export_ilm_data():
    from ilm.models import Ilm
    from django.db.models import Sum, Count, Avg, Min, Max
    qs_kuud = Ilm.objects \
        .values('timestamp__year', 'timestamp__month') \
        .annotate(Sum('precipitations'), Avg('airtemperature')) \
        .order_by('timestamp__year', 'timestamp__month')
    import csv

    with open('ilm.csv', 'w', newline='') as csvfile:
        fieldnames = ['month', 'avgtemp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for kuu in qs_kuud:
            writer.writerow(
                {
                    'month': f'{kuu["timestamp__year"]}-{kuu["timestamp__month"]}-01',
                    'avgtemp': float(kuu["airtemperature__avg"])
                }
            )

def import_ilm_maxmin_airtemperature():
    from ilm.models import Ilm
    from datetime import datetime
    # fn_import = 'ilm_maxmin.txt'
    fn_import = 'ilm_maxmin_upd_2021_07_09_08.txt'
    format = '%Y-%m-%d %H:%M:%S%z'
    with open(fn_import) as f:
        ok = 0
        nok = 0
        y = 0
        with open('nok.txt', 'w') as viga:
            for line in f:
                data = line.split(';')
                dt_loc_str = data[0].strip()

                dt_loc = datetime.strptime(dt_loc_str, format)
                if y != dt_loc.year:
                    y = dt_loc.year
                    print(y) # edenemise näitamiseks
                obs = Ilm.objects.filter(timestamp=dt_loc).first()

                if len(data)>2 and obs and (float_or_none(data[2]) != None or float_or_none(data[3]) != None):
                    obs.airtemperature_max = float_or_none(data[2])
                    obs.airtemperature_min = float_or_none(data[3])
                    # print(dt_loc, airtemperature_max, airtemperature_min)
                    obs.save(update_fields=['airtemperature_max', 'airtemperature_min'])
                    ok += 1
                else:
                    print('Viga: ', line, end='')
                    viga.write(line)
                    nok += 1
    print(ok, nok)

def ilm_maxmin():
    from ilm.models import Ilm
    from django.db.models import Sum, Count, Avg, Min, Max
    years_top = dict()
    years_maxmin_qs = Ilm.objects\
        .values('timestamp__year')\
        .annotate(Max('airtemperature_max'), Min('airtemperature_min'), Sum('precipitations'))\
        .order_by('timestamp__year')
    days_maxmin_qs = Ilm.objects\
        .values('timestamp__year', 'timestamp__month', 'timestamp__day')\
        .annotate(Max('airtemperature_max'), Min('airtemperature_min'), Avg('airtemperature'), Sum('precipitations'))\
        .order_by('timestamp__year', 'timestamp__month', 'timestamp__day')
    for year in years_maxmin_qs:
        y = year['timestamp__year']
        # Maksimum-miinimum
        year_min = year['airtemperature_min__min']
        obs_min = Ilm.objects.filter(airtemperature_min=year_min, timestamp__year=y)
        year_max = year['airtemperature_max__max']
        obs_max = Ilm.objects.filter(airtemperature_max=year_max, timestamp__year=y)
        # Põevi Min(d)>+30 ja Max(d)<-30
        days_below30 = days_maxmin_qs.filter(timestamp__year=y, airtemperature_max__max__gte=30).count()
        days_above30 = days_maxmin_qs.filter(timestamp__year=y, airtemperature_min__min__lte=-30).count()
        # Põevi Avg(d)>+20 ja Avg(d)<-20
        days_below20 = days_maxmin_qs.filter(timestamp__year=y, airtemperature_min__min__gte=20).count()
        days_above20 = days_maxmin_qs.filter(timestamp__year=y, airtemperature_max__max__lte=-20).count()

        print(
            y,
            year_min,
            [obs.timestamp for obs in obs_min],
            year_max,
            [obs.timestamp for obs in obs_max],
            days_below20,
            days_above20,
            days_below30,
            days_above30,
        )
        years_top[y] = {
            'year_min': year_min,
            'obs_min': obs_min,
            'year_max': year_max,
            'obs_max': obs_max,
            'days_below20': days_below20,
            'days_above20': days_above20
        }

def clean_ophan_images():
    # remove ophan pictures

    # Returns a list of names in list files.
    print("Pildid:")
    files = glob.glob(str(MEDIA_DIR / 'pildid/**/*.*'), recursive=True)
    print(type(files[0]))

    print('Kokku:', len(files))
    c = Counter(
        [file.split('.')[-1] for file in files]
    )
    print(c)

    def img_type(filename):
        if 'icon' in filename:
            return 'icon'
        elif 'thumb' in filename:
            return 'thumb'
        else:
            return 'other'

    c = Counter(
        [
            img_type(file)
            for file
            in files]
    )
    print(c)

    files_ok = []
    pildid = Pilt.objects.all()
    for pilt in pildid:
        # pilt
        pildifail = str(MEDIA_DIR / pilt.pilt.name)
        try:
            found = files.index(pildifail)
        except:
            found = -1
            print(pildifail in files_ok, pildifail)
        if found > -1:
            files_ok.append(files.pop(found))
        # thumb
        pildifail = str(MEDIA_DIR / pilt.pilt_thumbnail.name)
        if len(pilt.pilt_thumbnail.name) == 0:
            print('null thumb', pilt.pilt.name)
        if pildifail.find('thumb') < 0:
            print('thumb', pildifail)
        try:
            found = files.index(pildifail)
        except:
            found = -1
            print(pildifail in files_ok, pildifail)
        if found > -1:
            files_ok.append(files.pop(found))
        # icon
        pildifail = str(MEDIA_DIR / pilt.pilt_icon.name)
        if len(pilt.pilt_icon.name) == 0:
            print('null icon', pilt.pilt.name)
        if pildifail.find('icon') < 0:
            print('icon', pildifail)
        try:
            found = files.index(pildifail)
        except:
            found = -1
            print(pildifail in files_ok, pildifail)
        if found > -1:
            files_ok.append(files.pop(found))

    print(len(files_ok), len(files))
    c = Counter(
        [
            img_type(file)
            for file
            in files_ok]
    )
    print(c)

    Path(MEDIA_DIR / 'orphans').mkdir(parents=True, exist_ok=True)
    print(MEDIA_DIR)
    for fail in files:
        src = Path(fail)
        dst = PurePath(MEDIA_DIR, 'orphans', *src.parent.parts[-3:], src.name)
        # print(dst)
        dst_dir = dst.parent
        Path(dst_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
        os.remove(src)

def get_vg_vilistlased():
    # base_url = 'https://www.valgagym.ee/vilistlased/lopetanud/list/loetelu/'
    base_url = 'https://www.valgagym.ee/kool/vilistlased/lopetanud/list/loetelu/'
    data = {}
    for aasta in range(1933, 2022):
        if aasta in [1939]:
            continue # selle aasta andmed puuduvad
        suffix = ''
        if aasta in [2004]:
            suffix = '-'
        if aasta in [1997, 2007, 2008]:
            suffix = '-2'
        url = f'{base_url}{aasta}-a{suffix}/'
        r = requests.get(url)
        html_doc = r.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        cols = soup.find_all("div", class_="grid-cols-2")
        klassid = soup.find_all("div", class_="class-row")
        if aasta in [1940, 1945]:
            klassid = [cols[0]]
        if aasta in [1966]:
            varu = klassid
            klassid = [cols[0]]
            klassid.extend(varu)
        print(aasta, len(cols), len(klassid))
        data[aasta] = {
            'url': url,
            'harud': {}
        }
        for klass in klassid:
            haru = klass.h3
            try:
                haru = haru.text.strip()
            except:
                if aasta == 1966:
                    haru = 'A'
                else:
                    haru = '-'
            nimekiri = klass.find_all("p")
            print(haru, nimekiri[0].text.split('\n')[:3])
            data[aasta]['harud'][haru] = nimekiri[0].text.split('\n')
        print()

    import json
    with open('vilistlased1933-2021.json', mode='w', encoding='utf8') as f:
        json.dump(data, f)

import time
import xml.etree.ElementTree as ET

import pandas as pd

def get_muis_vamf():
    with open('resource.rdf', 'r') as resource:
        content = resource.read()
        root = ET.fromstring(content)

    muis_viited = muis_viited_inuse()
    muis_vamf = []

    for child in root:
        # print(child.tag)
        if 'E78' in child.tag:
            n = 1
            total = len(child)
            for crm in child:
                url = crm.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']
                print(n, url)
                r = requests.get(url)
                html_doc = r.text
                soup = BeautifulSoup(html_doc, 'html.parser')
                table = soup.find_all("div", id="general_museaal")[0]
                trs = table.find_all("tr")
                number, nimetus, dateering, inuse = '', '', '', ''

                for tr in trs:
                    if tr.text.find('Number') == 0:
                        number = tr.find_all('td')[0].text
                        if number in muis_viited:
                            inuse = 'OK'
                    if tr.text.find('Nimetus') == 0:
                        nimetus = tr.find_all('td')[0].text
                    if tr.text.find('Dateering') == 0:
                        dateering = tr.find_all('td')[0].text

                pildiplokid = soup.find_all('table', class_='grp_block_table')
                pilte = len(pildiplokid)

                for pildiplokk in pildiplokid:
                    trs = pildiplokk.find_all('tr')
                    pisipilt_failinimi = trs[0].find_all('td')[0].text
                    pisipilt_url = trs[0].find_all('td')[0].a.get('href')
                    pisipilt_suurus = trs[1].find_all('td')[0].text
                    if len(trs) > 3:
                        suurpilt_failinimi = trs[3].find_all('td')[0].text
                        suurpilt_url = trs[3].find_all('td')[0].a.get('href')
                        suurpilt_suurus = trs[4].find_all('td')[0].text
                    else:
                        suurpilt_failinimi = ''
                        suurpilt_url = ''
                        suurpilt_suurus = ''
                    # print(
                    #     number,
                    #     nimetus,
                    #     inuse,
                    #     pisipilt_failinimi,
                    #     pisipilt_suurus,
                    #     suurpilt_failinimi,
                    #     suurpilt_suurus
                    # )

                    muis_vamf.append(
                        [
                            number,
                            nimetus,
                            dateering,
                            inuse,
                            pilte,
                            url,
                            pisipilt_failinimi,
                            pisipilt_suurus,
                            pisipilt_url,
                            suurpilt_failinimi,
                            suurpilt_suurus,
                            suurpilt_url
                        ]
                    )
                n += 1
                time.sleep(1)
    columns = [
        'number',
        'nimetus',
        'dateering',
        'inuse',
        'pilte',
        'url',
        'pisipilt_failinimi',
        'pisipilt_suurus',
        'pisipilt_url',
        'suurpilt_failinimi',
        'suurpilt_suurus',
        'suurpilt_url'
    ]
    df = pd.DataFrame(
        muis_vamf,
        columns=columns
    )
    print(df.shape)
    df.to_excel(
        "muis_vamf.xlsx",
        sheet_name='muis_vamf'
    )

def muis_viited_inuse():
    muis_viited = {}
    from wiki.models import Pilt, Viide, Allikas
    allikad = Allikas.objects.filter(id__in=[43, 33])
    viited = Viide.objects.filter(allikas__in=allikad)
    for viide in viited:
        muis_viited[viide.kohaviit] = {
            'art': [artikkel.id for artikkel in viide.artikkel_set.all() if viide.artikkel_set.all()],
            'isik': [isik.id for isik in viide.isik_set.all() if viide.isik_set.all()],
            'org': [organisatsioon.id for organisatsioon in viide.organisatsioon_set.all() if viide.organisatsioon_set.all()],
            'obj': [objekt.id for objekt in viide.objekt_set.all() if viide.objekt_set.all()],
            'pilt': [pilt.id for pilt in viide.pilt_set.all() if viide.pilt_set.all()],
        }
    return muis_viited

import re
def init_pilt_tyyp():
    otsistringid = [f'_{otsistring}_' for otsistring in ['art', 'isik', 'org', 'obj']]
    pattern = re.compile("|".join(re.escape(x) for x in otsistringid))
    pildid = Pilt.objects.all()
    for pilt in pildid:
        if not pattern.findall(pilt.nimi, re.IGNORECASE):
            pilt.tyyp = 'P'
            pilt.save(update_fields=['tyyp'])

def init_pilt_profiilipildid():
    pildid = Pilt.objects.all()
    for pilt in pildid:
        if pilt.profiilipilt_allikas and pilt.allikad.all():
            for obj in pilt.allikad.all():
                pilt.profiilipilt_allikad.add(obj)
        if pilt.profiilipilt_artikkel and pilt.artiklid.all():
            for obj in pilt.artiklid.all():
                pilt.profiilipilt_artiklid.add(obj)
        if pilt.profiilipilt_isik and pilt.isikud.all():
            for obj in pilt.isikud.all():
                pilt.profiilipilt_isikud.add(obj)
        if pilt.profiilipilt_organisatsioon and pilt.organisatsioonid.all():
            for obj in pilt.organisatsioonid.all():
                pilt.profiilipilt_organisatsioonid.add(obj)
        if pilt.profiilipilt_objekt and pilt.objektid.all():
            for obj in pilt.objektid.all():
                pilt.profiilipilt_objektid.add(obj)

def ilmajama():
    print('Nullist:')
    print('datetime naive [datetime.now()]:', datetime.now())
    dt_naive = datetime.now()
    print('datetime UTC   [datetime.now(timezone.utc)]:', datetime.now(timezone.utc))
    dt_utc = datetime.now(timezone.utc)
    print('datetime Eesti [datetime.now(tz=ZoneInfo("Europe/Tallintoolsn")]:', datetime.now(tz=ZoneInfo('Europe/Tallinn')))
    dt_eesti = datetime.now(tz=ZoneInfo('Europe/Tallinn'))
    print('Teisendused:')
    dt_utc_uus = dt_naive.astimezone(timezone.utc)
    print(f'naive -> utc   [dt_naive.astimezone(timezone.utc)]: {dt_naive} -> {dt_utc_uus}')
    dt_eesti_uus = dt_naive.astimezone(ZoneInfo("Europe/Tallinn"))
    print(f'naive -> Eesti [dt_naive.astimezone(ZoneInfo("Europe/Tallinn"))]: {dt_naive} -> {dt_eesti_uus}')
    dt_utc2eesti_uus = dt_utc.astimezone(ZoneInfo("Europe/Tallinn"))
    print(f'UTC   -> Eesti [dt_utc.astimezone(ZoneInfo("Europe/Tallinn"))]: {dt_utc} -> {dt_utc2eesti_uus}')
    print(f'{dt_eesti_uus} == {dt_utc_uus} -> {dt_eesti_uus == dt_utc_uus}')

def check_profiilipildid_notin_pildid():
    for model in [Artikkel, Isik, Organisatsioon, Objekt]:
        objs = model.objects.all()
        for obj in objs:
            profiilipildid = obj.profiilipildid.all()
            if profiilipildid.count() > 0:
                for pilt in profiilipildid:
                    if pilt not in obj.pildid.all():
                        print(model, 'obj:', obj.id, 'pilt:', pilt.id)


if __name__ == "__main__":
    # get_vg_vilistlased()
    # get_muis_vamf()
    # muis_viited_inuse()
    ilmajama()
    pass