import csv

from datetime import date, datetime, timedelta

from django.db.models import (
    Case, F, Q, Value, When,
    BooleanField, DateField, DateTimeField, DecimalField, IntegerField,
    ExpressionWrapper
)
from django.db.models.functions import Extract, Trunc, ExtractDay

from ipwhois import IPWhois

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt, Pilt, Allikas, Viide


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
Wiktor Änilane, Herman Jentson, Herbert Karu, Walentin Treumuth, Eduard Tõra, Wiktor Jõgi, Karl-Julius Karu, Robert Lillimägi, Johannes Lippert, Igor Padrik, Alfred Parron, Olew Saag, Anatooli Zimmermann, Julius Kõiw, Jaan Olli
    """
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=9252)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=5326)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org = Organisatsioon.objects.get(id=2743) # 33=tüt gümn, 85=poeg gymn, 2736=vene gymn, 2770=läti kesk, saksa eragymn, 19=6.algkool
    print(org)
    # Milline viide lisada isikule
    viited_ids = [10032]
    viited = Viide.objects.filter(id__in=viited_ids)
    print(viited)
    # Isiku kirjeldus
    isik_kirjeldus = 'Tööstuskooli esimese lennu lõpetaja 1928'
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
def task_art7358():
    art = Artikkel.objects.get(id=7358)
    pil = Pilt.objects.get(id=2625)
    for isik in art.isikud.all():
        print(isik)
        pil.isikud.add(isik)
    for obj in art.objektid.all():
        print(obj)
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