"""
Tükk kroonikaraamatu andmete lisamiseks viidete hulka
"""
from wiki.models import Artikkel, Allikas, Viide, Kroonika

# Käsitleme ainult Duvini kroonikaraamatut
kroonika = Kroonika.objects.get(id=1)
# Valime ainult Duvini raamatu artiklid
artiklid = Artikkel.objects.filter(kroonika=kroonika)
# Valime allikaks eelnevalt kirjeldatud Duvini kroonikaraamatu kande
allikas = Allikas.objects.get(id=1)

# Käime läbi kõik kirjed
for obj in artiklid:
    print(obj.lehekylg, obj.id)
    # Lisame uue viite
    viide = Viide(
        allikas=allikas,
        hist_year=2005,
        kohaviit=f'lk {obj.lehekylg}'
    )
    viide.save()
    # Salvestame viite artikli juurde
    obj.viited = viide.id
    obj.save()

