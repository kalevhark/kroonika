import calendar
from datetime import datetime, timedelta
import json

import logging
from sqlite3 import Row
logger = logging.getLogger(__name__)

import os
from pathlib import Path
import tempfile

import django
from django.conf import settings
import pandas as pd
import pytz
import redis
# import requests

if __name__ == "__main__":
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    # setup_test_environment()

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.db.models import F, RowRange, Window, Count, Sum, Avg, Min, Max

from django.http import JsonResponse
from django.shortcuts import render

from ilm.forms import NameForm
from ilm.models import Ilm
from ilm.utils import utils, IlmateenistusValga
import ilm.utils.ephem_util as ephem_data

if settings.REDIS_INUSE:
    redis_client = redis.Redis(host=settings.REDIS_HOST, port=6379, db=0)

bdi = IlmateenistusValga.IlmateenistusData()

KUUD = [
    '', # Tühi selleks et kuunumber=indeks
    'jaanuar',
    'veebruar',
    'märts',
    'aprill',
    'mai',
    'juuni',
    'juuli',
    'august',
    'september',
    'oktoober',
    'november',
    'detsember'
]
TMP_ALGUSKUVA = Path(tempfile.gettempdir()) / '_valgalinn.ee_ilm.tmp'

# Highcharts vaikevärvid
COLORS = [
    "#7cb5ec", # helesinine
    "#434348", # tumehall
    "#90ed7d", # heleroheline
    "#f7a35c", # oranzh
    "#8085e9", # lillakas sinine
    "#f15c80", # tumeroosa
    "#e4d354", # murtud roheline
    "#2b908f", # sinakas roheline
    "#f45b5b", # kahvatu punane
    "#91e8e1" # murtud heleroheline
]

# Temperatuuride värvid
COLORS_TEMP = {
    'negative': '#48AFE8', # helesinine
    'positive': '#FF3333'  # helepunane
}

# OpenWeatherMaps ilmakoodid
OWM_CODES = {
    "200": "nõrk äikesevihm", # thunderstorm with light rain;Thunderstorm
    "201": "äikesevihm", # thunderstorm with rain;Thunderstorm
    "202": "tugev äikesevihm", # thunderstorm with heavy rain;Thunderstorm
    "210": "nõrk äike", # light thunderstorm;Thunderstorm
    "211": "äike", # thunderstorm;Thunderstorm
    "212": "tugev äike", # heavy thunderstorm;Thunderstorm
    "221": "äge äike", # ragged thunderstorm;Thunderstorm
    "230": "nõrk äikesevihm", # thunderstorm with light drizzle;Thunderstorm
    "231": "äikesevihm", # thunderstorm with drizzle;Thunderstorm
    "232": "tugev äikesevihm", # thunderstorm with heavy drizzle;Thunderstorm
    "300": "nõrk uduvihm", # light intensity drizzle;Drizzle
    "301": "uduvihm", # drizzle;Drizzle
    "302": "tugev uduvihm", # heavy intensity drizzle;Drizzle
    "310": "kerge uduvihm", # light intensity drizzle rain;Drizzle
    "311": "uduvihm", # drizzle rain;Drizzle
    "312": "tugev uduvihm", # heavy intensity drizzle rain;Drizzle
    "313": "tugev uduvihm", # shower rain and drizzle;Drizzle
    "314": "tugev uduvihm", # heavy shower rain and drizzle;Drizzle
    "321": "tugev uduvihm", # shower drizzle;Drizzle
    "500": "nõrk vihm", # light rain;Rain
    "501": "vihm", # moderate rain;Rain
    "502": "tugev vihm", # heavy intensity rain;Rain
    "503": "väga tugev vihm", # very heavy rain;Rain
    "504": "ekstreemne vihmasadu", # extreme rain;Rain
    "511": "külmuv vihm", # freezing rain;Rain
    "520": "nõrk paduvihm", # light intensity shower rain;Rain
    "521": "paduvihm", # shower rain;Rain
    "522": "tugev paduvihm", # heavy intensity shower rain;Rain
    "531": "väga tugev paduvihm", # ragged shower rain;Rain
    "600": "kerge lumesadu", # light snow;Snow
    "601": "lumesadu", # Snow;Snow
    "602": "tugev lumesadu", # Heavy snow;Snow
    "611": "lörts", # Sleet;Snow
    "612": "kerge lörtsisadu", # Light shower sleet;Snow
    "613": "tugev lörtsisadu", # Shower sleet;Snow
    "615": "kerge lörtsisadu", # Light rain and snow;Snow
    "616": "lörts", # Rain and snow;Snow
    "620": "kerge lumesadu", # Light shower snow;Snow
    "621": "lumesadu", # Shower snow;Snow
    "622": "tugev lumesadu", # Heavy shower snow;Snow
    "701": "uduvine", # mist;Mist
    "711": "suits", # Smoke;Smoke
    "721": "vine", # Haze;Haze
    "731": "liiva-/tolmupöörised", # sand/ dust whirls;Dust
    "741": "udu", # fog;Fog
    "751": "liiv", # sand;Sand
    "761": "tolm", # dust;Dust
    "762": "vulkaaniline tuhk", # volcanic ash;Ash
    "771": "tuulepuhangud", # squalls;Squall
    "781": "tornaado", # tornado;Tornado
    "800": "selge", # clear sky;Clear
    "801": "õrn pilvisus", # few clouds: 11-25%;Clouds
    "802": "vahelduv pilvisus", # scattered clouds: 25-50%;Clouds
    "803": "vahelduv pilvisus", # broken clouds: 51-84%;Clouds
    "804": "pilvine", # overcast clouds: 85-100%;Clouds
}

# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value)
    except:
        return None

def float_or_zero(value):
    try:
        return float(value)
    except:
        return 0

def index(request):
    # Avalehekülg, kus näidatakse 24h ilmaajalugu + 48h prognoos
    history = utils.get_ilmateenistus_history()
    sun = ephem_data.get_sun_data()
    current_weather = utils.get_ilmateenistus_now()
    forecasts = utils.get_forecasts(hours=12)

    context = {
        # 'weather': weather,
        'history': history,
        'sun': sun,
        'current_weather': current_weather,
        'forecasts': forecasts,
        # 'ilm_ilmateenistus_now': ilm_ilmateenistus_now,
        # 'ilm_ilmateenistus_forecast': ilm_ilmateenistus_forecast
    }
    return render(request, 'ilm/index.html', context)

def history(request):
    # Ajalooliste ilmaandmete töötlused
    # saab ka küsida kujul /ilm/history/?aasta=2019&kuu=1&p2ev=1
    params = request.GET # Kas on parameetrid, kui jah, siis kasutada neid v6i vaikimisi salvestatud
    aasta = params.get('aasta')
    if aasta:
        try:
            aasta = int(aasta)
        except:
            aasta = bdi.aasta
        kuu = params.get('kuu')
        if kuu:
            try:
                kuu = int(kuu)
            except:
                kuu = bdi.kuu
            p2ev = params.get('p2ev')
            try:
                p2ev = int(p2ev)
            except:
                p2ev = 1
        else:
            kuu = 1
            p2ev = 1
    try:
        testime_kuup2eva = datetime(int(aasta), int(kuu), int(p2ev)) # Kas küsitud kuupäev on loogiline
        bdi.aasta = aasta
        bdi.kuu = kuu
        bdi.p2ev = p2ev
        form = NameForm(initial={'aasta': aasta, 'kuu': kuu, 'p2ev': p2ev})
    except:
        form = NameForm(initial={'aasta': bdi.aasta, 'kuu': bdi.kuu, 'p2ev': bdi.p2ev})

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NameForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            bdi.aasta = form.cleaned_data['aasta']
            bdi.kuu = form.cleaned_data['kuu']
            bdi.p2ev = form.cleaned_data['p2ev']

    return render(
        request,
        'ilm/history.html',
        {
            'form': form
        }
    )


def container_history_andmed(request):
    andmed = {'parameetrid': bdi.bdi_startstopp()}
    return JsonResponse(andmed)


def container_history_aastad(request):
    # Täisaastate ilmaandmed graafikuna
    chart = dict()
    sel = list(bdi.qs_years)
    categories = []
    sel_temp_averages = []
    sel_temp_ranges = []
    sel_prec_sums = []
    for i in range(len(sel)):
        # X-telje väärtused
        categories.append(f"{sel[i]['timestamp__year']}")
        # Valitud kuu päeva andmed
        # print(i, sel[i])
        sel_temp_averages.append([i, round(float(sel[i]['airtemperature__avg']), 1)])
        sel_temp_ranges.append(
            [
                round(float(sel[i]['airtemperature__min']), 1),
                round(float(sel[i]['airtemperature__max']), 1)
            ]
        )
        if sel[i]['precipitations__sum']:
            sel_prec_sums.append(round(float(sel[i]['precipitations__sum']), 1))
        else:
            sel_prec_sums.append(0)  # Kui mõõtmistulemusi kogu päev polnud

    hist_temp_average = round(sum(data[1] for data in sel_temp_averages) / len(sel_temp_averages), 1)
    chart['aastad'] = f'{min(categories)}-{max(categories)}'
    # Graafiku andmeseeriate kirjeldamine
    series_sel_temp_averages = {
        'name': f'aasta keskmine',
        'regression': True,
        'regressionSettings': {
            'type': 'linear',
            'color': 'rgba(223, 83, 83, .9)'
        },
        'data': sel_temp_averages,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_sel_temp_ranges = {
        'name': f'aasta min/max',
        'data': sel_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_prec_sums = {
        'name': f'aasta sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_prec_sums,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    # Graafiku joonistamine
    chart = {
        'title': {
            'text': f'{chart["aastad"]} Valga linnas'
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
                'plotLines': [{
                    'color': COLORS[0],
                    'width': 2,
                    'dashStyle': 'Dot',
                    'value': hist_temp_average,
                    'zIndex': 5,
                    'label': {
                        'text': f'{chart["aastad"]} keskmine {hist_temp_average}°C',
                        'align': 'right',
                        'x': 0,
                        'y': 20,
                    }
                }]
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temp_averages,
            series_sel_temp_ranges,
            series_sel_prec_sums
        ]
    }
    return JsonResponse(chart)


def container_history_aasta(request):
    # Valitud aasta ilmaandmed graafikuna
    # Kontroll
    chart = dict()
    chart['aasta'] = bdi.aasta
    if bdi.aasta > bdi.stopp.year or bdi.aasta < bdi.start.year:
        chart['tyhi'] = True
        return JsonResponse(chart)
    else:
        chart['tyhi'] = False
    # Andmete ettevalmistamine
    categories = []
    sel_temp_averages = []
    sel_temp_ranges = []
    sel_prec_sums = []
    hist_temp_averages = []
    hist_temp_ranges = []
    sel = list(
        Ilm.objects
        .filter(timestamp__year=bdi.aasta)
        .values('timestamp__month', 'timestamp__day')
        .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations'))
        .order_by('timestamp__month', 'timestamp__day')
    )
    if calendar.isleap(bdi.aasta):
        hist = list(bdi.qs366)
    else: # Jätame 29. veebruari välja
        hist = list(bdi.qs366.exclude(timestamp__day=29, timestamp__month=2))
    offset = 0  # Kui valitud aastas ei ole 366 päeva mõõtmistulemusi, siis arvutatakse vahe
    for i in range(len(hist)):
        # X-telje väärtused
        categories.append(f"{hist[i]['timestamp__day']}.{str(hist[i]['timestamp__month']).zfill(2)}")
        # Ajaloo väärtused
        hist_temp_averages.append(round(float(hist[i]['airtemperature__avg']), 1))
        hist_temp_ranges.append(
            [
                round(float(hist[i]['airtemperature__min']), 1),
                round(float(hist[i]['airtemperature__max']), 1)
            ]
        )
        # Valitud aasta väärtused
        if (
                (sel[offset]['timestamp__month'] == hist[i]['timestamp__month']) and
                (sel[offset]['timestamp__day'] == hist[i]['timestamp__day'])
        ):
            sel_temp_averages.append(round(float(sel[offset]['airtemperature__avg']), 1))
            sel_temp_ranges.append(
                [
                    round(float(sel[offset]['airtemperature__min']), 1),
                    round(float(sel[offset]['airtemperature__max']), 1)
                ]
            )
            if sel[offset]['precipitations__sum']:
                sel_prec_sums.append(round(float(sel[offset]['precipitations__sum']), 1))
            else:
                sel_prec_sums.append(0)  # Kui mõõtmistulemusi kogu päev polnud
            if offset < (len(sel) - 1):
                offset += 1
        else:
            # Valitud kuupäeva andmeid ei ole
            sel_temp_averages.append(None)
            sel_temp_ranges.append(None)
            sel_prec_sums.append(None)

    # Graafiku andmeseeriate kirjeldamine
    series_sel_temp_averages = {
        'name': f'{bdi.aasta} keskmine',
        'data': sel_temp_averages,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_hist_temp_averages = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} keskmine',
        'data': hist_temp_averages,
        'dashStyle': 'ShortDot',
        'zIndex': 1,
        'marker': {
            'lineWidth': 1,
        },
        'color': COLORS[5],
        'negativeColor': '#48AFE8'
    }
    series_hist_temp_ranges = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} min/max',
        'data': hist_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_temp_ranges = {
        'name': f'{bdi.aasta} min/max',
        'data': sel_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_prec_sums = {
        'name': f'{bdi.aasta} sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_prec_sums,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }

    # Graafiku joonistamine
    chart = {
        'title': {
            'text': bdi.aasta
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            # 'type': 'datetime',
            'dateTimeLabelFormats': {
                'day': '%e of %b'
            },
            # 'categories': json.dumps(categories, cls=DjangoJSONEncoder),
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temp_averages,
            series_hist_temp_averages,
            series_hist_temp_ranges,
            series_sel_temp_ranges,
            series_sel_prec_sums
	    ]
    }
    return JsonResponse(chart)


def container_history_kuud(request):
    # Valitud aasta kõigi kuude ilmaandmed graafikuna
    # Kontroll
    chart = dict()
    chart['aasta'] = bdi.aasta
    if bdi.aasta > bdi.stopp.year or bdi.aasta < bdi.start.year:
        chart['tyhi'] = True
        return JsonResponse(chart)
    else:
        chart['tyhi'] = False
    # Andmete ettevalmistamine
    categories = [] # kuud
    sel_temp_averages = [] # valitud aasta kuude keskmised temperatuurid
    sel_temp_ranges = [] # valitud aasta kuude temperatuuride vahemikud
    sel_prec_sums = [] # valitud aasta kuude summaarsed sademed
    hist_temp_averages = [] # ajaloo kuude keskmised sademed
    hist_temp_ranges = [] # ajaloo kuude tempreratuuride vahemikud
    hist_prec_ranges = [] # ajaloo kuude sumaarsete sademete vahemikud
    hist_prec_averages = [] # ajaloo kuude summaarsete sademete keskmised

    # Valitud aasta ilmaandmed
    qs_sel = Ilm.objects \
        .filter(timestamp__year=bdi.aasta) \
        .values('timestamp__month') \
        .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations')) \
        .order_by('timestamp__month')
    sel = dict((el['timestamp__month'], el) for el in qs_sel)

    # Ajaloo ilmaandmed
    qs_hist =  Ilm.objects \
            .values('timestamp__month') \
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature')) \
            .order_by('timestamp__month')
    hist = dict((el['timestamp__month'], el) for el in qs_hist)

    for kuu in range(1, 13):
        # X-telje v22rtused
        categories.append(
            KUUD[kuu]
        )
        # Valitud aasta ilmaandmed kuude kaupa
        kuu_sel_data = sel.get(kuu)
        if kuu_sel_data:
            kuu_airtemperature_avg = round(float(kuu_sel_data['airtemperature__avg']), 1)
            kuu_airtemperature_min = round(float(kuu_sel_data['airtemperature__min']), 1)
            kuu_airtemperature_max = round(float(kuu_sel_data['airtemperature__max']), 1)
            try:
                kuu_precipitations_sum = round(float(kuu_sel_data['precipitations__sum']), 1)
            except:
                kuu_precipitations_sum = None
        else:
            kuu_airtemperature_avg = None
            kuu_airtemperature_min = None
            kuu_airtemperature_max = None
            kuu_precipitations_sum = None

        sel_temp_averages.append(kuu_airtemperature_avg)
        sel_temp_ranges.append(
            [
                kuu_airtemperature_min,
                kuu_airtemperature_max
            ]
        )
        sel_prec_sums.append(kuu_precipitations_sum)

        # Ajaloo ilmaandmed
        kuu_hist_data = hist.get(kuu)
        if kuu_hist_data:
            kuu_airtemperature_avg = round(float(kuu_hist_data['airtemperature__avg']), 1)
            kuu_airtemperature_min = round(float(kuu_hist_data['airtemperature__min']), 1)
            kuu_airtemperature_max = round(float(kuu_hist_data['airtemperature__max']), 1)
        else:
            kuu_airtemperature_avg = None
            kuu_airtemperature_min = None
            kuu_airtemperature_max = None


        hist_temp_averages.append(kuu_airtemperature_avg)
        hist_temp_ranges.append(
            [
                kuu_airtemperature_min,
                kuu_airtemperature_max
            ]
        )

        hist_prec_monthly = bdi.qs_kuud \
            .filter(timestamp__month=kuu) \
            .aggregate(Avg('precipitations__sum'), Min('precipitations__sum'), Max('precipitations__sum'))
        hist_prec_monthly_avg = hist_prec_monthly['precipitations__sum__avg']
        hist_prec_averages.append(
            round(float(hist_prec_monthly_avg), 1)
        )
        hist_prec_monthly_range = [
            round(float(hist_prec_monthly['precipitations__sum__min']), 1),
            round(float(hist_prec_monthly['precipitations__sum__max']), 1)
        ]
        hist_prec_ranges.append(
            hist_prec_monthly_range
        )

    # sel = list(
    #     Ilm.objects
    #         .filter(timestamp__year=bdi.aasta)
    #         .values('timestamp__month')
    #         .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations'))
    #         .order_by('timestamp__month')
    # )
    # hist = list(bdi.qs12)
    # offset = 0  # Kui valitud aastas ei ole 12 kuu mõõtmistulemusi, siis arvutatakse vahe
    # for i in range(len(sel)):
    #     while (
    #             (sel[i]['timestamp__month'] != hist[i + offset]['timestamp__month'])
    #     ):
    #         offset += 1
    #
    #     categories.append(
    #         KUUD[int(sel[i]['timestamp__month'])]
    #     )
    #     sel_temp_averages.append(round(float(sel[i]['airtemperature__avg']), 1))
    #     sel_temp_ranges.append(
    #         [
    #             round(float(sel[i]['airtemperature__min']), 1),
    #             round(float(sel[i]['airtemperature__max']), 1)
    #         ]
    #     )
    #     if sel[i]['precipitations__sum']:
    #         sel_prec_sums.append(round(float(sel[i]['precipitations__sum']), 1))
    #     else:
    #         sel_prec_sums.append(0)  # Kui mõõtmistulemusi kogu kuu polnud
    #     hist_temp_averages.append(round(float(hist[i + offset]['airtemperature__avg']), 1))
    #     hist_temp_ranges.append(
    #         [
    #             round(float(hist[i + offset]['airtemperature__min']), 1),
    #             round(float(hist[i + offset]['airtemperature__max']), 1)
    #         ]
    #     )
    #     hist_prec_monthly = bdi.qs_kuud \
    #         .filter(timestamp__month=i + 1) \
    #         .aggregate(Avg('precipitations__sum'), Min('precipitations__sum'), Max('precipitations__sum'))
    #     hist_prec_monthly_avg = hist_prec_monthly['precipitations__sum__avg']
    #     hist_prec_averages.append(
    #         round(float(hist_prec_monthly_avg), 1)
    #     )
    #     hist_prec_monthly_range = [
    #         round(float(hist_prec_monthly['precipitations__sum__min']), 1),
    #         round(float(hist_prec_monthly['precipitations__sum__max']), 1)
    #     ]
    #     hist_prec_ranges.append(
    #         hist_prec_monthly_range
    #     )

    # Graafiku andmeseeriate kirjeldamine
    series_sel_temp_averages = {
        'name': f'{bdi.aasta} keskmine temperatuur',
        'data': sel_temp_averages,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_hist_temp_averages = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} keskmine temperatuur',
        'data': hist_temp_averages,
        'dashStyle': 'ShortDot',
        'zIndex': 1,
        'marker': {
            'lineWidth': 1,
        }
    }
    series_hist_temp_ranges = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} min/max temperatuurid',
        'data': hist_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_temp_ranges = {
        'name': f'{bdi.aasta} min/max temperatuurid',
        'data': sel_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_prec_sums = {
        'name': f'{bdi.aasta} sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_prec_sums,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    series_hist_prec_ranges = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} min/max sademed',
        'data': hist_prec_ranges,
        'type': 'errorbar',
        'yAxis': 1,
        # 'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    series_hist_prec_averages = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} keskmised sademed',
        'yAxis': 1,
        'data': hist_prec_averages,
        'dashStyle': 'ShortDot',
        'zIndex': 1,
        'marker': {
            'lineWidth': 1,
        },
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    # Graafiku joonistamine
    chart = {
        'title': {
            'text': f'{bdi.aasta} kuude kaupa'
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            # 'type': 'datetime',
            # 'dateTimeLabelFormats': {
            #    'day': '%e of %b'
            # },
            # 'categories': json.dumps(categories, cls=DjangoJSONEncoder),
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temp_averages,
            series_hist_temp_averages,
            series_hist_temp_ranges,
            series_sel_temp_ranges,
            series_sel_prec_sums,
            series_hist_prec_ranges,
            series_hist_prec_averages
        ]
    }

    return JsonResponse(chart)


def container_history_kuu(request):
    # Valitud kuu ilmaandmed graafikuna
    chart = dict()
    chart['aasta'] = bdi.aasta
    chart['kuu'] = bdi.kuu
    # Kontroll
    kontroll = pytz.timezone('utc').localize(datetime(bdi.aasta, bdi.kuu, 1))
    if (
            (kontroll > bdi.stopp) or
            (kontroll < bdi.start.replace(day=1, hour=0))
    ):
        chart['tyhi'] = True
        return JsonResponse(chart)
    else:
        chart['tyhi'] = False
    # Valitud kuu päring
    sel = list(
        Ilm.objects
            .filter(timestamp__year=bdi.aasta, timestamp__month=bdi.kuu)
            .values('timestamp__day')
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations'))
            .order_by('timestamp__day')
    )
    # Ajaloo kuu päring
    if calendar.isleap(bdi.aasta):
        hist = list(bdi.qs366.filter(timestamp__month=bdi.kuu))
    else:
        hist = list(bdi.qs366.exclude(timestamp__day=29, timestamp__month=2).filter(timestamp__month=bdi.kuu))
    # Andmete ettevalmistamine
    categories = []
    sel_temp_averages = []
    sel_temp_ranges = []
    sel_prec_sums = []
    hist_temp_averages = []
    hist_temp_ranges = []
    offset = 0  # Kui valitud kuus ei ole kõigi päevade mõõtmistulemusi, siis arvutatakse vahe
    for i in range(len(hist)):
        # X-telje väärtused
        categories.append(
            f"{hist[i]['timestamp__day']}.{str(bdi.kuu).zfill(2)}"
        )
        # Kogu ajaloo väärtused
        hist_temp_averages.append(round(float(hist[i]['airtemperature__avg']), 1))
        hist_temp_ranges.append(
            [
                round(float(hist[i]['airtemperature__min']), 1),
                round(float(hist[i]['airtemperature__max']), 1)
            ]
        )
        # Valitud kuu väärtused
        if sel[offset]['timestamp__day'] == hist[i]['timestamp__day']:
            # Valitud kuu päeva andmed olemas
            sel_temp_averages.append(round(float(sel[offset]['airtemperature__avg']), 1))
            sel_temp_ranges.append(
                [
                    round(float(sel[offset]['airtemperature__min']), 1),
                    round(float(sel[offset]['airtemperature__max']), 1)
                ]
            )
            if sel[offset]['precipitations__sum']:
                sel_prec_sums.append(round(float(sel[offset]['precipitations__sum']), 1))
            else:
                sel_prec_sums.append(0)  # Kui mõõtmistulemusi kogu päev polnud
            if offset < (len(sel) - 1):
                offset += 1
        else:
            # Valitud kuu päeva andmeid ei ole
            sel_temp_averages.append(None)
            sel_temp_ranges.append(None)
            sel_prec_sums.append(None)
    # Graafiku andmeseeriate kirjeldamine
    series_sel_temp_averages = {
        'name': f'{bdi.aasta} keskmine',
        'data': sel_temp_averages,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_hist_temp_averages = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} keskmine',
        'data': hist_temp_averages,
        'dashStyle': 'ShortDot',
        'zIndex': 1,
        'marker': {
            'lineWidth': 1,
        }
    }
    series_hist_temp_ranges = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} min/max',
        'data': hist_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_temp_ranges = {
        'name': f'{bdi.aasta} min/max',
        'data': sel_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_prec_sums = {
        'name': f'{bdi.aasta} sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_prec_sums,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }

    # Graafiku joonistamine
    chart = {
        'title': {
            'text': f'{KUUD[bdi.kuu]} {bdi.aasta}'
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            # 'type': 'datetime',
            'dateTimeLabelFormats': {
                'day': '%e of %b'
            },
            # 'categories': json.dumps(categories, cls=DjangoJSONEncoder),
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temp_averages,
            series_hist_temp_averages,
            series_hist_temp_ranges,
            series_sel_temp_ranges,
            series_sel_prec_sums
        ]
    }
    return JsonResponse(chart)


def container_history_p2ev(request):
    # Valitud päeva ilmaandmed graafikuna
    chart = dict()
    try:
        # Kontroll
        kontroll = pytz.timezone('utc').localize(datetime(bdi.aasta, bdi.kuu, bdi.p2ev))
    except:
        chart['tyhi'] = True
        return JsonResponse(chart)

    chart['aasta'] = bdi.aasta
    chart['kuu'] = bdi.kuu
    chart['p2ev'] = bdi.p2ev

    if (
            (kontroll > bdi.stopp) or
            (kontroll < bdi.start.replace(hour=0))
    ):
        chart['tyhi'] = True
        return JsonResponse(chart)
    else:
        chart['tyhi'] = False

    # Andmete ettevalmistamine
    categories = []
    sel_temps = []
    sel_precs = []
    hist_temp_averages = []
    hist_temp_ranges = []

    # Valitud päeva ilmaandmed
    qs_sel = Ilm.objects \
        .filter(timestamp__year=bdi.aasta, timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev) \
        .values('timestamp__hour', 'airtemperature', 'precipitations') \
        .order_by('timestamp__hour')
    sel = dict((el['timestamp__hour'], el) for el in qs_sel)

    # Ajaloolised ilmaandmed
    qs_hist = bdi.qs8784.filter(timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev)
    hist = dict((el['timestamp__hour'], el) for el in qs_hist)

    for tund in range(len(hist)):
        # X-telje väärtused
        categories.append(
            f"{str(hist[tund]['timestamp__hour']).zfill(2)}:00"
        )

        # Kogu ajaloo väärtused
        hist_temp_averages.append(round(float(hist[tund]['airtemperature__avg']), 1))
        hist_temp_ranges.append(
            [
                round(float(hist[tund]['airtemperature__min']), 1),
                round(float(hist[tund]['airtemperature__max']), 1)
            ]
        )
        # Valitud kuu päeva väärtused
        tund_sel_data = sel.get(tund)
        try:
            sel_airtemperature = round(float(tund_sel_data['airtemperature']), 1)
        except:
            sel_airtemperature = None
        try:
            sel_precipitations = round(float(tund_sel_data['precipitations']), 1)
        except:
            sel_precipitations = None

        sel_temps.append(sel_airtemperature)
        sel_precs.append(sel_precipitations)

    # sel = list(
    #     Ilm.objects \
    #         .filter(timestamp__year=bdi.aasta, timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev) \
    #         .values('timestamp__hour', 'airtemperature', 'precipitations') \
    #         .order_by('timestamp__hour')
    # )
    # hist = list(bdi.qs8784.filter(timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev))
    #
    # offset = 0  # Kui valitud päevas ei ole kõigi tundide mõõtmistulemusi, siis arvutatakse vahe
    # for i in range(len(hist)):
    #     # X-telje väärtused
    #     categories.append(
    #         f"{str(hist[i]['timestamp__hour']).zfill(2)}:00"
    #     )
    #     # Kogu ajaloo väärtused
    #     hist_temp_averages.append(round(float(hist[i]['airtemperature__avg']), 1))
    #     hist_temp_ranges.append(
    #         [
    #             round(float(hist[i]['airtemperature__min']), 1),
    #             round(float(hist[i]['airtemperature__max']), 1)
    #         ]
    #     )
    #     # Valitud kuu väärtused
    #
    #     if sel[offset]['timestamp__hour'] == hist[i]['timestamp__hour']:
    #         # Valitud kuu päeva andmed olemas
    #         sel_temps.append(round(float_or_none(sel[offset]['airtemperature']), 1))
    #         if sel[offset]['precipitations']:
    #             sel_precs.append(round(float(sel[offset]['precipitations']), 1))
    #         else:
    #             sel_precs.append(0)  # Kui mõõtmistulemusi kogu päev polnud
    #         if offset < (len(sel) - 1):
    #             offset += 1
    #     else:
    #         # Valitud kuu päeva andmeid ei ole
    #         sel_temps.append(None)
    #         sel_precs.append(None)

    # Graafiku andmeseeriate kirjeldamine
    series_sel_temps = {
        'name': f'{KUUD[bdi.kuu]} {bdi.aasta}',
        'data': sel_temps,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_hist_temp_averages = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} keskmine',
        'data': hist_temp_averages,
        'dashStyle': 'ShortDot',
        'zIndex': 1,
        'marker': {
            'lineWidth': 1,
        }
    }
    series_hist_temp_ranges = {
        'name': f'{bdi.start.year} - {bdi.stopp.year} min/max',
        'data': hist_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_precs = {
        'name': f'{KUUD[bdi.kuu]} {bdi.aasta} sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_precs,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    # Graafiku joonistamine
    chart = {
        'title': {
            'text': f'{bdi.p2ev}. {KUUD[bdi.kuu]} {bdi.aasta}'
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            # 'type': 'datetime',
            'dateTimeLabelFormats': {
                'day': '%e of %b'
            },
            # 'categories': json.dumps(categories, cls=DjangoJSONEncoder),
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temps,
            series_hist_temp_averages,
            series_hist_temp_ranges,
            series_sel_precs
        ]
    }

    return JsonResponse(chart)

def container_history_p2evad(request):
    # Valitud päeva ja kuu ilmaandmed graafikuna läbi aastate
    chart = dict()
    try:
        # Kontroll
        kontroll = pytz.timezone('utc').localize(datetime(bdi.aasta, bdi.kuu, bdi.p2ev))
    except:
        chart['tyhi'] = True
        return JsonResponse(chart)
    chart['aasta'] = bdi.aasta
    chart['kuu'] = bdi.kuu
    chart['p2ev'] = bdi.p2ev
    if (
            (kontroll > bdi.stopp) or
            (kontroll < bdi.start.replace(hour=0))
    ):
        chart['tyhi'] = True
        return JsonResponse(chart)
    else:
        chart['tyhi'] = False
    sel = list(Ilm.objects
               .filter(timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev)
               .values('timestamp__year')
               .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations'))
               .order_by('timestamp__year')
    )
    hist  = list(Ilm.objects \
        .filter(timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev) \
        # .order_by('timestamp') \
        .aggregate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature')) \
        .values()
    )
    categories = []
    sel_temp_averages = []
    sel_temp_ranges = []
    sel_prec_sums = []
    hist_temp_average = round(float(hist[0]), 1)
    hist_temp_min = round(float(hist[1]), 1)
    hist_temp_max = round(float(hist[2]), 1)
    for i in range(len(sel)):
        # X-telje väärtused
        categories.append(f"{sel[i]['timestamp__year']}")
        # Valitud kuu päeva andmed
        sel_temp_averages.append(round(float(sel[i]['airtemperature__avg']), 1))
        sel_temp_ranges.append(
            [
                round(float(sel[i]['airtemperature__min']), 1),
                round(float(sel[i]['airtemperature__max']), 1)
            ]
        )
        if sel[i]['precipitations__sum']:
            sel_prec_sums.append(round(float(sel[i]['precipitations__sum']), 1))
        else:
            sel_prec_sums.append(0)  # Kui mõõtmistulemusi kogu päev polnud
    # Graafiku andmeseeriate kirjeldamine
    series_sel_temp_averages = {
        'name': f'päeva keskmine',
        'data': sel_temp_averages,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_sel_temp_ranges = {
        'name': f'päeva min/max',
        'data': sel_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_prec_sums = {
        'name': f'päeva sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_prec_sums,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    # Graafiku joonistamine
    chart = {
        'title': {
            'text': f'{bdi.p2ev}. {KUUD[bdi.kuu]} Valga linnas läbi aastate'
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            # 'type': 'datetime',
            # 'dateTimeLabelFormats': {
            #     'day': '%e of %b'
            # },
            # 'categories': json.dumps(categories, cls=DjangoJSONEncoder),
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
                'plotLines': [{
                    'color': COLORS[0],
                    'width': 2,
                    'dashStyle': 'Dot',
                    'value': hist_temp_average,
                    'zIndex': 5,
                    'label': {
                        'text': f'{bdi.start.year}-{bdi.stopp.year} keskmine {hist_temp_average}°C',
                        'align': 'right',
                        'x': 0,
                        'y': 20,
                    }
                }]
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temp_averages,
            series_sel_temp_ranges,
            series_sel_prec_sums
        ]
    }
    return JsonResponse(chart)

def container_history_kuud_aastatekaupa(request):
    # Valitud kuu ilmaandmed graafikuna läbi aastate
    chart = dict()
    chart['aasta'] = bdi.aasta
    chart['kuu'] = bdi.kuu
    chart['tyhi'] = False

    try:
        # Kontroll
        kontroll = pytz.timezone('utc').localize(datetime(bdi.aasta, bdi.kuu, 1))
    except:
        chart['tyhi'] = True
        return JsonResponse(chart)

    sel = list(Ilm.objects
               .filter(timestamp__month=bdi.kuu)
               .values('timestamp__year')
               .annotate(
                   Avg('airtemperature'), 
                   Min('airtemperature'), 
                   Max('airtemperature'), 
                   Sum('precipitations'),
                )
               .order_by('timestamp__year')
    )
    hist  = list(Ilm.objects
        .filter(timestamp__month=bdi.kuu)
        .aggregate(
            Avg('airtemperature'), 
            Min('airtemperature'), 
            Max('airtemperature')
        )
        .values()
    )
    hist_precipitationdays_counts_qs = (
        Ilm.objects
        .filter(
            precipitations__gt=0,
            timestamp__month=bdi.kuu
        )
        .values('timestamp__year')
        .annotate(
            days_with_precipitation=Count('timestamp__day', distinct=True)
        )
        .order_by('timestamp__year')
    )
    hist_precipitationdays_counts = {
        row['timestamp__year']: row['days_with_precipitation']
        for row
        in hist_precipitationdays_counts_qs
    }

    categories = []
    sel_temp_averages = []
    sel_temp_ranges = []
    sel_prec_sums = []
    sel_prec_days_counts = []
    hist_temp_average = round(float(hist[0]), 1)
    hist_temp_min = round(float(hist[1]), 1)
    hist_temp_max = round(float(hist[2]), 1)
    for i in range(len(sel)):
        # X-telje väärtused
        categories.append(f"{sel[i]['timestamp__year']}")
        # Valitud kuu päeva andmed
        sel_temp_averages.append(round(float(sel[i]['airtemperature__avg']), 1))
        sel_temp_ranges.append(
            [
                round(float(sel[i]['airtemperature__min']), 1),
                round(float(sel[i]['airtemperature__max']), 1)
            ]
        )
        if sel[i]['precipitations__sum']:
            sel_prec_sums.append(round(float(sel[i]['precipitations__sum']), 1))
        else:
            sel_prec_sums.append(0)  # Kui mõõtmistulemusi kogu kuu polnud
        sel_prec_days_counts.append(
            hist_precipitationdays_counts.get(sel[i]['timestamp__year'], 0)
        )
    
    # Graafiku andmeseeriate kirjeldamine
    series_sel_temp_averages = {
        'name': f'kuu keskmine',
        'data': sel_temp_averages,
        'zIndex': 2,
        'marker': {
            'lineWidth': 2,
        },
        'color': '#FF3333',
        'negativeColor': '#48AFE8'
    }
    series_sel_temp_ranges = {
        'name': f'kuu min/max',
        'data': sel_temp_ranges,
        'type': 'arearange',
        'lineWidth': 0,
        'linkedTo': ':previous',
        'color': COLORS[0],
        'fillOpacity': 0.3,
        'zIndex': 0,
        'marker': {
            'enabled': False
        }
    }
    series_sel_prec_sums = {
        'name': f'kuu sademed',
        'type': 'column',
        'yAxis': 1,
        'data': sel_prec_sums,
        'color': COLORS[0],
        'tooltip': {
            'valueSuffix': ' mm'
        }
    }
    series_sel_prec_days_counts = {
        'name': f'kuus sajupäevi',
        'type': 'spline',
        'yAxis': 1,
        'data': sel_prec_days_counts,
        # 'color': COLORS[0],
        'lineWidth': 0,
        'marker': {
            'radius': 6
        },
        'tooltip': {
            'valueSuffix': ' p'
        }
    }
    # Graafiku joonistamine
    chart = {
        'title': {
            'text': f'{KUUD[bdi.kuu]} Valga linnas läbi aastate'
        },

        'subtitle': {
            'text': 'Allikas: <a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>',
            'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            'y': 25
        },

        'xAxis': {
            # 'type': 'datetime',
            # 'dateTimeLabelFormats': {
            #     'day': '%e of %b'
            # },
            # 'categories': json.dumps(categories, cls=DjangoJSONEncoder),
            'categories': categories,
            # 'labels': {
            #     'format': '{value:%e. %b}'
            # }
        },

        'yAxis': [
            {
                'title': {
                    'text': 'Temperatuur'
                },
                'labels': {
                    'format': '{value}°C'
                },
                'plotLines': [{
                    'color': COLORS[0],
                    'width': 2,
                    'dashStyle': 'Dot',
                    'value': hist_temp_average,
                    'zIndex': 5,
                    'label': {
                        'text': f'{bdi.start.year}-{bdi.stopp.year} keskmine {hist_temp_average}°C',
                        'align': 'right',
                        'x': 0,
                        'y': 20,
                    }
                }]
            }, {
                'title': {
                    'text': 'Sademed'
                },
                'labels': {
                    'format': '{value} mm'
                },
                'opposite': True
            }
        ],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'valueSuffix': '°C'
        },

        'legend': {
        },

        'series': [
            series_sel_temp_averages,
            series_sel_temp_ranges,
            series_sel_prec_sums,
            series_sel_prec_days_counts
        ]
    }
    return JsonResponse(chart)

# def yrno_48h():
#     # Weather forecast from Yr, delivered by the Norwegian Meteorological Institute and the NRK
#     href = 'http://www.yr.no/place/Estonia/Valgamaa/Valga/forecast_hour_by_hour.xml'
#     # tree = etree.parse(href)
#     # root = tree.getroot()
#     r = requests.get(href)
#     root = ET.fromstring(r.text)
#     yr = {}
#     tag_timezone = root.find("location").find("timezone") # Otsime XML puu asukoha andmetega
#     utcoffsetMinutes = int(tag_timezone.attrib['utcoffsetMinutes'])
#     tag_meta = root.find("meta") # Otsime XML puu metaandmetega
#     yr['meta'] = {}
#     yr['meta']['lastupdate'] = datetime.strptime(tag_meta.find("lastupdate").text, '%Y-%m-%dT%H:%M:%S')
#     yr['meta']['nextupdate'] = datetime.strptime(tag_meta.find("nextupdate").text, '%Y-%m-%dT%H:%M:%S')
#     # yr['forecast'] = {}
#     cat = []
#     dt = []
#     prec = []
#     wind = []
#     temp = []
#     pres = []
#     symb = []
#     dateticks = [0] # Graafikul kuupäevatikkerite jaoks
#     tag_forecast = root.find("forecast").find("tabular") # Otsime XML puu prognoosi tabeliga
#     for n in range(len(tag_forecast)):
#         data = tag_forecast[n]
#         date = pytz.timezone('Europe/Tallinn').localize(datetime.strptime(data.attrib['from'], '%Y-%m-%dT%H:%M:%S'))
#         dt.append(datetime.timestamp(date))
#         if date.hour == 0:
#             dateticks.append(n)
#         cat.append(date) # Aeg
#         # Sademed
#         prec_value = float(data.find("precipitation").attrib['value'])
#         try:
#             prec_maxvalue = float(data.find("precipitation").attrib['maxvalue'])
#             prec_minvalue = float(data.find("precipitation").attrib['minvalue'])
#         except:
#             prec_minvalue = prec_maxvalue = prec_value
#
#         prec.append([prec_value, prec_minvalue, prec_maxvalue]) # Sademed
#         wind.append(
#             [float(data.find("windSpeed").attrib['mps']),
#             float(data.find("windDirection").attrib['deg'])]
#         )
#         temp.append(float(data.find("temperature").attrib['value'])) # Temperatuur
#         pres.append(float(data.find("pressure").attrib['value'])) # Õhurõhk
#         symb.append(data.find("symbol").attrib['var']) # Ilmasümboli kood (YR)
#     yr['forecast'] = {
#         'start': cat[0], # Mis kellast prognoos algab
#         'temperatures': temp,
#         'windbarbs': wind,
#         'airpressures': pres,
#         'precipitations': prec,
#         'symbols': symb,
#         'dt': dt,
#     }
#     return yr

# kasutusest v2ljas alates juuni 2024 TODO: cleanup
# def owm_onecall():
#     api_key = settings.OWM_APIKEY
#     city_id = 587876  # Valga
#     lon = '26.05'
#     lat = '57.78'
#     owm_url = 'https://api.openweathermap.org/data/2.5/'
#
#     # Hetkeandmed ja prognoos
#     params = {
#         'lat': lat,
#         'lon': lon,
#         'appid': api_key,
#         'units': 'metric',
#     }
#     resp = requests.get(
#         owm_url + 'onecall',
#         # headers=headers,
#         params=params
#     )
#     weather = json.loads(resp.text)
#
#     # Ajalugu
#     now = datetime.now()
#     dt = int(datetime.timestamp(datetime(now.year, now.month, now.day, now.hour)))
#     params['dt'] = dt
#     resp = requests.get(
#         owm_url + 'onecall/timemachine',
#         # headers=headers,
#         params=params
#     )
#     weather['history'] = json.loads(resp.text)
#
#     if weather:
#         # weather['current']['datetime'] = datetime.fromtimestamp(weather['current']['dt'], timezone.utc)
#         weather['current']['kirjeldus'] = OWM_CODES.get(
#             str(weather['current']['weather'][0]['id']),
#             weather['current']['weather'][0]['description']
#         )
#         for hour in weather['hourly']:
#             # hour['datetime'] = datetime.fromtimestamp(hour['dt'], timezone.utc)
#             hour['kirjeldus'] = OWM_CODES.get(
#                 str(hour['weather'][0]['id']),
#                 hour['weather'][0]['description']
#             )
#         for day in weather['daily']:
#             # day['datetime'] = datetime.fromtimestamp(day['dt'], timezone.utc)
#             day['kirjeldus'] = OWM_CODES.get(
#                 str(day['weather'][0]['id']),
#                 day['weather'][0]['description']
#             )
#         weather['history']['hourly3h'] = weather['history']['hourly'][-3:]  # viimased kolm tundi
#         for hour in weather['history']['hourly']:
#             # hour['datetime'] = datetime.fromtimestamp(hour['dt'], timezone.utc)
#             hour['kirjeldus'] = OWM_CODES.get(
#                 str(hour['weather'][0]['id']),
#                 hour['weather'][0]['description']
#             )
#     return weather

def mitutundi(algus, l6pp):
    # Tagastab kahe kuupäeva vahe tundides
    # print(algus, l6pp)
    return (l6pp-algus).days * 24 + (l6pp-algus).seconds/3600

    
def nighttime2(algus, l6pp):
    '''
    Ilmaprogonoosile lisame hämara ja pimeda aja varjutuse
    Sisendiks graafiku vaadeldava perioodi algus ja lõpp
    Tagastatakse list varjutuse perioodidega kujul
    [{'from':, (tundi algusest), 'to': (tundi algusest), 'color':(hämar või pime)}]
    '''
    jada = list()
    pime = '#aaaaaa'
    h2mar = '#dddddd'
    
    d = algus
    while d <= l6pp + timedelta(days=1): # Kõigi prognoosis esinevate kuupäevade päikeseandmed
        sun = IlmateenistusValga.sun_moon(d)['sun']
        jada.append({
            'from': d.replace(hour=0),
            'to': sun['dawn'],
            'color': pime}
        )
        jada.append({
            'from': sun['dawn'],
            'to': sun['sunrise'],
            'color': h2mar}
        )
        jada.append({
            'from': sun['sunset'],
            'to': sun['dusk'],
            'color': h2mar}
        )
        jada.append({
            'from': sun['dusk'],
            'to': d.replace(hour=23, minute=59, second=59, microsecond=999999),
            'color': pime}
        )
        d += timedelta(days=1)

    plotBands = list()
    # Sordime välja perioodi mitte jäävad pimedaajad
    for i in range(len(jada)):
        if jada[i]['to'] >= algus and jada[i]['from'] <= l6pp:
            if jada[i]['from'] < algus and jada[i]['to'] > algus:
                jada[i]['from'] = algus
            if jada[i]['from'] < l6pp and jada[i]['to'] > l6pp:
                jada[i]['to'] = l6pp
            # Teisendame aja tundideks graafiku nullpunktist
            jada[i]['from'] = mitutundi(algus, jada[i]['from'])
            jada[i]['to'] = mitutundi(algus, jada[i]['to'])
            plotBands.append(jada[i])
    return plotBands

def get_mixed_ilmateade(request):
    '''
    Koondab andmed ja koostab graafiku, mis näitab:
    - 24h mõõdetud ilmaandmeid ilmateenistus.ee veebist
    - Viimaseid mõõdetud ilmaandmeid ilmateenistus.ee veebist
    - 48 ilmaprognoosi yr.no veebist
    - pimeda ja valge aja vaheldumist
    Kutsutakse välja ajax funktsiooniga
    '''
    # Kasutame ainult ajavööndiga ajainfot
    d = pytz.timezone('Europe/Tallinn').localize(datetime.now())
    # Erinevus UTC ja kohaliku ajavööndi vahel (sekundites)
    utcoffset = d.utcoffset().seconds
    # x-telg 72 tundi: d -24h, d +48h
    c = pd.date_range(
        (d - timedelta(hours=23)).replace(minute=0, second=0, microsecond=0),
        periods=72,
        freq='h'
    )
    # Ilmaandmete hankimine
    andmed_eelnevad24h = bdi.viimase24h_andmed(
        'Valga',
        d.replace(minute=0, second=0, microsecond=0)
    )

    yAPI = utils.YrnoAPI()
    andmed_j2rgnevad48h_yrno = yAPI.yrno_forecasts

    andmed_j2rgnevad48h_ilmateenistus_data = utils.ilmateenistus_forecast()
    if andmed_j2rgnevad48h_ilmateenistus_data:
        andmed_j2rgnevad48h_ilmateenistus = andmed_j2rgnevad48h_ilmateenistus_data['forecast']
        andmed_j2rgnevad48h_ilmateenistus_temperatures = [
            float_or_none(andmed_j2rgnevad48h_ilmateenistus[hour]['temperature'])
            for hour
            in andmed_j2rgnevad48h_ilmateenistus
        ][:48]
        andmed_j2rgnevad48h_ilmateenistus_pressures = [
            float_or_none(andmed_j2rgnevad48h_ilmateenistus[hour]['pressure'])
            for hour
            in andmed_j2rgnevad48h_ilmateenistus
        ][:48]
        andmed_j2rgnevad48h_ilmateenistus_phenomen = [
            andmed_j2rgnevad48h_ilmateenistus[hour]['phenomen']['className']
            for hour
            in andmed_j2rgnevad48h_ilmateenistus
        ][:48]
    else:
        andmed_j2rgnevad48h_ilmateenistus_temperatures = [None] * 48
        andmed_j2rgnevad48h_ilmateenistus_pressures = [None] * 48
        andmed_j2rgnevad48h_ilmateenistus_phenomen = [None] * 48

    # Pimeda aja varjutused
    andmed_nighttime = nighttime2(c[0], c[-1])

    # Hetkeaja joon
    andmed_nyyd = mitutundi(c[0], d)

    # Kuupäeva teisendused highchart formaati (epoch time)
    graafik_categories = list((el + timedelta(seconds=el.utcoffset().seconds)).timestamp()*1000 for el in c)
    graafik_nullpunkt = graafik_categories[0]
    graafik_00hours = list(
        ((el + timedelta(seconds=c[0].utcoffset().seconds)).timestamp() * 1000 - graafik_nullpunkt) / (60 * 60 * 1000)
        for el in c if el.hour == 0
    )

    # Kuu ja p2ikese seisud
    sun_str = ephem_data.get_sun_str(d)
    moon_str = ephem_data.get_moon_str(d)

    # Graafiku pealkirjad
    ilmastring_now = andmed_eelnevad24h['ilmastring']
    ilmastring_fore = andmed_j2rgnevad48h_yrno['meta']['lastupdate'].strftime("%d.%m.%Y %H:%M")
    graafik_title = f'Mõõtmised: {ilmastring_now}; Prognoos (yr.no): {ilmastring_fore}<br>{sun_str} {moon_str}'
    
    graafik_subtitle = (
        'Allikad: ' +
        'mõõtmised: ' +
        '<a href="https://www.ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/tunniandmed/" target="_blank">ilmateenistus.ee</a>' + '; ' 
        'prognoos:' + 
        # '<a href="https://www.yr.no/place/Estonia/Valgamaa/Valga/hour_by_hour.html" target="_blank">yr.no</a>:'
        '<a href="https://www.yr.no/en/forecast/daily-table/2-587876/Estonia/Valgamaa/Valga%20vald/Valga" target="_blank">yr.no</a>' +
        ', <a href="https://www.ilmateenistus.ee/ilm/prognoosid/asukoha-prognoos/?coordinates=57.776678;26.030958" target="_blank">ilmateenistus.ee</a>' + '; '
    )

    # Graafiku kujundamine
    chart = {
        'title': {
            'useHTML': True,
            'text': graafik_title,
            'align': 'left',
            'style': {"fontSize": "12px"},
            'x': 30,
            'y': 20
        },
	
	    'subtitle': {
            'text': graafik_subtitle,
            # 'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            # 'y': 40
        },
        # 'data': {
        #     'columnsURL': '/api/i/forecasts/',
        #     'enablePolling': True,
        #     'name': 'Ilmaandmed - Ilmaennustus 48h'
        # },
        'plotOptions': {
            'series': {
                'pointPadding': 0,
                'groupPadding': 0,
                'borderWidth': 0,
                'shadow': False,
            },
            'windbarb': {
                'lineWidth': 1,
                'vectorLength': 15,
                'tooltip': {
                    'valueSuffix': ' m/s'
                }
            },
            'column': {
                'stacking': 'normal',
            }
        },
        'xAxis': [
            {
                'tickInterval': 2, # kaks tundi
                'minorTickInterval': 1, # üks tund
                'tickLength': 10,
                'gridLineWidth': 1,
                'gridLineColor': '#F0F0F0',
                'startOnTick': False,
                'endOnTick': False,
                'minPadding': 0,
                'maxPadding': 0,
                'offset': 30,
                'showLastLabel': True,
                'categories': graafik_categories,
                'plotBands': andmed_nighttime,
                'plotLines': [{
                    'value': andmed_nyyd,
                    'label': {
                        'text': d.strftime("%H:%M"),
                        'style': {
                            'color': 'gray',
                            "fontSize": "10px"
                        }
                    },
                    'color': 'gray',
                    'dashStyle': 'Dot',
                    'width': 2,
                    'zIndex': 3
                }],
                'labels': {
                    'format': '{value:%H}'
                },
                'crosshair': True
	        }, {
                'linkedTo': 0,
                'alignTicks': False,
                # 'type': 'datetime',
                'categories': graafik_categories,
                'tickPositions': graafik_00hours,
                'labels': {
                    'format': '{value:%d.%m}',
                    'align': 'left',
                    'x': 3,
                    'y': 0
                },
                'opposite': True,
                'tickLength': 20,
                'gridLineWidth': 4
            }
        ],
	
        'yAxis': [
            { # temperature axis
                'title': {
                    'text': '°C'
                },
                'labels': {
                    'format': '{value}°',
                    'style': {
                        'fontSize': '10px'
                    },
                    'x': -3
                },
                'plotLines': [{ # zero plane
                    'value': 0,
                    'color': '#BBBBBB',
                    'width': 1,
                    'zIndex': 2
                }],
                'maxPadding': 0.3,
                'minRange': 8,
                'tickInterval': 2,  # kaks tundi
                'minorTickInterval': 2,  # üks tund
                'gridLineColor': '#F0F0F0'

            }, { # precipitation axis
                'title': {
                    'text': ''
                },
                'labels': {
                    'enabled': False
                },
                'gridLineWidth': 0,
                'tickLength': 0,
                'minRange': 10,
                'min': 0

            }, { # Air pressure
                'allowDecimals': False,
                'title': { # Title on top of axis
                    'text': 'hPa',
                    'offset': 0,
                    'align': 'high',
                    'rotation': 0,
                    'style': {
                        'fontSize': '10px',
                        'color': '#90ed7d'
                    },
                    'textAlign': 'left',
                    'x': 3
                },
                'labels': {
                    'style': {
                        'fontSize': '8px',
                        'color': '#90ed7d'
                    },
                    'y': 2,
                    'x': 3
                },
                'gridLineWidth': 0,
                'opposite': True,
                'showLastLabel': False
        }],

        'tooltip': {
            'crosshairs': True,
            'shared': True,
            'headerFormat': '{point.key:%d.%m %H:%M}<br>',
        },

	    'series': [{
            'id': 'empty_72h',
            'name': '',
            'data': ['null'] * 72, # Joonistame tühja graafiku 72 tunniks
            'showInLegend': False
        }, {
            'id': 'andmed_eelnevad24h_airtemperatures',
            'name': 'Temperatuur (mõõdetud)', # Ajalooliselt mõõdetud
            'data': andmed_eelnevad24h['airtemperatures'],
            'type': 'spline',
            'marker': {
                'enabled': False,
                'states': {
                    'hover': {
                        'enabled': True
                    }
                }
            },
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
	    }, {
            'id': 'andmed_j2rgnevad48h_yrno_temperatures',
            'name': 'Temperatuur (yr.no prognoos)', # Prognoos
            'data': 24 * [None] + andmed_j2rgnevad48h_yrno['series']['temperatures'],
            'type': 'spline',
            'marker': {
                'enabled': False,
                'states': {
                    'hover': {
                        'enabled': True
                    }
                }
            },
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'dashStyle': 'shortdot',
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
	    }, {
            'id': 'andmed_j2rgnevad48h_ilmateenistus_temperatures',
            'name': 'Temperatuur (ilmateenistus.ee prognoos)', # Ilmateenistuse prognoos
            'data': 24 * [None] + andmed_j2rgnevad48h_ilmateenistus_temperatures,
            'type': 'spline',
            'marker': {
                'enabled': False,
                'states': {
                    'hover': {
                        'enabled': True
                    }
                }
            },
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'dashStyle': 'dash',
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
	    }, {
            'id': 'andmed_eelnevad24h_precipitations',
            'name': 'Sademed (mõõdetud)',
            'data': andmed_eelnevad24h['precipitations'],
            'type': 'column',
            'color': '#68CFE8',
            'yAxis': 1,
            'groupPadding': 0,
            'pointPadding': 0,
            'grouping': False,
            'dataLabels': {
                'enabled': True,
                'style': {
                    'fontSize': '8px',
                    # 'color': 'gray'
                }
            },
            'lineWidth' : 2, 
            'tooltip': {
                'valueSuffix': ' mm'
            },
            'showInLegend': False
	    }, {
            'id': 'andmed_j2rgnevad48h_precipitations_max',
            'name': 'Sademed (yr.no prognoos max)',
            'type': 'column',
            # 'plotOptions': {
            #     'column': {
            #         'stacking': 'normal',
            #     }
            # },
            'dataLabels': {
                'enabled': True,
                'style': {
                    'fontSize': '8px',
                    # 'color': 'gray'
                }
            },
            'data': 24 * [None] + [round(el[2]-el[1], 1) for el in andmed_j2rgnevad48h_yrno['series']['precipitations']], # err prec
            'color': {
                'pattern': {
                    'path': {
                        'd': 'M 0 0 L 5 5 M 4.5 -0.5 L 5.5 0.5 M -0.5 4.5 L 0.5 5.5',
                    },
                    'width': 5,
                    'height': 5,
                    'color': '#68CFE8',
                }
            },
            'yAxis': 1,
            'groupPadding': 0,
            'pointPadding': 0,
            'grouping': False,
            'lineWidth' : 2,
            'tooltip': {
                'valueSuffix': ' mm'
            },
            'showInLegend': False
	    }, {
            'id': 'andmed_j2rgnevad48h_precipitations',
            'name': 'Sademed (yr.no prognoos min)',
            'type': 'column',
            # 'plotOptions': {
            #     'column': {
            #         'stacking': 'normal',
            #     }
            # },
            'dataLabels': {
                'enabled': False,
                # 'style': {
                #     'fontSize': '8px',
                #     'color': 'gray'
                # }
            },
            'data': 24 * [None] + [el[1] for el in andmed_j2rgnevad48h_yrno['series']['precipitations']], # min prec
            'color': '#68CFE8',
            'yAxis': 1,
            'groupPadding': 0,
            'pointPadding': 0,
            'grouping': False,
            'lineWidth' : 2,
            'tooltip': {
                'valueSuffix': ' mm'
            },
            'showInLegend': False
	    }, {
            'id': 'andmed_eelnevad24h_airpressures',
            'name': 'Õhurõhk (mõõdetud)',
            'data': andmed_eelnevad24h['airpressures'],
            'color': '#90ed7d',
            'type': 'spline',
            'marker': {
                'enabled': False
            },
            'zIndex': 2,
            'shadow': False,
            'tooltip': {
                'valueSuffix': ' hPa'
            },
            'lineWidth' : 2, 
            'dashStyle': 'solid',
            'yAxis': 2
	    }, {
            'id': 'andmed_j2rgnevad48h_yrno_airpressures',
            'name': 'Õhurõhk (yr.no prognoos)',
            'data': 24 * [None] + andmed_j2rgnevad48h_yrno['series']['airpressures'],
            'color': '#90ed7d',
            'type': 'spline',
            'marker': {
                'enabled': False
            },
            'zIndex': 2,
            'shadow': False,
            'tooltip': {
                'valueSuffix': ' hPa'
            },
            'lineWidth' : 2, 
            'dashStyle': 'shortdot',
            'yAxis': 2
	    }, {
            'id': 'andmed_j2rgnevad48h_ilmateenistus_airpressures',
            'name': 'Õhurõhk (ilmateenistus.ee prognoos)',
            'data': 24 * [None] + andmed_j2rgnevad48h_ilmateenistus_pressures,
            'color': '#90ed7d',
            'type': 'spline',
            'marker': {
                'enabled': False
            },
            'zIndex': 2,
            'shadow': False,
            'tooltip': {
                'valueSuffix': ' hPa'
            },
            'lineWidth' : 2,
            'dashStyle': 'dash',
            'yAxis': 2
	    }, {
            'id': 'andmed_eelnevad24h_windbarbs',
            'name': 'Tuul (mõõdetud)',
            'data': andmed_eelnevad24h['windbarbs'],
            'type': 'windbarb',
            'showInLegend': False
	    }, {
            'id': 'andmed_j2rgnevad48h_windbarbs',
            'name': 'Tuul (yr.no prognoos)',
            'data': 24 * [None] + andmed_j2rgnevad48h_yrno['series']['windbarbs'],
            'type': 'windbarb',
            'color': 'gray',
            'showInLegend': False
	    }]
    }

    chart['yrno_symbols'] = andmed_eelnevad24h['symbols'] + andmed_j2rgnevad48h_yrno['series']['symbols']
    chart['ilmateenistus_symbols'] = andmed_eelnevad24h['symbols'] + andmed_j2rgnevad48h_ilmateenistus_phenomen

    # Hetketemperatuur
    chart['airtemperatures'] = andmed_eelnevad24h['airtemperatures']

    if settings.TMP_ALGUSKUVA_CACHE and isinstance(request.user, AnonymousUser):
        if settings.REDIS_INUSE: # salvestame redisesse
            redis_client.set(
                'ilmateenistus_mixed_ilmateade_chart',
                json.dumps(chart),
                ex=5 * 60
            )
        else: # salvestame faili
            with open(TMP_ALGUSKUVA, 'w', encoding='utf-8') as f:
                json.dump(chart, f)
    return chart

def mixed_ilmateade(request):
    if settings.TMP_ALGUSKUVA_CACHE and isinstance(request.user, AnonymousUser):
        if settings.REDIS_INUSE and redis_client.exists('ilmateenistus_mixed_ilmateade_chart'):
            chart_jsondumps = redis_client.get('ilmateenistus_mixed_ilmateade_chart')
            chart = json.loads(chart_jsondumps)
            return JsonResponse(chart)

    chart = get_mixed_ilmateade(request)
    return JsonResponse(chart)

# veebiversioon
def forecasts(request):
    forecast = utils.get_forecasts()
    context = {
        'forecast': forecast
    }
    return render(request, 'ilm/forecasts.html', context)

# API versioon
def forecasts_api(request):
    forecast = utils.get_forecasts()
    return JsonResponse(forecast)

from ilm.utils import forecast_log_analyze
def forecasts_quality(request):
    path = settings.BASE_DIR
    context = {
        'data': forecast_log_analyze.main(path)
    }
    return render(request, 'ilm/forecasts_quality.html', context)

# Ajaloo ilmanäitajate ekstreemumid, keskmised ja varieerumine
def maxmin(request):
    # Agregeeritud näitajad kuupäevade kaupa
    days_maxmin_qs = Ilm.objects \
        .values('timestamp__year', 'timestamp__month', 'timestamp__day') \
        .annotate(Max('airtemperature_max'), Min('airtemperature_min'), Avg('airtemperature'), Sum('precipitations')) \
        .order_by('timestamp__year', 'timestamp__month', 'timestamp__day')

    # Agregeeritud näitajad aasta päevade kaupa
    days_airtemp_avgs_qs = Ilm.objects \
        .values('timestamp__month', 'timestamp__day') \
        .annotate(Avg('airtemperature')) \
        .order_by('timestamp__month', 'timestamp__day')
    days_airtemp_avgs = dict()

    avg_min = (datetime.now(), 20)
    avg_max = (datetime.now(), -20)
    for day in days_maxmin_qs:
        if day['airtemperature__avg'] > avg_max[1]:
            avg_max = (
                datetime(day['timestamp__year'], day['timestamp__month'], day['timestamp__day']),
                day['airtemperature__avg']
            )
        if day['airtemperature__avg'] < avg_min[1]:
            avg_min = (
                datetime(day['timestamp__year'], day['timestamp__month'], day['timestamp__day']),
                day['airtemperature__avg']
            )
    # print(
    #     'kuum p2ev', avg_max,
    #     'kylm p2ev', avg_min
    # )

    for day in days_airtemp_avgs_qs:
        day_tuple = (day['timestamp__month'], day['timestamp__day'])
        days_airtemp_avgs[day_tuple] = day['airtemperature__avg']

    years_top = dict()
    # Agregeeritud näitajad aastate kaupa
    from django.db.models import F, OuterRef, Subquery, IntegerField

    years_maxmin_qs = Ilm.objects\
        .values('timestamp__year')\
        .annotate(
            Max('airtemperature_max'),
            Min('airtemperature_min'),
            Avg('airtemperature'),
            Sum('precipitations'))\
        .order_by('timestamp__year')

    # hours_rolling = Ilm.objects.annotate(
    #     rolling_min=Window(
    #         expression=Min('airtemperature_min'),
    #         order_by=F('timestamp').asc(),
    #         frame=RowRange(start=-7, end=0)
    #     ),
    #     rolling_max=Window(
    #         expression=Max('airtemperature_max'),
    #         order_by=F('timestamp').asc(),
    #         frame=RowRange(start=-7, end=0)
    #     )
    # ).values('timestamp', 'rolling_min', 'rolling_max')

    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM ilm_ilm_rolling_1y')
        years_rolling_1y = cursor.fetchall()
        cursor.execute('SELECT * FROM ilm_ilm_rolling_5y')
        years_rolling_5y = cursor.fetchall()
        cursor.execute('SELECT * FROM ilm_ilm_rolling_8h')
        years_rolling_8h = cursor.fetchall()

    # Aastate Maksimum-miinimum tabeli andmed:
    for year in years_maxmin_qs:
        y = year['timestamp__year']
        year_min = year['airtemperature_min__min']
        obs_min = Ilm.objects.filter(
            airtemperature_min=year_min,
            timestamp__year=y
        ).values_list('timestamp', flat=True).first()

        year_max = year['airtemperature_max__max']
        obs_max = Ilm.objects.filter(
            airtemperature_max=year_max,
            timestamp__year=y
        ).values_list('timestamp', flat=True).first()

        year_temp_avg = year['airtemperature__avg']
        year_prec_sum = year['precipitations__sum']
        # Põevi Min(d)>+30 ja Max(d)<-30
        days_above30 = days_maxmin_qs.filter(
            timestamp__year=y,
            airtemperature_max__max__gte=30
        ).count()
        days_below30 = days_maxmin_qs.filter(
            timestamp__year=y,
            airtemperature_min__min__lte=-30
        ).count()
        # Öid, mil temperatuur ei lange alla 20 kraadi (öö = UTC18:00-02:00)
        # days_above20 = len([
        #     el
        #     for el
        #     in hours_rolling
        #     if (
        #         el['rolling_min'] and
        #         el['timestamp'].year==y and
        #         el['timestamp'].hour==2 and
        #         el['rolling_min'] >= 20
        #     )
        # ])
        days_above20 = len([
            el
            for el
            in years_rolling_8h
            if (
                el[1] and
                el[0].year==y and
                el[0].hour==2 and
                el[1] >= 20
            )
        ])
        # Päevi, mil temperatuur ei tõuse üle -20 kraadi (päev = UTC09:00-17:00)
        # days_below20 = len([
        #     el
        #     for el
        #     in hours_rolling
        #     if (
        #             el['rolling_max'] and
        #             el['timestamp'].year == y and
        #             el['timestamp'].hour == 17 and
        #             el['rolling_max'] <= -20
        #     )
        # ])
        days_below20 = len([
            el
            for el
            in years_rolling_8h
            if (
                    el[2] and
                    el[0].year == y and
                    el[0].hour == 17 and
                    el[2] <= -20
            )
        ])
        years_top[y] = {
            'year_min': year_min, # madalaim aasta jooksul mõõdetud õhutemperatuur
            'obs_min': obs_min, # madalaima aasta jooksul mõõdetud õhutemperatuuri mõõtmise aeg
            'year_max': year_max, # kõrgeim aasta jooksul mõõdetud õhutemperatuur
            'obs_max': obs_max, # kõrgeima aasta jooksul mõõdetud õhutemperatuuri mõõtmise aeg
            'year_temp_avg': year_temp_avg,
            'year_prec_sum': year_prec_sum,
            'days_below20': days_below20,
            'days_above20': days_above20,
            'days_below30': days_below30,
            'days_above30': days_above30
        }

    yearMin = min(years_top.keys())
    yearMax = max(years_top.keys())

    # heatmap data
    # def myFunc(e): # listi sortimiseks
    #     return (
    #         e[2], # year
    #         e[1], # month
    #         e[0], # day
    #     )

    data = list()
    # days_airtemp_monthmaxmin = dict()
    # for month in range(1, 13):
    #     days_airtemp_monthmaxmin[month] = {
    #         'airtemperature_max': -40,
    #         'airtemperature_max_timestamp': None,
    #         'airtemperature_min': 40,
    #         'airtemperature_min_timestamp': None,
    #     }
    for day in days_maxmin_qs:
        row = [
            day['timestamp__day'],
            day['timestamp__month'],
            day['timestamp__year'],
            round(day['airtemperature__avg'], 1),
            day['precipitations__sum'] if day['precipitations__sum'] else 0,
        ]
        data.append(row)

    #     # Kuude ekstreemumid
    #     if day['airtemperature_max__max'] and days_airtemp_monthmaxmin[day['timestamp__month']]['airtemperature_max'] < day['airtemperature_max__max']:
    #         days_airtemp_monthmaxmin[day['timestamp__month']] = {
    #             'airtemperature_max': day['airtemperature_max__max'],
    #             'airtemperature_max_timestamp': datetime(day['timestamp__year'], day['timestamp__month'], day['timestamp__day']),
    #             'airtemperature_min': days_airtemp_monthmaxmin[day['timestamp__month']]['airtemperature_min'],
    #             'airtemperature_min_timestamp': days_airtemp_monthmaxmin[day['timestamp__month']]['airtemperature_min_timestamp'],
    #         }
    #     if day['airtemperature_min__min'] and days_airtemp_monthmaxmin[day['timestamp__month']]['airtemperature_min'] > day['airtemperature_min__min']:
    #         days_airtemp_monthmaxmin[day['timestamp__month']] = {
    #             'airtemperature_max': days_airtemp_monthmaxmin[day['timestamp__month']]['airtemperature_max'],
    #             'airtemperature_max_timestamp': days_airtemp_monthmaxmin[day['timestamp__month']]['airtemperature_max_timestamp'],
    #             'airtemperature_min': day['airtemperature_min__min'],
    #             'airtemperature_min_timestamp': datetime(day['timestamp__year'], day['timestamp__month'], day['timestamp__day']),
    #         }

    # data.sort(key=myFunc)

    # Kuude ekstreemumid alernatiiv 2
    month_maxmin = IlmateenistusValga.calc_month_maxmin()

    # Heatmaps
    chartdata_heatmap_daily = "Date,Time,Temperature"
    chartdata_heatmap_relative = "Date,Time,Temperature"
    chartdata_heatmap_precipitations = "Date,Time,Precipitations"
    for row in data:
        y = row[2]
        m = row[1]
        d = row[0]
        t = row[3]
        p = row[4]
        # päevakeskmised temperatuurid
        chartdata_heatmap_daily += f'\n2016-{m}-{d},{y},{t}' # kasutame liigaastat 2016
        # päevakeskmised temperatuurid võrrelduna ajaloo keskmisega samal kuul ja päeval
        delta_t = round(t - days_airtemp_avgs[(m, d)], 1)
        chartdata_heatmap_relative += f'\n2016-{m}-{d},{y},{delta_t}'
        # sademete hulk
        chartdata_heatmap_precipitations += f'\n2016-{m}-{d},{y},{p}'

    # # arvutatakse ujuv aastakeskmine
    # years_rolling_1y = Ilm.objects.annotate(
    #     rolling_avg_1y=Window(expression=Avg('airtemperature'),
    #         order_by=F('timestamp').asc(),
    #         frame=RowRange(start=-int(365 * 24 / 2 - 1), end=int(365 * 24 / 2))),
    # ).values('timestamp', 'rolling_avg_1y')

    from statistics import mean
    histAvg = round(mean([el[1] for el in years_rolling_1y]), 1)

    chartdata_rolling_year_avg = 'aasta,ühe aasta keskmine, viie aasta keskmine'

    years_rolling = list(zip(
        [el[0] for el in years_rolling_1y],
        [el[1] for el in years_rolling_1y],
        [el[1] for el in years_rolling_5y]
    ))

    row_count = len(years_rolling)
    for index, row in enumerate(years_rolling):
        dt = row[0]
        y = dt.year
        m = dt.month
        d = dt.day
        h = dt.hour
        if (row_count - 365) > index:
            avg_1y_delta = round(row[1] - histAvg, 1)
        else:  # ääreperioodi ujuv ei ole korrektne
            avg_1y_delta = ''
        if (row_count - 365 * 5) > index:
            avg_5y_delta = round(row[2] - histAvg, 1)
        else: # ääreperioodi ujuv ei ole korrektne
            avg_5y_delta = ''
        chartdata_rolling_year_avg += f'\n{y}-{m}-{d} {h}:00,{avg_1y_delta},{avg_5y_delta}'

    context = {
        'years_top': years_top,
        'chartdata_heatmap_daily': chartdata_heatmap_daily,
        'chartdata_heatmap_relative': chartdata_heatmap_relative,
        'chartdata_heatmap_precipitations': chartdata_heatmap_precipitations,
        'chartdata_rolling_year_avg': chartdata_rolling_year_avg,
        # 'chartdata_rolling_year_avg_data_categories': chartdata_rolling_year_avg_data_categories,
        # 'chartdata_rolling_year_avg_data_averages': chartdata_rolling_year_avg_data_averages,
        # 'days_airtemp_monthmaxmin': days_airtemp_monthmaxmin,
        'month_maxmin': month_maxmin,
        'yearMin': yearMin,
        'yearMax': yearMax,
        'histAvg': histAvg
    }
    return render(
        request,
        'ilm/maxmin.html',
        context
    )

# Ei ole kasutusel, vigane
# def maxmin_new(request=None):
#     columns = ['timestamp', 'airtemperature', 'airtemperature_min', 'airtemperature_max', 'precipitations']
#     qs = Ilm.objects.all().\
#         values_list(*columns).\
#         order_by('timestamp')
#     # NB! timestamp = UTC aeg
#     df = pd.DataFrame(qs, columns=columns)
#     df[
#         ['airtemperature',
#         'airtemperature_min',
#         'airtemperature_max',
#         'precipitations']
#     ] = df[
#         ['airtemperature',
#         'airtemperature_min',
#         'airtemperature_max',
#         'precipitations']
#     ].astype(float)
#     # Lisame Eesti aja
#     ee = pytz.timezone('Europe/Tallinn')
#     df['timestamp_ee'] = df['timestamp'].dt.tz_convert(ee)
#     # test = df[(df['timestamp'].dt.year == 2004) & (df['timestamp'].dt.month == 3) & (df['timestamp'].dt.day == 28)]
#     # test = df[(df['timestamp_ee'].dt.year == 2004) & (df['timestamp_ee'].dt.month == 10) & (df['timestamp_ee'].dt.day == 31)]
#     # print(test.head(10))
#     # print(test['timestamp'].dt.tz_convert('Europe/Tallinn').head(10))
#     # print(test['timestamp'].dt.tz_convert(ee).head(10))

#     window = timedelta(hours=8)
#     df_rolling = df.set_index('timestamp').rolling(window).agg(
#         {
#             'airtemperature_max': ['max'],
#             'airtemperature_min': ['min'],
#             'precipitations': ['sum']
#         }
#     )
#     df_rolling.columns = df_rolling.columns.get_level_values(0) # jätame ainult 1. taseme pealkirjad

#     days_maxmin_df = df.groupby(
#         [df['timestamp_ee'].dt.year, df['timestamp_ee'].dt.month, df['timestamp_ee'].dt.day]).apply(
#         lambda s: pd.Series(
#             {
#                 "airtemperature_max": s["airtemperature_max"].dropna().max(),
#                 "airtemperature_min": s["airtemperature_min"].dropna().min(),
#                 "airtemperature_avg": s["airtemperature"].dropna().mean(),
#                 "precipitations_sum": s["precipitations"].dropna().sum(),
#             }
#         )
#     )

#     years_maxmin_df = df.groupby([df['timestamp_ee'].dt.year]).apply(
#         lambda s: pd.Series(
#             {
#                 "year_max": s["airtemperature_max"].max(),
#                 "obs_max": None,
#                 "year_min": s["airtemperature_min"].min(),
#                 "obs_min": None,
#                 "year_temp_avg": s["airtemperature"].mean(),
#                 "year_prec_sum": s["precipitations"].sum(),
#                 "days_above30": None,
#                 "days_below30": None,
#                 "days_above20": None,
#                 "days_below20": None,
#             }
#         )
#     )

#     for year, row in years_maxmin_df.iterrows():
#         # Lisama aasta maksimaalse temperatuuri mõõtmise aja
#         if not row['year_max'] != row['year_max']:
#             obs_max_idx = df[df['timestamp_ee'].dt.year == year]['airtemperature_max'].idxmax()
#             obs_max = df.loc[obs_max_idx].at['timestamp_ee']
#             years_maxmin_df.loc[year, 'obs_max'] = obs_max
#             # print(obs_max)
#         # Lisama aasta minimaalse temperatuuri mõõtmise aja
#         if not row['year_min'] != row['year_min']:
#             obs_min_idx = df[df['timestamp_ee'].dt.year == year]['airtemperature_min'].idxmin()
#             obs_min = df.loc[obs_min_idx].at['timestamp_ee']
#             years_maxmin_df.loc[year, 'obs_min'] = obs_min
#             # print(obs_min)
#         # Lisame aasta päevade arvu, millal temperatuur tõusis üle 30
#         days_above30 = days_maxmin_df[
#             (days_maxmin_df.index[0] == year) &
#             (days_maxmin_df['airtemperature_max'] >= 30)
#             ]['airtemperature_max'].count()
#         years_maxmin_df.loc[year, 'days_above30'] = days_above30
#         # Lisame aasta päevade arvu, millal temperatuur langes alla 30
#         days_below30 = days_maxmin_df[
#             (days_maxmin_df.index[0] == year) &
#             (days_maxmin_df['airtemperature_min'] <= -30)
#             ]['airtemperature_min'].count()
#         years_maxmin_df.loc[year, 'days_below30'] = days_below30
#         # Troopiline öö
#         days_above20 = df_rolling[
#             (df_rolling['airtemperature_max'] >= 20) &
#             (df_rolling.index.year == year) &
#             (df_rolling.index.hour == 2)
#             ]['airtemperature_max'].count()
#         years_maxmin_df.loc[year, 'days_above20'] = days_above20
#         # Arktiline päev
#         days_below20 = df_rolling[
#             (df_rolling['airtemperature_min'] <= -20) &
#             (df_rolling.index.year == year) &
#             (df_rolling.index.hour == 17)
#             ]['airtemperature_min'].count()
#         years_maxmin_df.loc[year, 'days_below20'] = days_below20

#     return df
