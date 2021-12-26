import csv
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

if __name__ == "__main__":
    import os
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()

from django.core import serializers

from django.db.models import (
    Case, F, Q, Value, When,
    BooleanField, DateField, DateTimeField, DecimalField, IntegerField,
    ExpressionWrapper
)

from django.db.models.functions import Extract, Trunc, ExtractDay

from ipwhois import IPWhois

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt, Pilt, Viide, Allikas

# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value.strip().replace(',', '.'))
    except:
        return None

#
# Funktsioon duplikaatkirjete koondamiseks
# Kasutamine:
# python manage.py shell
# import tools
# tools.join('andmebaas', kirje_id_kust_kopeerida, kirje_id_kuhu_kopeerida)
#
def join(model_name, source_id, dest_id):
    if model_name == 'isik':
        model = Isik
    elif model_name == 'organisatsioon':
        model = Organisatsioon
    elif model_name == 'objekt':
        model = Objekt
    else:
        return None

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
                new.synd_koht = old.synd_koht
        if old.surm_koht:
            if new.surm_koht == None:
                new.surm_koht = old.surm_koht
        if old.maetud:
            if new.maetud == None:
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
                    new.month = old.month
        if old.asukoht:
            if new.asukoht == None:
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
    # Salvestame muudatused
    new.save()

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
Hans Järv,
Artur-Helmut Kaigas,
Verner-Herman Kulbok,
Elmar Kull,
Alfred-Artur Käärmann,
Eduard Laas,
Heinrich-Oskar Mehist(Mehilane),
Voldemar Mürk,
Jaan-Rudolf Orav,
Endrik Piho,
Karl-Edgar Rebase,
Peeter Saar,
Theodor-Rudolf Siim,
Jaan Sulsenberg,
August Taal,
Aleksander Timpmann,
Arnold Viiding,
    """
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=9970)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=6834)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org = Organisatsioon.objects.get(id=85) # 33=tüt gümn, 85=poeg gymn, 2736=vene gymn, 2770=läti kesk, saksa eragymn, 19=6.algkool
    print(org)
    # Milline viide lisada isikule
    viited_ids = [11091, 11093]
    viited = Viide.objects.filter(id__in=viited_ids)
    print(viited)
    # Isiku kirjeldus
    isik_kirjeldus = 'Valga poeglaste gümnaasiumi reaalharu lõpetaja 1930'
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
            if pilt.profiilipilt_objekt==True:
                pilt.profiilipilt_organisatsioon=True
                pilt.save()
            pilt.organisatsioonid.add(org)
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


# Andmete varundamiseks offline kasutuseks
# Loob valgalinn.ee ajalookroonika koopia json ja xml formaatides

# Salvestame ainult kasutatud allikad
def serverless_save_allikad(path, method, allikas):
    SAVE_PATH = path / method / 'allikad'
    FILE_NAME = SAVE_PATH / f'allikas_{allikas.id}.{method}'
    Serializer = serializers.get_serializer(method)
    serializer = Serializer()
    if not Path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as out:
            serializer.serialize([allikas], stream=out)

# Salvestame ainult kasutatud viited
def serverless_save_viited(path, method, obj):
    viited = obj.viited.all()
    if viited:
        SAVE_PATH = path / method / 'viited'
        for viide in viited:
            # print(viide.id)
            FILE_NAME = SAVE_PATH / f'viide_{viide.id}.{method}'
            Serializer = serializers.get_serializer(method)
            serializer = Serializer()
            if not Path.exists(FILE_NAME):
                with open(FILE_NAME, "w", encoding="utf-8") as out:
                    serializer.serialize([viide], stream=out)
                if viide.allikas:
                    serverless_save_allikad(path, method, viide.allikas)

# Salvestame ainult kasutatud pildid
def serverless_save_pildid(path, method, obj, verbose_name_plural, base_dir, pildifailid):
    filterset = {f'{verbose_name_plural}__in': [obj]}
    pildid = Pilt.objects.filter(**filterset)
    if pildid:
        SAVE_PATH = path / method / 'pildid'
        for pilt in pildid:
            FILE_NAME = SAVE_PATH / f'pilt_{pilt.id}.{method}'
            Serializer = serializers.get_serializer(method)
            serializer = Serializer()
            if not Path.exists(FILE_NAME):
                with open(FILE_NAME, "w", encoding="utf-8") as out:
                    serializer.serialize([pilt], stream=out)
                serverless_save_viited(path, method, pilt)
            pildifail = str(pilt.pilt)
            if Path.exists(base_dir / 'media' / pildifail) and (pildifail not in pildifailid):
                pildifailid.append(pildifail)
    return pildifailid

# Kopeerime pildid BACKUP_DIRi
def serverless_copy_pildid(pildifailid, BACKUP_DIR, BASE_DIR):
    Path(BACKUP_DIR / 'media').mkdir(parents=True, exist_ok=True)
    for fail in pildifailid:
        src = Path(BASE_DIR / 'media' / fail)
        dst = Path(BACKUP_DIR / 'media' / fail)
        dst_dir = dst.parent
        Path(dst_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    print('Kopeeriti', len(pildifailid), 'pilti')

def serverless_make_index(objs, andmebaas, BACKUP_DIR):
    for method in ['xml', 'json']:
        Serializer = serializers.get_serializer(method)
        serializer = Serializer()
        file_name = BACKUP_DIR / method / f'{andmebaas["verbose_name_plural"]}.{method}'
        # with open(file_name, "w", encoding="utf-8") as out:
        #     serializer.serialize(objs, fields=('hist_year', 'hist_date', 'slug'), stream=out)

    # millisest andmebaasi tabelist andmed
    db_table = objs.model._meta.db_table

    # init xml-data
    xml_content = ET.Element('root', attrib={'lang': 'et', 'origin': 'https://valgalinn.ee', 'db_table': db_table})

    # init json-data
    json_content = {
        'origin': 'https://valgalinn.ee',
        'db_table': db_table,
        'data': []
    }

    # init html-data
    html_content = ET.Element('html', attrib={'lang': 'et'})
    html_content_h1 = ET.SubElement(html_content, 'h1')
    html_content_table = ET.SubElement(html_content, 'table')
    html_content_table_thead = ET.SubElement(html_content_table, 'thead')
    html_content_table_tbody = ET.SubElement(html_content_table, 'tbody')

    for obj in objs:
        object = {
            'pk': str(obj.pk),
            'hist_year': str(obj.hist_year),
            'hist_date': obj.hist_date.strftime('%Y-%m-%d') if obj.hist_date else str(obj.hist_date),
            'hist_enddate': obj.hist_enddate.strftime('%Y-%m-%d') if obj.hist_enddate else str(obj.hist_enddate),
            'obj': str(obj),
            'JSON': f'json/{andmebaas["verbose_name_plural"]}/{andmebaas["acronym"]}_{obj.id}.json',
            'XML':  f'xml/{andmebaas["verbose_name_plural"]}/{andmebaas["acronym"]}_{obj.id}.xml'
        }

        # Lisame xml elemendi
        xml_content_object = ET.SubElement(xml_content, 'object')
        for field in object.keys():
            xml_content_field = ET.SubElement(xml_content_object, 'field', attrib={'name': field})
            xml_content_field.text = object[field]

        # Lisame json elemendi
        json_content['data'].append(object)

        # Lisame html elemendi
        if not html_content_table_thead.findall("./tr"): # kui tabeli päist ei ole
            # link = '<a href="https://valgalinn.ee" target="_blank">valgalinn.ee</a>'
            link = 'https://valgalinn.ee'
            html_content_h1.text = f'Väljavõte {link} veebilehe andmetabelist {db_table}'
            html_content_table_thead_tr = ET.SubElement(html_content_table_thead, 'tr')
            for field in object.keys():
                html_content_table_thead_tr_th = ET.SubElement(html_content_table_thead_tr, 'th')
                html_content_table_thead_tr_th.text = field

        html_content_table_tbody_tr = ET.SubElement(html_content_table_tbody, 'tr')
        for field in object.keys():
            html_content_table_tbody_tr_td = ET.SubElement(html_content_table_tbody_tr, 'td')
            if field in ['JSON', 'XML']:
                html_content_table_tbody_tr_td_a = ET.SubElement(
                    html_content_table_tbody_tr_td,
                    'a',
                    attrib={'href': object[field]}
                )
                html_content_table_tbody_tr_td_a.text = field
            else:
                html_content_table_tbody_tr_td.text = object[field]

    xml_content_file_name = BACKUP_DIR / 'xml' / f'{andmebaas["verbose_name_plural"]}.xml'
    tree = ET.ElementTree(xml_content)
    tree.write(xml_content_file_name, encoding = "UTF-8", xml_declaration = True)

    json_content_file_name = BACKUP_DIR / 'json' / f'{andmebaas["verbose_name_plural"]}.json'
    with open(json_content_file_name, "w", encoding = "UTF-8") as write_file:
        json.dump(json_content, write_file)

    html_content_file_name = BACKUP_DIR / f'{andmebaas["verbose_name_plural"]}.html'
    # write_file.write(ET.dump(html_content))
    tree = ET.ElementTree(html_content)
    tree.write(html_content_file_name, encoding = "UTF-8")

def serverless(objects=10):
    BASE_DIR = Path(__file__).resolve().parent
    print('Alustasime:', datetime.now())

    # Loome backup kataloogistruktuuri
    now = datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M')
    BACKUP_DIR = BASE_DIR / now_string
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    for method in ['xml', 'json']:
        Path(BACKUP_DIR / method / 'artiklid').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'isikud').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'organisatsioonid').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'objektid').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'viited').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'allikad').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'pildid').mkdir(parents=True, exist_ok=True)

    pildifailid = []

    andmebaasid = [
        {'model': Artikkel, 'verbose_name_plural': 'artiklid', 'acronym': 'art'}, # Lood
        {'model': Isik, 'verbose_name_plural': 'isikud', 'acronym': 'isik'}, # Isikud
        {'model': Organisatsioon, 'verbose_name_plural': 'organisatsioonid', 'acronym': 'org'},  # Asutised
        {'model': Objekt, 'verbose_name_plural': 'objektid', 'acronym': 'obj'},  # Kohad
    ]

    from django.forms.models import model_to_dict
    for andmebaas in andmebaasid:
        objs = andmebaas['model'].objects.all()
        if objects > 0:
            objs = objs[:objects]
        print(f'Kopeerime {andmebaas["verbose_name_plural"]}:', len(objs), 'objekti...', end=' ')

        for method in ['xml', 'json']:
            print(method, end=' ')
            Serializer = serializers.get_serializer(method)
            serializer = Serializer()
            for obj in objs:
                # obj_dict = model_to_dict(obj)
                # filterset = {f"{andmebaas['verbose_name_plural']}__in": [obj]}
                # pildid = Pilt.objects.filter(**filterset).values('id', 'pilt')
                # obj_dict['pildid'] = pildid
                serverless_save_viited(
                    BACKUP_DIR,
                    method,
                    obj
                )
                pildifailid = serverless_save_pildid(
                    BACKUP_DIR,
                    method,
                    obj,
                    andmebaas['verbose_name_plural'],
                    BASE_DIR,
                    pildifailid
                )
                file_name = BACKUP_DIR / method / andmebaas['verbose_name_plural'] / f'{andmebaas["acronym"]}_{obj.id}.{method}'

                serializer.serialize([obj])
                data = serializer.getvalue()

                # Lisame pildiviited
                filterset = {f"{andmebaas['verbose_name_plural']}__in": [obj]}
                pildid = [pilt.id for pilt in Pilt.objects.filter(**filterset)]

                if method == 'json':
                    json_src = json.loads(data)[0]
                    json_src['fields']['pildid'] = pildid
                    dst = json.dumps(json_src)
                    with open(file_name, "w", encoding="utf-8") as out:
                        out.write(dst)
                elif method == 'xml':
                    xml_src = ET.fromstring(data)
                    # <field name="viited" rel="ManyToManyRel" to="wiki.viide"><object pk="2459"></object>
                    fields = xml_src.find('object')
                    field_pildid = ET.SubElement(fields, "field", {"name": "pildid", "rel": "ManyToManyRel", "to": "wiki.pilt"})
                    for pilt in pildid:
                        object_pilt = ET.SubElement(field_pildid, 'object', attrib={'pk': str(pilt)})
                    dst = ET.ElementTree(xml_src)
                    # tree = ET.ElementTree(html_content)
                    dst.write(file_name, encoding="UTF-8", xml_declaration=True)
                else:
                    continue

        print('loome indeksi', end=' ')
        serverless_make_index(objs, andmebaas, BACKUP_DIR)

        print('OK')

    # kopeerime asjakohased pildid BACKUP_DIRi
    serverless_copy_pildid(pildifailid, BACKUP_DIR, BASE_DIR)

    print('Lõpetasime:', datetime.now())

if __name__ == "__main__":
    serverless(objects=3) # objects=0 = täiskoopia