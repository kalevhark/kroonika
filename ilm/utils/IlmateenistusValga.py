from datetime import datetime, timedelta
import re
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from astral import LocationInfo, moon
from astral.sun import sun
from bs4 import BeautifulSoup
from django.db import connection
from django.db.models import Sum, Count, Avg, Min, Max
import numpy as np
import xml.etree.ElementTree as ET
import pytz
from pytz import timezone
import requests
# from shapely import length

if __name__ == '__main__':
    import os
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()

from ilm.models import Ilm, Jaam
from ilm.utils import utils
from ilm.utils.utils import sun_moon, ilman2htus_yrnosymboliks

"""
Ilmateenistuse terminid:
Öösel  21-05 
Öö hakul (õhtupoole ööd, enne keskööd)  21-00 
Kesköö paiku  23-02 
Hommikupoole ööd  03-05 
Hommikul  05-09 
Päeval  09-17 
Ennelõunal  09-12 
Keskpäeval  12-14 
Pärastlõunal  14-17 
Õhtul  17-21
"""
# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value)
    except:
        return None

# def sun_moon(dt):
#     # Tagastab konkreetese kuupäeva (ajavööndi väärtusega) päikese- ja kuuandmed
#     # Vana Astral
#     # city_name = 'Tallinn'
#     # a = Astral()
#     # a.solar_depression = 'civil'
#     # city = a[city_name]
#     # s = {}
#     # s['sun'] = city.sun(date=dt, local=True)
#     # s['moon'] = a.moon_phase(date=dt)
#     # Uus Astral
#     tallinn_tz = timezone('Europe/Tallinn')
#     city = LocationInfo("Valga", "Estonia", "Europe/Tallinn", 57.776944, 26.031111)
#     s = {}
#     sun_states = sun(city.observer, dt)
#     for state in sun_states.keys():
#         sun_states[state] = sun_states[state].astimezone(tallinn_tz)
#     s['sun'] = sun_states
#     s['moon'] = moon.phase(date=dt)
#     return s


# def ilman2htus_yrnosymboliks(phenomenon, dt):
#     """
#     Tagastab symboli väärtuse vastavalt tabelile:
#     https://cdn.jsdelivr.net/gh/YR/weather-symbols@7.0.0/dist/svg/
#     prognoosi sümbolile lisatakse vastavalt päeva- või ööajale 'd' või 'n'
#     """
#     if phenomenon == None:
#         return None
#     phenomenon = phenomenon.lower()
#     phenomenons = {
#         'clear': '01',
#         'selge': '01',
#         'nähtusteta': '01',
#         'few clouds': '02',
#         'vähene pilvisus': '02',
#         'variable clouds': '03',
#         'poolpilves': '03',
#         'cloudy with clear spells': '03',
#         'peamiselt pilves': '03',
#         'cloudy': '04',
#         'pilves': '04',
#         'light snow shower': '44',
#         'nõrk hooglumi': '44',
#         'moderate snow shower': '08',
#         'mõõdukas hooglumi': '08',
#         'heavy snow shower': '45',
#         'tugev hooglumi': '08',
#         'light shower': '46',
#         'nõrk hoogvihm': '46',
#         'moderate shower': '09',
#         'mõõdukas hoogvihm': '09',
#         'heavy shower': '10',
#         'tugev hoogvihm': '10',
#         'light rain': '46',
#         'nõrk vihm': '46',
#         'moderate rain': '09',
#         'mõõdukas vihm': '09',
#         'vihm': '09',
#         'heavy rain': '10',
#         'tugev vihm': '10',
#         'glaze': '15',
#         'jäide': '15',
#         'jäätuv uduvihm': '15',
#         'jääkruubid': '15',
#         'light sleet': '47',
#         'nõrk lörtsisadu': '47',
#         'nõrk vihm koos lumega': '47',
#         'sademed': '47',
#         'moderate sleet': '12',
#         'mõõdukas lörtsisadu': '12',
#         'light snowfall': '44',
#         'nõrk lumesadu': '44',
#         'nõrk lumi': '44',
#         'moderate snowfall': '08',
#         'mõõdukas lumesadu': '08',
#         'lumi': '08',
#         'heavy snowfall': '45',
#         'tugev lumesadu': '45',
#         'blowing snow': '45',
#         'üldtuisk': '45',
#         'drifting snow': '44',
#         'pinnatuisk': '44',
#         'hail': '48',
#         'rahe': '48',
#         'mist': '15',
#         'uduvine': '15',
#         'fog': '15',
#         'udu': '15',
#         'thunder': '06',
#         'äike': '06',
#         'thunderstorm': '25',
#         'äikesevihm': '25'
#     }
#     if phenomenon in phenomenons:
#         symbol = phenomenons[phenomenon]
#     else:
#         symbol = None
#     # Kas lisada d või n vastavalt valgele või pimedale ajale
#     if symbol == None or symbol in [
#             '04', '09', '10', '11', '12', '13', '14', '15',
#             '22', '23', '30', '31', '32', '33', '34',
#             '46', '47', '48', '49', '50'
#             ]:
#         return symbol
#     sun = sun_moon(dt)['sun']
#     if dt > sun['sunrise'] and dt < sun['sunset']:
#         symbol = symbol + 'd'
#     else:
#         symbol = symbol + 'n'
#     return symbol

def logi(dt, andmed, allikas):
    # Andmete kasutus konsooli
    print(
        allikas,
        dt.strftime("%d.%m.%Y"),
        f'{dt.hour:>2}', end=' '
    )
    if allikas != 'E:':  # Kui ei ole vigased andmed
        # Värvikoodid
        CEND = '\33[0m'    # neutral
        CRED = '\33[91m'   # punane
        CBLUE = '\33[94m'  # sinine
        CGREEN = '\33[32m' # roheline

        print(((CRED if andmed["airtemperature"] >= 0 else CBLUE) + f'{andmed["airtemperature"]:+5}' + CEND) if (andmed["airtemperature"] != None) else f'{"-":>5}',
            f'{andmed["airpressure"]:6}' if andmed["airpressure"] else f'{"-":>6}',
            andmed['phenomenon']
        )
    else:
        print()

class IlmateenistusData():
    """
    Andmed Ilmateenistuse andmebaasist ja nende töötlused
    """

    def __init__(self):
        # Lähteandmed vormides
        dt = pytz.timezone('Europe/Tallinn').localize(datetime.now())
        self.aasta = dt.year
        self.kuu = dt.month
        self.p2ev = dt.day

        # 24h andmete cache
        self.cache24h = dict()
        algus = dt - timedelta(hours=24)
        qs = Ilm.objects.filter(timestamp__gt=algus).values()
        for el in qs:
            # Teisendame Decimal väljad Float väljadeks
            el['airtemperature'] = float_or_none(el['airtemperature'])
            el['windspeed'] = float_or_none(el['windspeed'])
            el['winddirection'] = float_or_none(el['winddirection'])
            el['airpressure'] = float_or_none(el['airpressure'])
            el['precipitations'] = float_or_none(el['precipitations'])
            # Salvestame cache
            self.cache24h[el['timestamp']] = el
        # print('Cache:', len(self.cache24h))

        # Leiame andmebaasi esimese ja viimase kirje ajad
        self.bdi_startstopp()

        # Ajalooliste andmete päringukirjeldused
        # Täisaastad
        if (self.start.month == 1) and (self.start.day == 1):
            t2isaasta_min = self.start.year
        else:
            t2isaasta_min = self.start.year + 1
        if (self.stopp.month == 12) and (self.stopp.day == 31):
            t2isaasta_max = self.stopp.year
        else:
            t2isaasta_max = self.stopp.year - 1

        self.qs_years = Ilm.objects \
            .filter(timestamp__year__gte = t2isaasta_min, timestamp__year__lte = t2isaasta_max) \
            .values('timestamp__year') \
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations')) \
            .order_by('timestamp__year')

        # 12 kuud
        self.qs12 = Ilm.objects \
            .values('timestamp__month') \
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature')) \
            .order_by('timestamp__month')

        # 12 kuud aastate kaupa
        self.qs_kuud = (
            Ilm.objects
            .filter(precipitations__gt=0)
            .values('timestamp__year', 'timestamp__month')
            .annotate(
                Sum('precipitations'),
                days_with_precipitation=Count('timestamp__day', distinct=True)
            )
            .order_by('timestamp__year', 'timestamp__month')
        )

        # 366 päeva
        self.qs366 = Ilm.objects \
            .values('timestamp__month', 'timestamp__day') \
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature')) \
            .order_by('timestamp__month', 'timestamp__day')
        
        # Agregeeritud näitajad kuupäevade kaupa
        self.qs_days_maxmin = Ilm.objects \
            .values('timestamp__year', 'timestamp__month', 'timestamp__day') \
            .annotate(Max('airtemperature_max'), Min('airtemperature_min'), Avg('airtemperature'), Sum('precipitations')) \
            .order_by('timestamp__year', 'timestamp__month', 'timestamp__day')

        # 366 x 24h
        self.qs8784 = Ilm.objects \
            .values('timestamp__month', 'timestamp__day', 'timestamp__hour') \
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature')) \
            .order_by('timestamp__month', 'timestamp__day', 'timestamp__hour')
        

    def bdi_startstopp(self):
        # Leian andmebaasi ajaliselt esimese ja viimase kande aja
        qs = list(Ilm.objects.aggregate(Min('timestamp'), Max('timestamp')).values())
        self.start = qs[0] if qs[0] else datetime.now()
        self.stopp = qs[1] if qs[1] else datetime.now()
        format = '%d.%m.%Y'
        text = f'Andmed: {self.start.strftime(format)}-{self.stopp.strftime(format)}'
        return text

    def mitutundi(self, algus, l6pp):
        # Tagastab kahe kuupäeva vahe tundides
        return (l6pp-algus).days * 24 + (l6pp-algus).seconds/3600

    def viimase24h_andmed(self, jaam, hetke_aeg):
        d = pytz.timezone('Europe/Tallinn').localize(datetime.now())
        # tunniloendur
        algus = hetke_aeg - timedelta(hours=23)
        # andmeloendid
        temperature = []
        symbol = []
        windbarb = []
        airpressure = []
        precipitation = []
        # Erinevus UTC ja kohaliku ajavööndi vahel
        utcoffset = algus.utcoffset()

        while algus < d: # Kogu päev kuni praeguse hetkeni
            # Päring kas on 24h cache hulgas
            if algus in self.cache24h:
                veebiandmed =  self.cache24h[algus]
                allikas = 'C:'
            else:
                # Päring andmebaasist, kas ilmaandmed olemas
                qs = Ilm.objects.filter(
                    timestamp__year=algus.year,
                    timestamp__month=algus.month,
                    timestamp__day=algus.day,
                    timestamp__hour=algus.hour).values().first()
                if qs: # Kui leiti andmebaasist
                    veebiandmed = qs
                    # Teisendame DecimalField väljad float tüübiks
                    veebiandmed['airtemperature'] = float_or_none(veebiandmed['airtemperature'])
                    veebiandmed['windspeed'] = float_or_none(veebiandmed['windspeed'])
                    veebiandmed['winddirection'] = float_or_none(veebiandmed['winddirection'])
                    veebiandmed['airpressure'] = float_or_none(veebiandmed['airpressure'])
                    veebiandmed['precipitations'] = float_or_none(veebiandmed['precipitations'])
                    allikas = 'D:'
                else: # Kui ei, siis hangitakse veebist
                    # veebiandmed = self.ilmaandmed_veebist(algus)
                    veebiandmed = utils.ilmaandmed_veebist(algus)
                    # Ilmaandmed andmebaasi juhul kui põhiandmed olemas
                    if veebiandmed and veebiandmed['airtemperature'] != None:
                        i = Ilm(**veebiandmed)
                        i.save()
                        print('Salvestan andmebaasi:', algus, veebiandmed['airtemperature'])
                    # allikas = 'W:'
                if veebiandmed:
                    if veebiandmed['airtemperature'] != None:
                        self.cache24h[algus] = veebiandmed

            if veebiandmed:  # Kui tunniandmed olemas
                # Graafiku nullpunktist tundide arv
                tund = self.mitutundi(
                    hetke_aeg - timedelta(hours=23),
                    veebiandmed['timestamp']
                )
                temperature.append([tund, veebiandmed['airtemperature']])
                windbarb.append([
                    veebiandmed['windspeed'], veebiandmed['winddirection']
                ])
                symbol.append(ilman2htus_yrnosymboliks(veebiandmed['phenomenon'], veebiandmed['timestamp']))
                airpressure.append([tund, veebiandmed['airpressure']])
                precipitation.append([tund, veebiandmed['precipitations']])
            else:
                allikas = 'E:'  # Näitame et saime valed andmed

            # Logi
            # logi(algus, veebiandmed, allikas)
            algus += timedelta(hours=1)

        # Lisame viimase mõõtmise andmed
        # i = self.ilm_praegu()
        i = utils.ilm_praegu()
        if i and i['airtemperature']: # Kui andmed saadi
            tund = self.mitutundi(
                hetke_aeg - timedelta(hours=23),
                i['timestamp']
            )
            temperature.append([tund, i['airtemperature']])
            airpressure.append([tund, i['airpressure']])
            humidity_string = str(int(i['relativehumidity'])) + '% '
            windspeed_string = str(i['windspeed']) + ' m/s'
            dt = i['timestamp']
            dt_string = dt.strftime("%d.%m.%Y %H:%M")

            # Teeme ilmandmete stringi
            if temperature[-1][1] < 0:
                color = '#48AFE8'  # Kui negatiivne, siis sinine
            else:
                color = '#FF3333'  # Kui positiivne, siis sinine
            temperature_string = f'{temperature[-1][1]:+.1f}°C'
            temperature_color_span = f'<span style="color: {color}">{temperature_string}</span>'
            ilmastring = f'{dt_string}: {temperature_color_span} {humidity_string} {windspeed_string}'
        else: # Viimase eduka mõõtmise andmed
            dt_delta = 23 - temperature[-1][0]
            dt = datetime.now() - timedelta(hours=dt_delta)
            dt_string = dt.strftime("%d.%m.%Y %H:00")
            ilmastring = f'-'

        andmed = dict()
        andmed['airtemperatures'] = temperature
        andmed['symbols'] = symbol
        andmed['windbarbs'] = windbarb
        andmed['airpressures'] = airpressure
        andmed['precipitations'] = precipitation
        andmed['ilmastring'] = ilmastring
        return andmed


def add_data(failinimi):
    from datetime import datetime
    import pytz
    from ilm.models import Ilm, Jaam
    import csv

    # Ilmaandmete andmebaasi kirjeldus
    before = Ilm.objects.count()
    ilm_fields = dict()
    fields = Ilm._meta.get_fields()
    field_names = []
    for field in fields:
        ilm_fields[field.name] = field.deconstruct()
        if not field.name == 'id':
            field_names.append(field.name)
    # Ilmaandmete lisamine andmebaasi
    f = 'ilm/static/ilm/bdi/' + failinimi
    jaam = 'Valga'
    j = Jaam.objects.filter(name=jaam).first()
    with open(f, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',', fieldnames=field_names)
        firstline = True
        for row in reader:
            if firstline:    #skip first line
                firstline = False
                continue
            row['station'] = j #lisame seose andmebaasiga Jaam
            row['timestamp'] = pytz.timezone('Europe/Tallinn').localize(
                datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                )
            for el in row:
                if row[el] == '':
                    row[el] = None
                if row[el]:
                    if el not in [
                        'station',
                        'cloudiness',
                        'phenomenon',
                        'phenomenon_observer',
                        'timestamp']:
                        row[el] = float(row[el])
            i = Ilm(**row)
            i.save()
            print(i)
    after = Ilm.objects.count()
    print(before, after)
    return before, after

def longest_period_aboveandbelow(verbose=False):
    longest_periods = {}
    days = Ilm.objects \
        .values('timestamp__year', 'timestamp__month', 'timestamp__day') \
        .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature')) \
        .order_by('timestamp__year', 'timestamp__month', 'timestamp__day')
    
    
    if verbose:
        print('pikim periood: päevakeskmine ei ole alla nulli')
    period = {
        'start_date': None,
        'end_date': None,
        'length': 0
    }
    length = 0
    for day in days:
        if day['airtemperature__avg'] >= 0:
            if length == 0:
                start_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            else:
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            length += 1
            if period['length'] < length:
                period['start_date'] = start_date
                period['end_date'] = end_date
                period['length'] = length
        else:
            length = 0
    if verbose:
        print(period)
    longest_periods['above_avg_zero_longest'] = period

    if verbose:
        print('pikim periood: päevamiinumum ei ole alla nulli')
    period = {
        'start_date': None,
        'end_date': None,
        'length': 0
    }
    length = 0
    for day in days:
        if day['airtemperature__min'] >= 0:
            if length == 0:
                start_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            else:
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            length += 1
            if period['length'] < length:
                period['start_date'] = start_date
                period['end_date'] = end_date
                period['length'] = length
        else:
            length = 0
    if verbose:
        print(period)
    longest_periods['above_min_zero_longest'] = period

    if verbose:
        print('pikim periood: päevakeskmine ei ole üle nulli')
    period = {
        'start_date': None,
        'end_date': None,
        'length': 0
    }
    length = 0
    for day in days:
        if day['airtemperature__avg'] < 0:
            if length == 0:
                start_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            else:
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            length += 1
            if period['length'] < length:
                period['start_date'] = start_date
                period['end_date'] = end_date
                period['length'] = length
        else:
            length = 0
    if verbose:
        print(period)
    longest_periods['below_avg_zero_longest'] = period

    if verbose:
        print('pikim periood: päevamaksimum ei ole üle nulli')
    period = {
        'start_date': None,
        'end_date': None,
        'length': 0
    }
    length = 0
    for day in days:
        if day['airtemperature__max'] < 0:
            if length == 0:
                start_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            else:
                end_date = [day['timestamp__year'], day['timestamp__month'], day['timestamp__day']]
            length += 1
            if period['length'] < length:
                period['start_date'] = start_date
                period['end_date'] = end_date
                period['length'] = length
        else:
            length = 0
    if verbose:
        print(period)
    longest_periods['below_max_zero_longest'] = period

    return longest_periods

def calc_month_maxmin(verbose=False):
    qs_kuud = (
        Ilm.objects
        .filter(precipitations__gt=0)
        .values('timestamp__year', 'timestamp__month')
        .annotate(
            Sum('precipitations'),
            days_with_precipitation=Count('timestamp__day', distinct=True)
        )
    )
    # Teeme tühja tabeli
    ii8 = np.iinfo(np.int8) 
    month_maxmin = {
        month: {
            'precipitations__sum': 0, 
            'precipitations__sum__timestamp__year': None,
            'days_with_precipitation': 0, 
            'days_with_precipitation__timestamp__year': None,
            'airtemperature_max__max': ii8.min,
            'airtemperature_max__max__timestamp': None,
            'airtemperature_min__min': ii8.max,
            'airtemperature_min__min__timestamp': None,
        } 
        for month 
        in range(1, 13)
    }
    for row in qs_kuud:
        month = row['timestamp__month']
        if month_maxmin[month]['precipitations__sum'] < row['precipitations__sum']:
            month_maxmin[month]['precipitations__sum'] = row['precipitations__sum']
            month_maxmin[month]['precipitations__sum__timestamp__year'] = row['timestamp__year']
        if month_maxmin[month]['days_with_precipitation'] < row['days_with_precipitation']:
            month_maxmin[month]['days_with_precipitation'] = row['days_with_precipitation']
            month_maxmin[month]['days_with_precipitation__timestamp__year'] = row['timestamp__year']

    # Agregeeritud näitajad kuupäevade kaupa
    days_maxmin_qs = Ilm.objects \
        .values('timestamp__year', 'timestamp__month', 'timestamp__day') \
        .annotate(Max('airtemperature_max'), Min('airtemperature_min'), Avg('airtemperature'), Sum('precipitations')) \
        .order_by('timestamp__year', 'timestamp__month', 'timestamp__day')
    for row in days_maxmin_qs:
        month = row['timestamp__month']
        date = datetime(row['timestamp__year'], row['timestamp__month'], row['timestamp__day'])
        if month_maxmin[month]['airtemperature_max__max'] < row['airtemperature_max__max']:
            month_maxmin[month]['airtemperature_max__max'] = row['airtemperature_max__max']
            month_maxmin[month]['airtemperature_max__max__timestamp'] = date
        if month_maxmin[month]['airtemperature_min__min'] > row['airtemperature_min__min']:
            month_maxmin[month]['airtemperature_min__min'] = row['airtemperature_min__min']
            month_maxmin[month]['airtemperature_min__min__timestamp'] = date

    if verbose:
        print(month_maxmin)

    return month_maxmin


if __name__ == '__main__':
    # see osa koodist käivitub, kui mooodul panna tööle käsurealt
    # (topeltklõps, must aken, IDLE's F5 vms)
    ##    run()
    STATIC_DIR = 'static/ilm/bdi/'
    bdi = IlmateenistusData()
    # longest_period_aboveandbelow(verbose=True)
    calc_month_maxmin(bdi, verbose=True)