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
    viide = Viide(
        allikas=allikas,
        hist_year=2005,
        kohaviit=f'lk {obj.lehekylg}'
    )
    viide.save()
    obj.viited.add(viide.id)
    obj.save()
    print(obj.lehekylg)

