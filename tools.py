from datetime import date, datetime, timedelta

from django.db.models import (
    Case, F, Q, Value, When,
    BooleanField, DateField, DateTimeField, DecimalField, IntegerField,
    ExpressionWrapper
)
from django.db.models.functions import Extract, Trunc

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

    # Seotud viited
    viited = old.viited.all()
    print('Viited:')
    for viide in viited:
        print(viide.id, viide)
        new.viited.add(viide)

    # Seotud andmebaasid
    if model_name == 'isik':
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
        print('Artiklid:')
        artiklid = Artikkel.objects.filter(objektid=old)
        for art in artiklid:
            print(art.id, art)
            art.objektid.add(new)
            # art.objektid.remove(old)
        print('Pildid:')
        pildid = Pilt.objects.filter(objektid=old)
        for pilt in pildid:
            print(pilt.id, pilt)
            pilt.objektid.add(new)
            # pilt.objektid.remove(old)

# Isikukirjete tekitamiseks artikli juurde
# import tools
# tools.massikanne()
def massikanne():
    # Millised isikud lisada artiklile
    isik_str = """
    Herta Blum,
    Elisabeth Edenberg,
    Armanda Elken,
    Lydia Hanschmidt,
    Johanna Kurvits,
    Linda Kurvits,
    Rufina Kõiv,
    Marta Kämbre,
    Noora Laar,
    Linda Lentso,
    Anna Madisson,
    Ljubov Must,
    Linda Müllerson,
    Hilda Needing,
    Erika Padjas,
    Alide Rebane,
    Anna Rotberg,
    Veronika Suija,
    Minna Zirk,
    Alice Trzeciak,
    Linda Umalas,
    Aniita Vassil
    """
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=7252)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=2425)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org = Organisatsioon.objects.get(id=33) # 33=tüt gümn
    print(org)
    # Milline viide lisada isikule
    viited_ids = [8135, 8148]
    viited = Viide.objects.filter(id__in=viited_ids)
    print(viited)
    # Isiku kirjeldus
    isik_kirjeldus = 'Valga Linna Tütarlastegümnaasiumi lõpetaja 1923'
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
def topelt_viidete_kustutamine():
    from django.db.models import Count
    # Kasutud viited
    tyhjad_viited = Viide.objects.annotate(
        num_art=Count('artikkel__id'),
        num_isik=Count('isik__id'),
        num_org=Count('organisatsioon__id'),
        num_obj=Count('objekt__id'),
        num_pilt=Count('pilt__id')
    ).filter(
        num_art=0, num_isik=0, num_org=0, num_obj=0, num_pilt=0
    )
    tyhjad_viited_ids = [viide.id for viide in tyhjad_viited]
    print(len(tyhjad_viited_ids))
    # Kroonikaraamatu viited
    allikas = Allikas.objects.get(id=1)
    # K6ik viited v2lja arvatud kroonikaraamatust
    viited = Viide.objects.exclude(allikas=allikas).exclude(id__in=tyhjad_viited_ids)
    topelt_viited = viited.\
        values('peatykk', 'hist_date', 'kohaviit').\
        annotate(kohaviit_num=Count('kohaviit')).\
        filter(kohaviit_num__gt=1).\
        order_by('hist_date')
    for topelt_viide in topelt_viited:
        hist_date = topelt_viide['hist_date']
        kohaviit = topelt_viide['kohaviit']
        # Topeltviidete id
        topelt_viide_ids = [el.id for el in viited.filter(hist_date=hist_date, kohaviit=kohaviit)]
        print(topelt_viide_ids)
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
            print('-')
        print('- - -')


# Näide päringust uue kalendri kuupäeva järgi
def query_by_ukj():
    artiklid = Artikkel.objects.filter(hist_date__isnull=False)
    artiklid_ukj_j2rgi = artiklid.annotate(
        hist_date_ukj=Case(
            When(hist_date__gt=date(1919, 1, 31), then=F('hist_date')),
            When(hist_date__gt=date(1900, 2, 28), then=F('hist_date') + timedelta(days=13)),
            When(hist_date__gt=date(1800, 2, 28), then=F('hist_date') + timedelta(days=12)),
            When(hist_date__gt=date(1700, 2, 28), then=F('hist_date') + timedelta(days=11)),
            When(hist_date__gt=date(1582, 10, 5), then=F('hist_date') + timedelta(days=10)),
            default=F('hist_date'),
            output_field=DateField()
        )
    )
    # day = 15
    # print(artiklid_ukj_j2rgi.filter(hist_date_ukj__day=day).count())
    return artiklid_ukj_j2rgi

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