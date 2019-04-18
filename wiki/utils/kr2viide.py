"""
Tükk kroonikaraamatu andmete lisamiseks viidete hulka
Kasutamiseks samasse kataloogi, kus models.py
# Django shellis kataloogis 'home/kalev/kroonika/' käivitamiseks: exec(open('wiki/kr2viide.py').read())
"""
from django.contrib.auth.models import User
from wiki.models import Artikkel, Allikas, Viide, Kroonika

# Nullime Viide andmebaasi
Viide.objects.all().delete()
# Muudame kasutajana 'admin'
user = User.objects.get(username='admin')
# Käsitleme ainult Duvini kroonikaraamatut
kroonika = Kroonika.objects.get(id=1)
# Valime ainult Duvini raamatu artiklid
artiklid = Artikkel.objects.filter(kroonika=kroonika)
# Valime allikaks eelnevalt kirjeldatud Duvini kroonikaraamatu kande
allikas = Allikas.objects.get(id=1)

# Käime läbi kõik kirjed
for obj in artiklid:
    print(obj.lehekylg, obj.id, end=' ')
    # Lisame uue viite
    viide = Viide(
        allikas=allikas,
        hist_year=2005,
        kohaviit=f'lk {obj.lehekylg}'
    )
    viide.save()
    print(viide.id)
    # Salvestame viite artikli juurde
    obj.viited.set([viide.id])
    # obj.updated_by.set([user])
    obj.save()

