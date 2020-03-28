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
    isik_str = 'Lydia Arras, Emilie Hanny, Meeta Jänes, Hilda Juram, Emilie Kask, Amali Nõgene, Alwine Patte, Marie Püwi, Jenni Rebane, Margarethe Stahl, Helmi Tinn, Irmgard Trees, Lilli Tõra, Natalie Wellner, Linda Zirk'
    # Millise artikliga siduda isik
    art = Artikkel.objects.get(id=6912)
    print(art)
    # Millise pildiga siduda isik
    pilt = Pilt.objects.get(id=2055)
    print(pilt)
    # Milline organisatsioon lisada isikule
    org = Organisatsioon.objects.get(id=33)
    print(org)
    # Milline viide lisada isikule
    viide = Viide.objects.get(id=7807)
    print(viide)
    # Isiku kirjeldus
    isik_kirjeldus = 'Tütarlastegümnaasiumi lõpetaja 1922'
    isikud = isik_str.split(',')
    for isik in isikud:
        # Loome uue isiku
        isik_nimi = isik.strip().split(' ')
        isik_eesnimi = isik_nimi[0].strip()
        isik_perenimi = isik_nimi[1].strip()
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
        # Lisame isikule seotud viite
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

# Geoinfo hankimine ip-aadressi järgi
def ipggeoinfo(ip_addr=''):
    ip_locate_url = 'https://geolocation-db.com/jsonp/' + ip_addr
    with urllib.request.urlopen(ip_locate_url) as url:
        data = url.read().decode()
        data = data.split("(")[1].strip(")")
        print(data)
    return data

# IP aadressi kohta WHOIS info
# eeldus pip install --upgrade ipwhois
def whoisinfo(ip_addr=''):
    obj = IPWhois(ip_addr)
    whois_data = obj.lookup_rdap(asn_methods=["whois"])
    return whois_data