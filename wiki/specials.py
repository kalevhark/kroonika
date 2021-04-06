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
# Jõulutervituse lehekülg 2019
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
# Linna sünnipäevatervituse lehekülg (pole kasutuses)
#
def special_valga436(request):
    return render(
        request,
        'wiki/special/wiki_special_valga436.html',
        {}
    )