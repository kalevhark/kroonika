# Arhiiv taaskasutamise jaoks:
from django.shortcuts import render

#
# Jõulutervituse lehekülg 2019
#
def special_j6ul2019(request):
    tervitaja = request.META['QUERY_STRING']
    # Kui tervituses on mitu osa
    tykid = tervitaja.split('&')
    # Filtreerime välja FB lisa
    tervitaja = '&'.join([tykk.replace('+', ' ') for tykk in tykid if 'fbclid=' not in tykk])
    if tervitaja:
        tervitaja = tervitaja[:30]
    else:
        tervitaja = 'valgalinn.ee'
    return render(
        request,
        'wiki/special/wiki_special_j6ul2019.html',
        {
            'tervitaja': tervitaja,
        }
    )

#
# Jõulutervituse lehekülg 2020
#
def special_j6ul2020(request):
    tervitaja = request.META['QUERY_STRING']
    # Kui tervituses on mitu osa
    tykid = tervitaja.split('&')
    # Filtreerime välja FB lisa
    tervitaja = '&'.join([tykk.replace('+', ' ') for tykk in tykid if 'fbclid=' not in tykk])
    if tervitaja:
        tervitaja = tervitaja[:30]
        if tervitaja == 'XKH':
            tervitaja = 'Kalev Härk'
    else:
        tervitaja = 'valgalinn.ee'
    return render(
        request,
        'wiki/special/wiki_special_j6ul2020.html',
        {
            'tervitaja': tervitaja,
        }
    )

#
# Jõulutervituse lehekülg 2021
#
def special_j6ul2021(request):
    tervitaja = request.META['QUERY_STRING']
    # Kui tervituses on mitu osa
    tykid = tervitaja.split('&')
    # Filtreerime välja FB lisa
    tervitaja = '&'.join([tykk.replace('+', ' ') for tykk in tykid if 'fbclid=' not in tykk])
    if tervitaja:
        tervitaja = tervitaja[:30]
        if tervitaja == 'XKH':
            tervitaja = 'Kalev Härk'
    else:
        tervitaja = 'valgalinn.ee'
    from django.utils import timezone
    if timezone.now().year == 2021:
        pyhadesoov = 'Ilusat jõuluaega!'
    else:
        pyhadesoov = 'Head uut aastat!'
    return render(
        request,
        'wiki/special/wiki_special_j6ul2021.html',
        {
            'tervitaja': tervitaja,
            'pyhadesoov': pyhadesoov
        }
    )

#
# Linna sünnipäevatervituse lehekülg 436
#
def special_valga436(request):
    return render(
        request,
        'wiki/special/wiki_special_valga436.html',
        {}
    )

#
# Linna sünnipäevatervituse lehekülg 437
#
def special_valga437(request):
    return render(
        request,
        'wiki/special/wiki_special_valga437.html',
        {}
    )