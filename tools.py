from wiki.models import Artikkel, Isik, Organisatsioon, Objekt, Pilt, Allikas

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
        objektid = old.organisatsioonid.all()
        for objekt in objektid:
            print(objekt.id, objekt)
            new.organisatsioonid.add(objekt)
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

