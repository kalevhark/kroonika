"""
xml-failist andmebaasi kerimiseks.
Kasutamiseks samasse kataloogi, kus models.py
Django shellis kataloogis 'home/kalev/kroonika/' käivitamiseks: exec(open('wiki/ocr2db.py').read())
"""

import os
import xml.etree.ElementTree as ET
from wiki.models import Artikkel, Kroonika

print('Jooksev kataloog', os.getcwd()) # Jooksev kataloog kontrolliks

# Allikas:
kroonika = Kroonika.objects.get(pk=1)

# Artikleid enne failitöötlust
artikleid_enne = Artikkel.objects.count()

# OCR faili lugemine
fn = 'wiki/static/wiki/ocr/1944.xml'
print(fn)

tree = ET.parse(fn)
root = tree.getroot()

# Aasta:
hist_year = int(root.attrib['hist_year'])
i = 0

for lk in root.iter('lk'):
    lehekylg = int(lk.attrib['lk'])
    for art in lk.iter():
        if len((art.text).strip()) > 0:
            a = Artikkel(
                kroonika=kroonika,
                lehekylg=lehekylg,
                hist_year=hist_year,
                body_text=art.text.strip()
                )
            # a.save()
            i += 1
            print(f'id={a.id} lk={a.lehekylg} len={len(art.text)}', art.text)

# Artikleid pärast failitöötlust
artikleid_p2rast = Artikkel.objects.count()

print('Kirjete muutus: +', i, artikleid_enne, '->', artikleid_p2rast)
        


