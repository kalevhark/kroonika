from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
import glob
import json
import logging
import os
from pathlib import Path, PurePath
import shutil
from zoneinfo import ZoneInfo

import psycopg2
import requests
from bs4 import BeautifulSoup

if __name__ == "__main__":
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename='tools_worker.log', 
        level=logging.INFO,
        format="%(asctime)s;%(levelname)s;%(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger.info('Started')

from django.conf import settings

from django.db.models import (
    Case, F, Q, Value, When,
    BooleanField, DateField, DateTimeField, DecimalField, IntegerField,
    ExpressionWrapper
)
from django.db.models.functions import Extract, Trunc, ExtractDay

from ilm.utils import utils
from wiki.models import (
    Aadress, Artikkel, Isik, Organisatsioon, Objekt, Pilt,
    Kaart, Kaardiobjekt,
    Viide, Allikas
)

MEDIA_DIR = settings.MEDIA_ROOT

# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value.strip().replace(',', '.'))
    except:
        return None


def massikanne_from_data():
    """
    Isikukirjete tekitamiseks artikli juurde
    > import tools
    > tools.massikanne_from_data()
    """
    # Millised isikud lisada artiklile
    isik_str = """
Olga Aas, Natalie Ammas, Leida Anderson, Hermine Hermann, Asne Kaplan, Villemine Korp, Linda Martinson, Marie Mõtsküla, Helene Sprenk, Salme Tamm, Jenny Teitelbaum, Eugenie Vaardt, Julie Vaher, Laine Vähi, Linda Ilves, Linda Kiima, Loreida Lääts, Erna Lepik, Aino Luik, Valve Niglas, Emmi Pettai, Rute Raska, Adele Tamm, Õie Salundi, Aita Värk, Leida Visnapuu, Aide Kivi, Klaudia Lainovool, Armanda Saretok, Loreida Johanson, Magda Lepik, Liine Till
    """
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=13989)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=14899)
    print(pilt)
    # Milline organisatsioon lisada isikule
    # 2777=ühisgümn, 2768=naiskutsekool, 2736=vene gymn, 2770=läti kesk, 
    # 2743=tööstuskool, 19=6.algkool, 2802=reaalkool(1937), 2801=progümnaasium(1937)
    # 3274=kaubanduskool(1937)
    org = Organisatsioon.objects.get(id=2768) 
    print(org)
    # Milline viide lisada isikule
    viited_ids = [16387]
    viited = Viide.objects.filter(id__in=viited_ids)
    viitestring = ' '.join([f'[viide_{viite_id}]' for viite_id in viited_ids])
    print(viited, viitestring)
    # Isiku kirjeldus
    isik_kirjeldus = f'Valga naiskutsekooli lõpetaja 1938 {viitestring}'
    isikud = isik_str.split(',')
    for isik in isikud:
        # Loome uue isiku
        isik_nimi = isik.strip().split(' ')
        isik_eesnimi = ' '.join(isik_nimi[:-1]).strip()
        isik_perenimi = isik_nimi[-1].strip()
        if isik_eesnimi or isik_perenimi:
            # print(isik_eesnimi, isik_perenimi)
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
                # pass
            # Lisame isiku artiklile
            art.isikud.add(uus_isik)
            # Lisame isiku pildile
            pilt.isikud.add(uus_isik)

# Isikukirjete tekitamiseks artikli juurde
# import tools
# tools.massikanne_from_json()
def massikanne_from_json():
    # Millise aasta lend
    aasta = '1938'
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=1869)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=14896)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org = Organisatsioon.objects.get(
        id=2777)  # 2777=ühisgümn, 2768=naiskutsekool, 2736=vene gymn, 2770=läti kesk, 2743=tööstuskool, 19=6.algkool
    print(org)
    # Milline viide lisada isikule
    viited_ids = [16387, 16388]
    viited = Viide.objects.filter(id__in=viited_ids)
    print(viited)
    viitestring = ' '.join([f'[viide_{viite_id}]' for viite_id in viited_ids])
    # Loeme lendude andmed
    with open('vilistlased1933-2021.json', mode='r', encoding='utf8') as f:
        data = json.load(f)

    harud = data[aasta]['harud']
    for haru in harud:
        print(f'**{haru}**')
        # Isiku kirjeldus
        isik_kirjeldus = f'Valga ühisgümnaasiumi {haru.lower()} lõpetaja {aasta} {viitestring}'
        isikud = harud[haru]
        for isik in isikud:
            # Loome uue isiku
            isik_nimi = isik.strip().split(',')
            isik_eesnimi = isik_nimi[1].strip()
            isik_perenimi = isik_nimi[0].strip()
            if isik_eesnimi or isik_perenimi:
                # print(isik_eesnimi, isik_perenimi)
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
                    # pass
                # Lisame isiku artiklile
                art.isikud.add(uus_isik)
                # Lisame isiku pildile
                pilt.isikud.add(uus_isik)

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

def clean_orphan_images():
    # remove orphan pictures
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
    start_aasta = 1933
    stopp_aasta = 2022
    for aasta in range(start_aasta, stopp_aasta):
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

    with open(f'vilistlased{start_aasta}-{stopp_aasta-1}.json', mode='w', encoding='utf8') as f:
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

def check_profiilipildid_notin_pildid():
    for model in [Artikkel, Isik, Organisatsioon, Objekt]:
        objs = model.objects.all()
        for obj in objs:
            profiilipildid = obj.profiilipildid.all()
            if profiilipildid.count() > 0:
                for pilt in profiilipildid:
                    if pilt not in obj.pildid.all():
                        print(model, 'obj:', obj.id, 'pilt:', pilt.id)

# Ühe sisuga artiklite lisamiseks
def lisa_artikkel_20200321():
    hist_years = [1384, 1385, 1387, 1391, 1393, 1396, 1398, 1410, 1412]
    kirjeldus = 'Valgas toimus Liivimaa linnade päev'
    viide = Viide.objects.get(id=7841)
    for hist_year in hist_years:
        uus_art = Artikkel(
            hist_year = hist_year,
            kirjeldus = kirjeldus
        )
        uus_art.save()
        uus_art.viited.add(viide)
        print(uus_art.id, uus_art)

# Ühe sisuga artiklite lisamiseks
def lisa_artikkel_20230209():
    date_tuples = [
        (1879, 8, 18),
        (1879, 8, 27),
        (1879, 11, 2),
        (1879, 11, 9),
        (1880, 2, 4),
        (1880, 3, 14),
        (1880, 4, 11),
        (1880, 6, 27),
        (1880, 9, 12),
        (1880, 10, 10),
        (1880, 10, 24),
        (1881, 2, 6),
        (1881, 5, 25),
        (1881, 7, 1),
        (1881, 9, 2),
        (1881, 11, 27),
        (1882, 3, 8),
        (1882, 4, 29),
        (1882, 8, 16),
        (1882, 10, 1),
        (1882, 11, 11),
        (1883, 2, 9),
        (1883, 4, 27),
        (1883, 5, 5),
        (1883, 6, 13),
        (1883, 6, 17),
        (1883, 8, 1),
        (1883, 9, 1),
    ]
    kirjeldus = 'Peeti Valga linnavolikogu koosolek'
    viide = Viide.objects.get(id=13803)
    org = Organisatsioon.objects.get(id=3240)
    print(org, viide)
    for date_tuple in date_tuples:
        uus_art = Artikkel(
            hist_date = date(*date_tuple),
            kirjeldus = kirjeldus
        )
        uus_art.save()
        uus_art.viited.add(viide)
        uus_art.organisatsioonid.add(org)
        print(uus_art.id)


def getFilename_fromCd(cd):
    """
    Get filename from content-disposition
    """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]

def getFile_fromUrl(url):
    # url = 'http://google.com/favicon.ico'
    r = requests.get(url, allow_redirects=True)
    filename = getFilename_fromCd(r.headers.get('content-disposition'))
    contentLength = r.headers.get('content-length', None)
    print(filename, contentLength)
    open(filename, 'wb').write(r.content)


from django.contrib.postgres.search import TrigramSimilarity
def isik_trigram_word_similarity(nimi):
    nimi = nimi.replace(' ', '')
    isikud = Isik.objects.daatumitega(request=None). \
        annotate(isikunimi = Concat('eesnimi', 'perenimi')). \
        annotate(similarity = TrigramSimilarity("isikunimi", nimi)). \
        filter(similarity__gt = 0.3). \
        order_by("-similarity")
    for isik in isikud[:10]:
        print(isik.nimi(), isik.similarity)

from PIL import Image, ImageOps, ImageDraw
import qrcode
import qrcode.image.svg
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

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

def get_qrcode_from_uri():
    # uri = request.GET.get('uri')
    uri = 'https://www.valgagym.ee/vilistlased/annetus/'
    # taking image which user wants
    # in the QR code center
    Logo_link = settings.BASE_DIR / 'wiki/static/wiki/img/special/vg.png'

    logo = Image.open(Logo_link)
    new_image = Image.new("RGBA", logo.size, "WHITE")  # Create a white rgba background
    new_image.paste(logo, (0, 0), logo)  # Paste the image on the background. Go to the links given below for details.
    # new_image.convert('RGB').save('test.jpg', "JPEG")  # Save as JPEG
    logo = new_image

    # taking base width
    basewidth = 1000

    # adjust image size
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth - 300, hsize - 300), Image.LANCZOS)
    logo = ImageOps.expand(logo, border=50, fill='white')
    QRcode = qrcode.QRCode(
        box_size=100,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )

    # adding URL or text to QRcode
    QRcode.add_data(uri)

    # generating QR code
    QRcode.make()

    # taking color name from user
    QRcolor = '#4ea9dc'

    # adding color to QR code
    QRimg = QRcode.make_image(
        fill_color=QRcolor,
        back_color="white",
        # image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer()
    ).convert('RGB')

    # set size of QR code
    pos = ((QRimg.size[0] - logo.size[0]) // 2,
           (QRimg.size[1] - logo.size[1]) // 2)
    QRimg.paste(logo, pos)

    QRimg = add_corners(QRimg, 500)

    # save the QR code generated
    QRimg.save('gfg_QR.png')

    # print('QR code generated!')
    # stream = BytesIO()
    # QRimg.save(stream, "PNG")

    # image_data = base64.b64encode(stream.getvalue()).decode('utf-8')
    # im = Image.open('gfg_QR.png')
    # im = add_corners(im, 500)
    # im.save('gfg_QR_rounded.png')

# ilmaandmete täiendamiseks ilmateenistus.ee veebilehelt
from datetime import datetime, timezone
from decimal import *
import numpy as np
import time

from ilm.models import Jaam, Ilm
def update_ilmaandmed(aasta=2025):
    print('Loeme faili...')
    # Alusfail "C:\Users\kalev\Documents\itiasjad\django\kroonika\Valga-2004-juuni-2024.xlsx"
    df_bigdata = pd.read_excel("Valga-2025.xlsx", header=2)
    df = df_bigdata[df_bigdata['Aasta']==aasta]
    
    # Select only columns that are float64 and convert them to float32
    # float64_cols = df.select_dtypes(include=['float64']).columns
    # df[float64_cols] = df[float64_cols].map(Decimal)
    # Select only columns that are int64 and convert them to int32
    # int64_cols = df.select_dtypes(include=['int64']).columns
    # df[int64_cols] = df[int64_cols].map(Decimal)
    # df['Aasta'] = df['Aasta'].map(Decimal)
    
    print(df.info())
    print('Kontrollime kandeid...')
    jaam = 'Valga'
    j = Jaam.objects.filter(name=jaam).first()
    for i in range(df.shape[0]):
        time.sleep(0.1)
        if i%1_000 == 0:
            print(i)
        y = df.iloc[i]['Aasta']
        m = df.iloc[i]['Kuu']
        d = df.iloc[i]['Päev']
        t = df.iloc[i]['Kell (UTC)']
        timestamp = datetime(y, m, d, t.hour, t.minute, tzinfo=timezone.utc)
        row = dict()
        row['station'] = j  # lisame seose andmebaasiga Jaam
        row['timestamp'] = timestamp
        airpressure = df.iloc[i]['Õhurõhk jaama kõrgusel hPa']
        if not np.isnan(airpressure):
            row['airpressure'] = airpressure
        precipitations = df.iloc[i]['Tunni sademete summa mm']
        if not np.isnan(precipitations):
            row['precipitations'] = precipitations
        relativehumidity = df.iloc[i]['Suhteline õhuniiskus %']
        if not np.isnan(relativehumidity):
            row['relativehumidity'] = df.iloc[i]['Suhteline õhuniiskus %']
        airtemperature = df.iloc[i]['Õhutemperatuur °C']
        if not np.isnan(airtemperature):
            row['airtemperature'] = airtemperature
        airtemperature_min = df.iloc[i]['Tunni miinimum õhutemperatuur °C']
        if not np.isnan(airtemperature_min):
            row['airtemperature_min'] = airtemperature_min
        airtemperature_max = df.iloc[i]['Tunni maksimum õhutemperatuur °C']
        if not np.isnan(airtemperature_max):
            row['airtemperature_max'] = airtemperature_max
        winddirection = df.iloc[i]['10 minuti keskmine tuule suund']
        if not np.isnan(winddirection):
            row['winddirection'] = winddirection
        windspeed = df.iloc[i]['10 minuti keskmine tuule kiirus m/s']
        if not np.isnan(windspeed):
            row['windspeed'] = windspeed
        windspeedmax = df.iloc[i]['Tunni maksimum tuule kiirus m/s']
        if not np.isnan(windspeedmax):
            row['windspeedmax'] = windspeedmax
        ilm_vana = Ilm.objects.filter(timestamp=timestamp).first()
        if isinstance(ilm_vana, Ilm):
            if not np.isnan(airtemperature) and ilm_vana.airtemperature == None:
                ilm_vana.airtemperature = row['airtemperature']
                ilm_vana.save(update_fields=["airtemperature"])
                print('Uuendatud airtemperature', timestamp)
            if not np.isnan(airtemperature_min) and ilm_vana.airtemperature_min == None:
                ilm_vana.airtemperature_min = row['airtemperature_min']
                ilm_vana.save(update_fields=["airtemperature_min"])
                print('Uuendatud airtemperature_min', timestamp)
            if not np.isnan(airtemperature_max) and ilm_vana.airtemperature_max == None:
                ilm_vana.airtemperature_max = row['airtemperature_max']
                ilm_vana.save(update_fields=["airtemperature_max"])
                print('Uuendatud airtemperature_max', timestamp)
            if not np.isnan(precipitations) and ilm_vana.precipitations == None:
                ilm_vana.precipitations = row['precipitations']
                ilm_vana.save(update_fields=["precipitations"])
                print('Uuendatud precipitations', timestamp)
        else:
            print("Lisame: ", timestamp)
            for key, value in row.items():
                if isinstance(value, np.float64):
                    row[key] = float(value)
                if isinstance(value, np.int64):
                    row[key] = int(value)
            ilm_uus = Ilm(**row)
            try:
                ilm_uus.save()
            except Exception as e:
                print(f"Viga {e} andmete salvestamisel: {y} {m} {d} {t}:{row}")

def update_ilmaandmed_min_max():
    from ilm.utils import utils
    # Täiendame ilmaandmeid, millel on ainult timestamp ja station, aga puuduvad temperatuurid
    jaam = 'Valga'
    j = Jaam.objects.filter(name=jaam).first()
    ilmaandmed_min_puudu = Ilm.objects.filter(station=j, airtemperature_min__isnull=True)
    ilmaandmed_max_puudu = Ilm.objects.filter(station=j, airtemperature_max__isnull=True)
    ilmaandmed_puudu = ilmaandmed_min_puudu.union(ilmaandmed_max_puudu)
    print('Ilmaandmed, millel puudub airtemperature_min või airtemperature_max:', ilmaandmed_puudu.count())

    for ilm in ilmaandmed_puudu:
        print(ilm.timestamp)
        ilm_andmed_veebist = utils.get_maxmin_airtemperature(ilm.timestamp)
        if ilm_andmed_veebist:
            ilm.airtemperature_min = ilm_andmed_veebist['airtemperature_min']
            ilm.airtemperature_max = ilm_andmed_veebist['airtemperature_max']
            ilm.save(update_fields=["airtemperature_min", "airtemperature_max"])
            print(
                'Uuendatud', ilm.timestamp, 
                'airtemperature_min:', ilm.airtemperature_min, 
                'airtemperature_max:', ilm.airtemperature_max
            )

    ilmaandmed_min_puudu = Ilm.objects.filter(station=j, airtemperature_min__isnull=True)
    ilmaandmed_max_puudu = Ilm.objects.filter(station=j, airtemperature_max__isnull=True)
    ilmaandmed_puudu = ilmaandmed_min_puudu.union(ilmaandmed_max_puudu)
    print('Kontroll: Ilmaandmed, millel puudub airtemperature_min või airtemperature_max:', ilmaandmed_puudu.count())

def update_addresses_from_kaardiobjektid():
    kaardiobjektid = Kaardiobjekt.objects \
        .filter(tyyp='H') \
        .filter(kaart__aasta__in=[1905, 1912, 2021])
    for kaardiobjekt in kaardiobjektid:
        nimi = ' '.join([kaardiobjekt.tn, kaardiobjekt.nr])
        kirjeldus = kaardiobjekt.lisainfo
        viide = kaardiobjekt.kaart.viited.first()
        objekt = kaardiobjekt.objekt
        hist_year = kaardiobjekt.kaart.aasta

        aadress = Aadress(
            nimi=nimi,
            kirjeldus=kirjeldus,
            objekt=objekt,
            # viited=viide,
            hist_year=hist_year
        )
        aadress.save()
        aadress.viited.add(viide)

def update_addresses_from_aadressraamat_1909():
    """Process the data from the address book for 1909"""
    path = settings.BASE_DIR / 'wiki' / 'static' / 'wiki' / 'data'
    with open(path /'1909 majaomanikud.csv', encoding = 'UTF-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        hist_year = 1909
        viide = Viide.objects.get(id=14410)  # Adolf Richters Baltische Verkehrs- und Adressbücher
        print(f'Processing address book for year {hist_year} with reference {viide}:')
        for row in reader:
            tn = row[0].strip()
            nr = row[2].strip()
            # district = row[1].strip()
            nimi = ' '.join([tn, nr])
            kirjeldus = ' '.join(row)
            print(nimi, kirjeldus)

            aadress = Aadress(
                nimi=nimi,
                kirjeldus=kirjeldus,
                hist_year=hist_year
            )
            aadress.save()
            aadress.viited.add(viide)

def update_addresses_from_aadressraamat_1925():
    """Process the data from the address book for 1925"""
    path = settings.BASE_DIR / 'wiki' / 'static' / 'wiki' / 'data'
    with open(path /'1925 majaomanikud.csv', encoding = 'UTF-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        hist_year = 1925
        viide = Viide.objects.get(id=14811)  # walga juht
        print(f'Processing address book for year {hist_year} with reference {viide}:')
        for row in reader:
            tn = row[0].strip().replace('tänaw.', 'tänaw')
            nr = row[1].strip()
            nimi = ' '.join([tn, nr])
            kirjeldus = ' '.join(row)
            print(nimi, kirjeldus)

            aadress = Aadress(
                nimi=nimi,
                kirjeldus=kirjeldus,
                hist_year=hist_year
            )
            aadress.save()
            aadress.viited.add(viide)

def update_lisainfo_1912_kaardiobjektid():
    vasted = """
    Aia, Garten Strasse    
    Aleksandri, Alexander Strasse
    Allee, Allee Strasse
    Elisabeti, Elisabeth Strasse
    Isidori, Isidor Strasse
    Jaani, Johannen Strasse
    Kitsas, Schmal Strasse
    Köie, Grosse Reeper Strasse
    Liiva, Sand Strasse
    Matuseaia, Kirchhofs Strasse
    Mesipuu, Bienen Strasse
    Moskva, Moskausche Strasse
    Mäe, Berg Strasse
    Pihkva, Pleskausche Strasse
    Puškini, Puschkin Strasse
    Põllu, Feld Strasse
    Pärnu, Pernausche Strasse
    Riia, Rigasche Strasse
    Sauna, Badstuben Strasse
    Sepa, Schmiede Strasse
    Tartu, Die Jurjewsche Strasse
    Uus, Neu Strasse
    Viljandi, Fellinsche Strasse
    Vladimiri, Wladimir Strasse
    Väike Liiva, Kleine Sand Strasse
    Väike Mäe, Kleine Berg Strasse
    Väike Puškini, [Kleine Puschkin Strasse]
    """
    paarid = vasted.strip().split('\n')
    kaart = Kaart.objects.get(aasta='1912')
    for paar in paarid:
        tn = paar.split(',')[0].strip()
        print('Alustänav:', tn)
        kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart).filter(tn__startswith=tn)
        for kaardiobjekt in kaardiobjektid:
            lisainfo_aadress = ' '.join([paar.split(',')[1].strip(), kaardiobjekt.nr]) if kaardiobjekt.nr else paar.split(',')[1].strip()
            kaardiobjekt.lisainfo = ', '.join([lisainfo_aadress, kaardiobjekt.lisainfo]) if kaardiobjekt.lisainfo else lisainfo_aadress
            print(kaardiobjekt.lisainfo)
            kaardiobjekt.save()

def add_2021_kaardiobjekt_as_objekt():
    t2navad_wiki = Objekt.objects.filter(tyyp='T').filter(gone=False)
    viide = Viide.objects.get(id=10490)
    kaart = Kaart.objects.get(aasta='2021')
    kaardiobjektid2021_instances = Kaardiobjekt.objects.filter(kaart=kaart).filter(tyyp='H')
    kinnistud2021 = Kaardiobjekt.objects.filter(kaart=kaart).filter(tyyp='A')
    v2listame = [
        'Rigas iela', 'Jaanikese küla, Kaasiku', 'Jaanikese küla, Laasi'
    ]
    n = 0
    for kaardiobjekt in kaardiobjektid2021_instances:
        if kaardiobjekt.tn in v2listame:
            continue
        nimi = ' '.join([kaardiobjekt.tn, kaardiobjekt.nr]).strip()
        if not Objekt.objects.filter(nimi__exact=nimi).exists():
            print(kaardiobjekt, end="-> ")
            tn_wikis = t2navad_wiki.filter(nimi__icontains=kaardiobjekt.tn).first()
            n += 1
            objekt = Objekt(
                nimi=nimi,
                tyyp='H'
            )
            # print(tn_wikis)
            objekt.save()
            objekt.viited.add(viide)
            objekt.objektid.add(tn_wikis)
            objekt.kaardiobjektid.add(kaardiobjekt)
            if kinnistud2021.filter(tn=kaardiobjekt.tn, nr=kaardiobjekt.nr).exists():
                kinnistu = kinnistud2021.filter(tn=kaardiobjekt.tn, nr=kaardiobjekt.nr).first()
                objekt.kaardiobjektid.add(kinnistu)
            print('Lisatud:', objekt)
    print(n)
    
def add_2021_t2navad():
    t2navad_wiki = Objekt.objects.filter(tyyp='T').filter(gone=False)
    kaart = Kaart.objects.get(aasta='2021')
    kaardiobjektid2021_instances = Kaardiobjekt.objects.filter(kaart=kaart).filter(tyyp='H')
    t2navad_2021 = list(set([k.tn for k in kaardiobjektid2021_instances]))
    viide = Viide.objects.get(id=10490)
    v2listame = [
        'Enno', 'Kuperjanovi', 'Rigas iela', 'Jaanikese küla, Kaasiku', 'Jaanikese küla, Laasi'
    ]
    for el in v2listame:
        t2navad_2021.remove(el)

    for tn in t2navad_2021:
        if t2navad_wiki.filter(nimi__startswith=tn).exists():
            tn_wikis = t2navad_wiki.filter(nimi__startswith=tn).first()
            print('Olemas:', tn_wikis)
            tn_wikis.viited.add(viide)
        else:
            print('Pole:', tn)
            objekt = Objekt(
                nimi = tn + ' tänav',
                tyyp = 'T',
            )
            objekt.save()
            objekt.viited.add(viide)

from pyproj import Transformer

def sort_l_aadress(e):
    return e['properties']['l_aadress']

def read_valgalinn_from_ky_json() -> list:
    """Process the data from the address book for 1925"""
    path = settings.BASE_DIR / 'wiki' / 'static' / 'wiki' / 'data'
    with open(path /'Valga_vald_KATASTER_JSON.json', encoding = 'UTF-8') as jsonfile:
        data_valgavald = json.load(jsonfile)
        data_valgalinn = [
            feature 
            for feature 
            in data_valgavald["features"] 
            if feature["properties"]["ay_nimi"] == "Valga linn"
        ]
    data_valgalinn.sort(key=sort_l_aadress)
    return data_valgalinn

def get_t2navad(data_valgalinn: list) -> list:
    data_valgalinn_t2navad = [
        feature
        for feature 
        in data_valgalinn
        if feature["properties"]["siht1"] == "TRANSPORDIMAA"
    ]
    return data_valgalinn_t2navad

def get_t2nav(
    data_valgalinn_t2navad: list,
    t2nava_nimi: str
) -> list:
    data_t2nav = [
        feature
        for feature 
        in data_valgalinn_t2navad
        if feature["properties"]["l_aadress"].find(t2nava_nimi) == 0
    ]
    return data_t2nav

def transform2lonlat(coordinates: list) -> list:
    """
    Convert to Latitude/Longitude (WGS84)
    Maa-amet L-EST (3301) -> standard GPS Lat/Lon (4326)
    ex: [[[622543.1, 6406070.93]]] -> [[[26.05808628030382, 57.782056560299104]]]
    """
    transformer = Transformer.from_crs("EPSG:3301", "EPSG:4326", always_xy=True)
    new_coordinate = lambda lonlat: list(transformer.transform(*lonlat))
    new_coordinates = []
    for feature in coordinates:
        feature_coordinates = []
        for coordinate in feature:
            feature_coordinates.append(new_coordinate(coordinate))
        new_coordinates.append(feature_coordinates)
    return new_coordinates

# Valga linna tänavate loetelu Eesti geoportaali andmetel 09.08.2026
# https://aks.geoportaal.ee/aks-api/kaart/page/app/aksavalik
t2navad_geoportaal_2026 = """
Aasa tänav
Aia tänav
Alfred Neulandi tänav
Allika tänav
Andrese tänav
Antsla tänav
Astra tänav
Edela tänav
Eha tänav
Energia tänav
Ernst Enno tänav
Haava tänav
Haru tänav
Heina tänav
Herne tänav
Hiie tänav
Hommiku tänav
Hämariku tänav
Iirise tänav
Ilmajaama tänav
Jaama puiestee
Jakobi tänav
Julius Kuperjanovi tänav
Järve tänav
Jõe tänav
Kadaka tänav
Kaevu tänav
Kagu tänav
Kalda tänav
Kalevi tänav
Kanepi tänav
Karja tänav
Kase tänav
Kesk tänav
Kesva tänav
Kevade tänav
Kibuvitsa tänav
Kirde tänav
Kirsipuu tänav
Koidu tänav
Kolde tänav
Kreegi tänav
Kreegipuu tänav
Kullerkupu tänav
Kungla tänav
Kuuse tänav
Köie tänav
Laatsi tänav
Lai tänav
Leiva tänav
Lembitu tänav
Lepa tänav
Liiva tänav
Lille tänav
Loode tänav
Luha tänav
Lõuna tänav
Lühike tänav
Maasika tänav
Maleva tänav
Mee tänav
Mesipuu tänav
Metsa tänav
Muru tänav
Mädarõika tänav
Mäe tänav
Männi tänav
Männiku põik
Männiku tänav
Männipuu tänav
Märdi tänav
Mööbli tänav
Narva tänav
Nelgi tänav
Nurme tänav
Odra tänav
Oja tänav
Ojaperve tänav
Oru tänav
Pagari tänav
Paju tänav
Palu põik
Palu tänav
Pargi tänav
Pedeli tänav
Perve tänav
Petseri tänav
Pihlaka tänav
Piiri tänav
Piirilinna tänav
Pikk tänav
Pipra tänav
Pirni tänav
Pirnipuu tänav
Ploomi tänav
Ploomipuu tänav
Puiestee tänav
Puu tänav
Pärna puiestee
Pärnu tänav
Pääsusilma tänav
Põhja tänav
Põik tänav
Põllu tänav
Rahu tänav
Raja tänav
Raudtee tänav
Ravila tänav
Redise tänav
Riia tänav
Roheline tänav
Roosi tänav
Räni tänav
Rükkeli tänav
Saare tänav
Sambla tänav
Savi tänav
Saviaugu tänav
Sepa tänav
Siguri tänav
Sinepi tänav
Sinilille tänav
Sireli tänav
Soo tänav
Spordi tänav
Sulevi tänav
Suve tänav
Sõpruse tänav
Sügise tänav
Talve tänav
Tambre tee
Tamme tänav
Tartu tänav
Tehase tänav
Tehnika tänav
Telliskivi tänav
Tibina tee
Tiigi tänav
Tolli tänav
Toogi põik
Toogi tänav
Toominga tänav
Torni tänav
Tulbi tänav
Turu tänav
Tuubi tänav
Tuule tänav
Tähe tänav
Tõrva tänav
Tööstuse tänav
Umb tänav
Uus tänav
Uus-Koidu tänav
Vaarika tänav
Vabaduse tänav
Vahe tänav
Vahtra tänav
Vaikne tänav
Vainu tänav
Valguse tänav
Valli tänav
Vana-Tambre tee
Vee tänav
Veski tänav
Viadukti tänav
Videviku tänav
Viinamarja tänav
Viljandi tänav
Väike-Köie tänav
Väike-Laatsi tänav
Väike-Lepa tänav
Väike-Nelgi tänav
Välja tänav
Võnnu tänav
Võru tänav
Võsa tänav
Õhtu tänav
Õunapuu tänav
Ülase tänav
"""

siht1 = {
    'ARIMAA', 
    'JAATMEHOIDLA_MAA', 
    'TOOTMISMAA', 
    'UHISKONDLIKE_EHITISTE_MAA', 
    'ELAMUMAA', 
    'TRANSPORDIMAA', 
    'ULDKASUTATAV_MAA', 
    'MAATULUNDUSMAA', 
    'RIIGIKAITSEMAA', 
    'SIHTOTSTARBETA_MAA', 
    'VEEKOGUDE_MAA'
}

siht1_uldkasutatav_maa = [
    # 'Ilmajaama tn 3', 
    # 'Transpordi tn 1b', 
    # 'Tartu tn 81a', 
    # 'Kirde tn 2', 
    # 'Pedeli luht', 
    'Räni org 1', 
    'Räni org 2', 
    # 'Valli tn 34', 
    # 'Lembitu tn 13', 
    # 'Kesva tn 7', 
    # 'Torni tn 9', 
    # 'Kungla tn 43a', 
    # 'Pikk tn 21', 
    # 'Riia tn 3a', 
    # 'Rükkeli tn 2', 
    # 'Saviaugu tn 7', 
    'Tambre oja 1', 
    'Tambre oja 2', 
    'Tambre oja 3', 
    # 'Pipra tn 1a', 
    # 'Saviaugu tn 3', 
    # 'Lohu tn 1', 
    'Plantsi', 
    'Pedeli virgestusala 3', 
    # 'Siguri tn 4', 
    # 'Kirde tn 10', 
    # 'Viljandi tn 69', 
    # 'Metsa tn 11', 
    # 'Tartu tn 34', 
    # 'Pärna pst 17a', 
    # 'Raja tn 12', 
    'Pedeli virgestusala 1', 
    # 'Pärnu tn 9', 
    # 'Uus tn 4a', 
    # 'Uus tn 10b', 
    # 'Uus tn 8b', 
    # 'Aia tn 10', 
    # 'Vabaduse tn 8a', 
    # 'Vabaduse tn 6a', 
    # 'Aia tn 12a', 
    # 'Puiestee tn 6b', 
    # 'Allika tn 9', 
    # 'Jaama pst 2f', 
    # 'Vabaduse tn 1', 
    # 'Jaama pst 1b', 
    # 'Kungla tn 30a', 
    # 'Allika tn 2c', 
    # 'J. Kuperjanovi tn 36a', 
    # 'Allika tn 8a', 
    # 'Kungla tn 24b', 
    # 'Saviaugu tn 1', 
    # 'Torni tn 14', 
    # 'Peebu tn 2', 
    # 'Roosi tn 2', 
    # 'Vahtra tn 30', 
    # 'Pikk tn 29', 
    # 'Viadukti tn 1', 
    # 'J. Kuperjanovi tn 78a', 
    'Linnamets 2', 
    'Linnamets 3', 
    # 'Eha tn 4', 
    'Linnamets 4', 
    'Linnamets 5', 
    'Linnamets 6', 
    'Linnamets 7', 
    # 'Viadukti tn 2', 
    # 'Palu põik 2', 
    # 'Võru tn 117', 
    # 'Saviaugu tn 5', 
    # 'Uus tn 41', 
    # 'Lille tn 20', 
    # 'Veski tn 24a', 
    'Räni org 3', 
    # 'Tartu tn 111', 
    # 'Sireli tn 2a', 
    # 'Pedeli jõgi', 
    # 'Transpordi tn 4', 
    'Pedeli virgestusala 2', 
    'Linnamets 1'
]

siht1_riigikaitsemaa = [
    # 'Pikk tn 16', 
    # 'Pikk tn 16b', 
    'Piiririba', 
    'Metsaääre', 
    # 'Sepa tn 15', 
    # 'Puiestee tn 2', 
    # 'Puiestee tn 4', 
    # 'Allika tn 2b', 
    # 'Jaama pst 16', 
    # 'Võru tn 12', 
    'Piiririba', 
    # 'Torni tn 22', 
    # 'Karja tn 16', 
    'Sepa tänav T1', 
    'Sõpruse tänav T1', 
    'Piiririba lõik 3', 
    'Piiririba lõik 4', 
    'Piiririba lõik 2', 
    'Piiririba lõik 7', 
    'Piiririba lõik 8', 
    'Piiririba lõik 5', 
    'Piiririba lõik 9', 
    'Piiririba lõik 1', 
    'Piiririba lõik 6'
]

siht1_veekogude_maa = [
    'Võsa tn 7a', 
    'Pirni tn 1a', 
    'Põllu tn 4a'
]

def get_address_data(
    address_query: str, 
    etak_tyyp: str = '',
    unik: str = '0', # kas üksusel peab olema unikaalne aadress
    ky: str = '1',
    poi: str = '1',
    knr: str = '1',
    appartments: str = '1', # kas näidatakse kortereid
    results: int = 100, # kui palju vasteid max tagastatakse
) -> list:
    """
    Otsingute tegemiseks geoportaalist
    """
    ETAK_TYYP = {
        '': "EHAK,TANAV,EHITISHOONE,KATASTRIYKSUS", # kõik
        'H': 'EHITISHOONE', # maja
        'T': 'TANAV',
        'E': 'EHITISHOONE', # sild, laululava,
        'A': 'KATASTRIYKSUS', # plats, piirkond, asustusüksus
        'M': 'EHAK,KATASTRIYKSUS', # sh looduslikud objektid
    }

    # Otsing ei tule toime tänavate täispikkade isikunimedega tänavanimetustega ja 
    # tuleb kasutada lühendeid
    if etak_tyyp == 'T':
        for eesnimi in ['Alfred', 'Ernst', 'Julius']:
            address_query = address_query.replace(eesnimi + ' ', '')
        address_query = address_query.replace('tänav', 'tn').replace('puiestee', 'pst')

    # API Request to Maa-amet ADS Gazetteer
    url = "https://aks.geoportaal.ee/inaks/inaadress/gazetteer"
    params = {
        "address": address_query,
        "features": ETAK_TYYP[etak_tyyp],
        "ehak": "8918",
        "iTappAsendus": "0",
        "out": "json",
        "unik": unik, #
        "ky": ky,
        "appartments": appartments,
        "poi": poi,
        "knr": knr,
        "results": results
    }

    response = requests.get(url, params=params)
    # response.raise_for_status()
    if response.status_code != 200:
        return None

    data = response.json()

    if not data.get("addresses"):
        return None

    # Kontrollime otsingu täpsust ja vajadusel filtreerime valed välja
    # Kesk 12 != Kesk 12a
    # Lepa != Väike-Lepa
    address_query_regex = r'(\s.+\s|\s)'.join(address_query.split())
    pattern = re.compile(rf'(^|.+)(?<!-){address_query_regex}($|\s)')
    addresses = [
        addr
        for addr
        in data["addresses"]
        if pattern.match(addr["pikkaadress"])
    ]
    return addresses

def check_t2navad_exists(t2navad_geoportaal_2026):
    """
    Kontrollime kas tänava nimetus on:
    Objekt andmebaasis
    Leitav kaardiportaalist õige vastega
    """
    t2navad_geoportaal_2026_list = [
        t2nav.strip()
        for t2nav
        in t2navad_geoportaal_2026.strip().split('\n')
    ]
    for t2nav in t2navad_geoportaal_2026_list:
        o = Objekt.objects.filter(tyyp='T', nimi__startswith=t2nav).first()
        addresses = get_address_data(t2nav, 'T')
        if o:
            message = f'Olemas: {t2nav} -> {o}'
            print(message, end=' ')
            logger.info(message)
        else:
            message = f'Pole: {t2nav}'
            print("Pole:", t2nav, end=' ')
            logger.warning(message)
        if addresses:
            message = f'Geoportaalis: {len(addresses)}'
            print(message)
            if len(addresses) > 0:
                print(addresses[0]['aadresstekst'])
                message += f' -> {addresses[0]['aadresstekst']}'
            logger.info(message)
        else:
            message = "Geoportaalis ei leitud"
            print(message)
            logger.warning(message)
        time.sleep(1)

def transform_address_bbox(
        g_boundingbox: str
) -> dict:
    # Vahetab lat <-> lon koordinaadid Leafleti jaoks
    address_bbox_coordinates = g_boundingbox.split()
    coordinates = [
        [
            float(coord.split(',')[1]),
            float(coord.split(',')[0])
        ]
        for coord
        in address_bbox_coordinates
    ]
    return {
      "type": "Polygon",
      "coordinates": [coordinates]
    }

def upd_add_t2navad(
    t2navad_geoportaal_2026: str
) -> None:
    """
    Kontrollime kas tänava nimetus on:
    Objekt andmebaasis
    Leitav kaardiportaalist õige vastega
    Kui pole, loome uue
    Loome kaardiobjektid ja seome tänavaga
    """

    kaart = Kaart.objects.get(aasta=2026)
    viide = kaart.viited.first()

    t2navad_geoportaal_2026_list = [
        t2nav.strip()
        for t2nav
        in t2navad_geoportaal_2026.strip().split('\n')
    ]
    for t2nav in t2navad_geoportaal_2026_list:
        objekt = Objekt.objects.filter(tyyp='T', nimi__startswith=t2nav).first()

        if objekt:
            message = f'Olemas: {t2nav} -> {objekt}'
            print(message, end=' ')
            logger.info(message)
        else:
            message = f'Pole: {t2nav}'
            print(message)
            logger.warning(message)
            objekt = Objekt(
                nimi=t2nav,
                tyyp='T',
            )
            objekt.save()
            message = f'Lisatud: {objekt}'
            print(message)
            logger.info(message)

        objekt.viited.add(viide)

        # kaardiobjektid_geoportaalist = get_address_data(t2nav, 'T')
        # if kaardiobjektid_geoportaalist:
        #     message = f"Geoportaalis: {len(kaardiobjektid_geoportaalist)}"
        #     print(message)
        #     if len(kaardiobjektid_geoportaalist) > 0:
        #         message = f'Kontroll: {kaardiobjektid_geoportaalist[0]['aadresstekst']}'
        #         print(message)
        #         logger.info(message)
        #         for kaardiobjekt_geoportaalist in kaardiobjektid_geoportaalist:
        #             kaardiobjekt = Kaardiobjekt(
        #                 kaart=kaart,
        #                 tn=kaardiobjekt_geoportaalist['aadresstekst'],
        #                 tyyp='A',
        #                 geometry=transform_address_bbox(
        #                     kaardiobjekt_geoportaalist['g_boundingbox']
        #                 ),
        #                 lisainfo=json.dumps(
        #                     kaardiobjekt_geoportaalist, 
        #                     indent=2
        #                 ),
        #                 objekt=objekt,
        #             )
        #             kaardiobjekt.save()
        #             objekt.kaardiobjektid.add(kaardiobjekt)
        #             message = f"Lisatud KO: {kaardiobjekt}"
        #             logger.info(message)
        # else:
        #     message = f"Geoportaalis ei leitud {t2nav}"
        #     print(message)
        #     logger.warning(message)
        # time.sleep(1)

def add_t2navad_from_json_data(
    t2navad_geoportaal_2026: str,
    data_valgalinn_t2navad: list
) -> None:
    kaart = Kaart.objects.get(aasta=2026)
    viide = kaart.viited.first()

    t2navad_geoportaal_2026_list = [
        t2nav.strip()
        for t2nav
        in t2navad_geoportaal_2026.strip().split('\n')
    ]

    for t2nav in t2navad_geoportaal_2026_list:
        objekt = Objekt.objects.filter(tyyp='T', nimi__startswith=t2nav).first()
        data_t2nav = get_t2nav(data_valgalinn_t2navad, t2nav)
        for part in data_t2nav:
            print(part["properties"]["l_aadress"])
            coordinates = part["geometry"]["coordinates"] # [[[622426.11, 6406338.99], [622440.76, 6406344.28], [622409.34, 6406398.81], [622391.59, 6406429.59], [622386.09, 6406439.99], [622357.56, 6406489.67], [622329.48, 6406539.36], [622321.08, 6406554.23], [622307.89, 6406546.23], [622335.95, 6406496.55], [622375.9, 6406426.46], [622387.02, 6406408.05], [622405.37, 6406375.24], [622426.11, 6406338.99]]]
            wgs_coordinates = transform2lonlat(coordinates)
            geometry = {
                "type": "Polygon",
                "coordinates": wgs_coordinates,
            }
            # print(new_coordinates)
            kaardiobjekt = Kaardiobjekt(
                kaart=kaart,
                tn=part["properties"]["l_aadress"],
                tyyp='A',
                geometry=geometry,
                lisainfo=json.dumps(
                    part, 
                    indent=2
                ),
                objekt=objekt,
            )
            kaardiobjekt.save()
            objekt.kaardiobjektid.add(kaardiobjekt)
            message = f"Lisatud KO: {kaardiobjekt}"
            logger.info(message)

from django.db import models
from django.contrib.postgres.search import TrigramSimilarity, TrigramWordSimilarity
def object_trigram_word_similarity(
    nimi: str,
    qs: models.QuerySet
) -> models.QuerySet:
    # nimi = nimi.replace(' ', '')
    qs = qs. \
        annotate(similarity = TrigramWordSimilarity(nimi, "nimi")). \
        filter(similarity__gt = 0.3). \
        order_by("-similarity")
    # for obj in qs[:10]:
    #     print(obj.nimi, obj.similarity)
    return qs

def get_building_geometry(search_string):
    """
    Fetches building shape from Maa-amet (ETAK) using the Building Register (EHR) code.
    """
    # WFS Service URL
    wfs_url = "https://gsavalik.envir.ee/geoserver/etak/wfs"
    # wfs_url = "https://gsavalik.envir.ee/geoserver/etak/wfs?request=GetFeature&service=WFS&version=1.1.0&outputFormat=json&typeName=etak:e_401_hoone_ka&cql_filter=ehr_gid=111015176&srsName=EPSG:4326"
    # wfs_url = "https://gsavalik.envir.ee/geoserver/etak/wfs?request=GetFeature&service=WFS&version=1.1.0&outputFormat=application%2Fjson&typeName=etak:e_401_hoone_ka&cql_filter=ads_lahiaadress%3D%27Aasa%20tn%2012%27&srsName=EPSG:4326"

    params = {
        "request": "GetFeature",
        "service": "WFS",
        "version": "2.0.0",
        "outputFormat": "json",
        "typeName": "etak:e_401_hoone_ka",
        # "typeName": "etak:e_403_muu_rajatis_ka",
        "cql_filter": f"ads_lahiaadress='{search_string}'",
        "srsName": "EPSG:4326",  # Standard Lat/Lon degrees
    }

    try:
        response = requests.get(
            wfs_url,
            params=params,
        )
        response.raise_for_status()
        data = json.loads(response.text)

        if not data.get("features"):
            return f"No geometry found for: {search_string}"

        # Extracting the geometry and some properties
        features = data["features"]
        return features

    except Exception as e:
        return f"Error: {e}"


from wiki.utils import shp_util

def check_ky(
    data_valgalinn: list
) -> None:
    kaart = Kaart.objects.get(aasta=2026)
    viide = kaart.viited.first()
    objektid_qs = Objekt.objects.exclude(gone=True).filter(hist_endyear__isnull=True)
    objektid_t2navad = objektid_qs.filter(tyyp='T')
    objektid_eiolet2navad = objektid_qs.exclude(tyyp='T')
    for ky in data_valgalinn[1000:1500]:
        # Kontrollime, kas on transpordimaa
        if ky['properties']['siht1'] == 'TRANSPORDIMAA':
            continue
        l_aadress = ky['properties']['l_aadress']
        coordinates = ky["geometry"]["coordinates"] # [[[622426.11, 6406338.99], [622440.76, 6406344.28], [622409.34, 6406398.81], [622391.59, 6406429.59], [622386.09, 6406439.99], [622357.56, 6406489.67], [622329.48, 6406539.36], [622321.08, 6406554.23], [622307.89, 6406546.23], [622335.95, 6406496.55], [622375.9, 6406426.46], [622387.02, 6406408.05], [622405.37, 6406375.24], [622426.11, 6406338.99]]]
        wgs_coordinates = transform2lonlat(coordinates)
        geometry = {
            "type": "Polygon",
            "coordinates": wgs_coordinates,
        }
        
        l_aadress_for_t2nav_search = [
            ['J. ', 'Julius '],
            ['E. ', 'Ernst '],
            ['A. ', 'Alfred '],
            ['tn', 'tänav'],
            ['pst ', 'puiestee'],
        ]
        l_aadress_for_t2nav = l_aadress
        for translation in l_aadress_for_t2nav_search:
            l_aadress_for_t2nav.replace(translation[0], translation[1])

        # Otsime vasted wikist
        t2nav = object_trigram_word_similarity(l_aadress_for_t2nav, objektid_t2navad).first()
        objekt = object_trigram_word_similarity(l_aadress, objektid_eiolet2navad).first()
        # Kontrollime otsingu täpsust ja vajadusel filtreerime valed välja
        # Kesk 12 != Kesk 12a
        # Lepa != Väike-Lepa
        if objekt:
            address_query_regex = r'(\s.+\s|\s)'.join(objekt.nimi.split())
            pattern = re.compile(rf'(^|.+)(?<!-){address_query_regex}($|\s)')
            if not pattern.match(l_aadress):
                objekt = None

        objektid_geoportaalist_addr = get_address_data(l_aadress, 'H')
        if objektid_geoportaalist_addr:
            ehitisi_aadr = len(objektid_geoportaalist_addr)
        else:
            ehitisi_aadr = None
        objektid_geoportaalist_etak = get_building_geometry(l_aadress)
        if objektid_geoportaalist_etak:
            ehitisi_etak = 0
            for feature in objektid_geoportaalist_etak:
                if isinstance(feature, dict) and shp_util.check_polygon_contains_polygon(
                    feature['geometry'],
                ):
                    ehitisi_etak += 1
        else:
            ehitisi_etak = None
        # objektid_geoportaalist_etak = shp_util.get_shp_data_ehitis(l_aadress)
        # ehitisi_etak = len(objektid_geoportaalist_etak)
        # time.sleep(1)

        message = f'{l_aadress} -> T: {t2nav} -> O: {objekt}: E ADR: {ehitisi_aadr} E ETAK: {ehitisi_etak}'
        print(message)
        if not t2nav or not objekt or not ehitisi_aadr or not ehitisi_etak:
            logger.warning(message)
        else:
            logger.info(message)

        # ky -> loome kaardiobjekti ky-st
        kaardiobjekt_ky = Kaardiobjekt(
            kaart=kaart,
            tn=ky["properties"]["l_aadress"],
            tyyp='A',
            geometry=geometry,
            lisainfo=json.dumps(
                ky, 
                indent=2
            ),
            # objekt=objekt,
        )
        kaardiobjekt_ky.save()
        message = f"Lisatud ky KO KY: {kaardiobjekt_ky.id} {kaardiobjekt_ky}"
        logger.info(message)

        if l_aadress in (
            siht1_uldkasutatav_maa + 
            siht1_riigikaitsemaa + 
            siht1_veekogude_maa
        ):
            message = f'{l_aadress} -> loome ainult kaardiobjekti'
            print(message)
            logger.info(message)
            continue
        
        if not isinstance(objekt, Objekt):
            if ehitisi_etak > 0:
                # loome objekti
                objekt = Objekt(
                    nimi=l_aadress,
                    tyyp='H',
                )
                objekt.save()
                if t2nav:
                    # lisame objektile seose t2navaga
                    objekt.objektid.add(t2nav)
                message = f'Loodud OBJEKT {objekt.id} {objekt}'
                print(message)
                logger.info(message)
            else:
                continue # loome ainult kaardiobjekti

        # lisame viite objektile
        objekt.viited.add(viide)
        # lisame ky kaardiobjektile seose objektiga
        objekt.kaardiobjektid.add(kaardiobjekt_ky)

        # lisame ETAK ehitiste andmed
        if ehitisi_etak > 0:
            for feature in objektid_geoportaalist_etak:
                if isinstance(feature, dict) and shp_util.check_polygon_contains_polygon(
                    feature['geometry'],
                ):
                    # lisame kaardiobjekti
                    geometry = feature['geometry']
                    tn = ky["properties"]["l_aadress"]
                    kaardiobjekt_etak = Kaardiobjekt(
                        kaart=kaart,
                        tn=tn,
                        tyyp='H',
                        geometry=geometry,
                        lisainfo=json.dumps(
                            feature, 
                            indent=2
                        ),
                        objekt=objekt,
                    )
                    kaardiobjekt_etak.save()
                    # lisame kaardiobjektile seose objektiga
                    # objekt.kaardiobjektid.add(kaardiobjekt_etak)
                    message = f"Lisatud KO ETAK: {kaardiobjekt_etak.id} {kaardiobjekt_etak}"
                    logger.info(message)
            


if __name__ == "__main__":
    # get_vg_vilistlased()
    # get_muis_vamf()
    # muis_viited_inuse()
    # url = 'http://opendata.muis.ee/dhmedia/2d69b089-d435-45a2-92f0-2f4f28784e58'
    # getFile_fromUrl(url)
    data_valgalinn = read_valgalinn_from_ky_json()
    # data_valgalinn_t2navad = get_t2navad(data_valgalinn)
    # data_t2nav = get_t2nav(data_valgalinn_t2navad, "Sulevi tänav")
    # for t2nav in data_t2nav:
    #     print(t2nav["properties"]["l_aadress"])
    #     coordinates = t2nav["geometry"]["coordinates"] # [[[622426.11, 6406338.99], [622440.76, 6406344.28], [622409.34, 6406398.81], [622391.59, 6406429.59], [622386.09, 6406439.99], [622357.56, 6406489.67], [622329.48, 6406539.36], [622321.08, 6406554.23], [622307.89, 6406546.23], [622335.95, 6406496.55], [622375.9, 6406426.46], [622387.02, 6406408.05], [622405.37, 6406375.24], [622426.11, 6406338.99]]]
    #     new_coordinates = transform2lonlat(coordinates)
    #     print(new_coordinates)
    # upd_add_t2navad(t2navad_geoportaal_2026)
    # add_t2navad_from_json_data(t2navad_geoportaal_2026, data_valgalinn_t2navad)
    check_ky(data_valgalinn)
    # search_string = 'Sulevi tn 9a'
    # features = get_building_geometry(search_string)
    # for feature in features:
    #     json.dumps(feature, indent=2)
    logger.info('Done.')

# import importlib
# importlib.reload(module)
