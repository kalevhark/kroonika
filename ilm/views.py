import calendar
from datetime import datetime, date, timedelta
import json
# from lxml import etree
import xml.etree.ElementTree as ET

from astral import *
from django.db.models import Sum, Count, Avg, Min, Max
from django.http import JsonResponse
from django.shortcuts import render, redirect
import pandas as pd
import pytz
import requests

from . import IlmateenistusValga

from .forms import NameForm
from .models import Ilm, Jaam

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

# Highcharts vaikevärvid
COLORS = [
    "#7cb5ec", "#434348",
    "#90ed7d", "#f7a35c",
    "#8085e9", "#f15c80",
    "#e4d354", "#2b908f",
    "#f45b5b", "#91e8e1"
]

# Decimal ndmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value)
    except:
        return None

def index(request):
    # Avalehekülg, kus näidatakse 24h ilmaajalugu + 48h prognoos
    return render(request, 'ilm/index.html', {})

def history(request):
    # Ajalooliste ilmaandmete töötlused
    valik_aasta = bdi.aasta # Salvestatud valikaasta
    valik_kuu = bdi.kuu # Salvestatud valikkuu
    valik_p2ev = bdi.p2ev # Salvestatud valikpäev
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NameForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            bdi.aasta = form.cleaned_data['aasta']
            bdi.kuu = form.cleaned_data['kuu']
            bdi.p2ev = form.cleaned_data['p2ev']
    # if a GET (or any other method) we'll create a blank form
    else:
        form = NameForm(initial={'aasta': bdi.aasta, 'kuu': bdi.kuu, 'p2ev': bdi.p2ev})

    return render(request, 'ilm/history.html', {
        'form': form
    })


def sun_moon(dt):
    # Tagastab konkreetese kuupäeva (ajavööndi väärtusega) päikese- ja kuuandmed
##        a = Astral(GoogleGeocoder)
##        location = a['Sulevi 9a/Valga'] # Kui annab veateate, tuleb enne GoogleMapsiga otsida (cache?)
##    dt = pytz.timezone('Europe/Tallinn').localize(dt) # Vajalik, kui ajavöönd ei ole märgitud
    city_name = 'Tallinn'
    a = Astral()
    a.solar_depression = 'civil'
    city = a[city_name]
    s = {}
    s['sun'] = city.sun(date=dt, local=True)
    s['moon'] = a.moon_phase(date=dt)
    return s


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
    categories = []
    sel_temp_averages = []
    sel_temp_ranges = []
    sel_prec_sums = []
    hist_temp_averages = []
    hist_temp_ranges = []
    sel = list(
        Ilm.objects
            .filter(timestamp__year=bdi.aasta)
            .values('timestamp__month')
            .annotate(Avg('airtemperature'), Min('airtemperature'), Max('airtemperature'), Sum('precipitations'))
            .order_by('timestamp__month')
    )
    hist = list(bdi.qs12)
    offset = 0  # Kui valitud aastas ei ole 12 kuu mõõtmistulemusi, siis arvutatakse vahe
    for i in range(len(sel)):
        while (
                (sel[i]['timestamp__month'] != hist[i + offset]['timestamp__month'])
        ):
            offset += 1

        categories.append(
            KUUD[int(sel[i]['timestamp__month'])]
        )
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
        hist_temp_averages.append(round(hist[i + offset]['airtemperature__avg'], 1))
        hist_temp_ranges.append(
            [
                round(float(hist[i + offset]['airtemperature__min']), 1),
                round(float(hist[i + offset]['airtemperature__max']), 1)
            ]
        )
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
            series_sel_prec_sums
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
    # Valitud kuu pärig
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
    if bdi.p2ev == None:
        chart['tyhi'] = True
        return JsonResponse(chart)
    chart['aasta'] = bdi.aasta
    chart['kuu'] = bdi.kuu
    chart['p2ev'] = bdi.p2ev
    # Kontroll
    kontroll = pytz.timezone('utc').localize(datetime(bdi.aasta, bdi.kuu, bdi.p2ev))
    print(kontroll, bdi.stopp)
    if (
            (kontroll > bdi.stopp) or
            (kontroll < bdi.start.replace(hour=0))
    ):
        chart['tyhi'] = True
        return JsonResponse(chart)
    else:
        chart['tyhi'] = False
    sel = list(
        Ilm.objects \
            .filter(timestamp__year=bdi.aasta, timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev) \
            .values('timestamp__hour', 'airtemperature', 'precipitations')
    )
    hist = list(bdi.qs8784.filter(timestamp__month=bdi.kuu, timestamp__day=bdi.p2ev))
    # Andmete ettevalmistamine
    categories = []
    sel_temps = []
    sel_precs = []
    hist_temp_averages = []
    hist_temp_ranges = []
    offset = 0  # Kui valitud päevas ei ole kõigi päevade mõõtmistulemusi, siis arvutatakse vahe
    for i in range(len(hist)):
        # X-telje väärtused
        categories.append(
            f"{str(hist[i]['timestamp__hour']).zfill(2)}:00"
        )
        # Kogu ajaloo väärtused
        hist_temp_averages.append(round(hist[i]['airtemperature__avg'], 1))
        hist_temp_ranges.append(
            [
                round(float(hist[i]['airtemperature__min']), 1),
                round(float(hist[i]['airtemperature__max']), 1)
            ]
        )
        # Valitud kuu väärtused

        if sel[offset]['timestamp__hour'] == hist[i]['timestamp__hour']:
            # Valitud kuu päeva andmed olemas
            sel_temps.append(round(float_or_none(sel[offset]['airtemperature']), 1))
            if sel[offset]['precipitations']:
                sel_precs.append(round(float(sel[offset]['precipitations']), 1))
            else:
                sel_precs.append(0)  # Kui mõõtmistulemusi kogu päev polnud
            if offset < (len(sel) - 1):
                offset += 1
        else:
            # Valitud kuu päeva andmeid ei ole
            sel_temps.append(None)
            sel_precs.append(None)
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
            'text': f'{bdi.p2ev}.{KUUD[bdi.kuu]} {bdi.aasta}'
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
    if bdi.p2ev == None:
        chart['tyhi'] = True
        return JsonResponse(chart)
    chart['aasta'] = bdi.aasta
    chart['kuu'] = bdi.kuu
    chart['p2ev'] = bdi.p2ev
    # Kontroll
    kontroll = pytz.timezone('utc').localize(datetime(bdi.aasta, bdi.kuu, bdi.p2ev))
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
               # .order_by('timestamp__year')
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


def yrno_48h():
    # Weather forecast from Yr, delivered by the Norwegian Meteorological Institute and the NRK
    href = 'http://www.yr.no/place/Estonia/Valgamaa/Valga/forecast_hour_by_hour.xml'
    # tree = etree.parse(href)
    # root = tree.getroot()
    r = requests.get(href)
    root = ET.fromstring(r.text)
    yr = {}
    tag_timezone = root.find("location").find("timezone") # Otsime XML puu asukoha andmetega
    utcoffsetMinutes = int(tag_timezone.attrib['utcoffsetMinutes'])
    tag_meta = root.find("meta") # Otsime XML puu metaandmetega
    yr['meta'] = {}
    yr['meta']['lastupdate'] = datetime.strptime(tag_meta.find("lastupdate").text, '%Y-%m-%dT%H:%M:%S')
    yr['meta']['nextupdate'] = datetime.strptime(tag_meta.find("nextupdate").text, '%Y-%m-%dT%H:%M:%S')
    yr['forecast'] = {}
    cat = []
    prec = []
    wind = []
    temp = []
    pres = []
    symb = []
    dateticks = [0] # Graafikul kuupäevatikkerite jaoks
    tag_forecast = root.find("forecast").find("tabular") # Otsime XML puu prognoosi tabeliga
    for n in range(len(tag_forecast)):
        data = tag_forecast[n]
        date = pytz.timezone('Europe/Tallinn').localize(datetime.strptime(data.attrib['from'], '%Y-%m-%dT%H:%M:%S'))
        if date.hour == 0:
            dateticks.append(n)
        cat.append(date) # Aeg
        prec.append(float(data.find("precipitation").attrib['value'])) # Sademed
        wind.append(
            [float(data.find("windSpeed").attrib['mps']),
            float(data.find("windDirection").attrib['deg'])]
        )
        temp.append(float(data.find("temperature").attrib['value'])) # Temperatuur
        pres.append(float(data.find("pressure").attrib['value'])) # Õhurõhk
        symb.append(data.find("symbol").attrib['var']) # Ilmasümboli kood (YR)
    yr['forecast'] = {}
    yr['forecast']['start'] = cat[0] # Mis kellast prognoos algab
    yr['forecast']['temperatures'] = temp
    yr['forecast']['windbarbs'] = wind
    yr['forecast']['airpressures'] = pres
    yr['forecast']['precipitations'] = prec
    yr['forecast']['symbols'] = symb
    return yr


def mitutundi(algus, l6pp):
    # Tagastab kahe kuupäeva vahe tundides
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
        sun = sun_moon(d)['sun']
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
            'to': d.replace(hour=0) + timedelta(hours=24),
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

def mixed_ilmateade(request):
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
        freq='H'
    )
    # x-telg 2 märgime ainult kuupäevavahetused
    c_00hours = []
    for el in c:
        if el.hour == 0:
            c_00hours.append(el)
    # Ilmaandmete hankimine
    andmed_eelnevad24h = bdi.viimase24h_andmed(
        'Valga',
        d.replace(minute=0, second=0, microsecond=0)
    )
    andmed_j2rgnevad48h = yrno_48h()
    # Pimeda aja varjutused
    andmed_nighttime = nighttime2(c[0], c[-1])
    # Hetkeaja joon
    andmed_nyyd = mitutundi(c[0], d)
    # Kuupäeva teisendused highchart formaati (epoch time)
    graafik_categories = list((el + timedelta(seconds=el.utcoffset().seconds)).timestamp()*1000 for el in c)
    graafik_nullpunkt = graafik_categories[0]
    graafik_00hours = list(
        ((el + timedelta(seconds=utcoffset)).timestamp() * 1000 - graafik_nullpunkt) / (60 * 60 * 1000)
        for el in c_00hours
    )

    graafik_title = (
        'Mõõtmised: ' +
        andmed_eelnevad24h['ilmastring'] + '; ' +
        'Prognoos:' + 
        andmed_j2rgnevad48h['meta']['lastupdate'].strftime("%d.%m.%Y %H:%M")
    )
    
    graafik_subtitle = (
        'Allikad: ' +
        'mõõtmised: ' +
        '<a href="https://www.ilmateenistus.ee/asukoha-prognoos/?id=8918" target="_blank">ilmateenistus.ee</a>' + '; ' 
        'prognoos:' + 
        '<a href="https://www.yr.no/place/Estonia/Valgamaa/Valga/hour_by_hour.html" target="_blank">yr.no</a>:'
    )

    # Graafiku kujundamine
    chart = {
        'title': {
            'text': graafik_title,
            'align': 'left',
            'style': {"fontSize": "12px"},
            'x': 30,
            'y': 40
        },
	
	    'subtitle': {
            'text': graafik_subtitle,
            # 'floating': True,
            'align': 'left',
            'x': 30,
            'verticalAlign': 'bottom',
            # 'y': 40
        },

        'plotOptions': {
            'series': {
                'pointPadding': 0,
                'groupPadding': 0,
                'borderWidth': 0,
                'shadow': False
            },
            'windbarb': {
                'lineWidth': 1,
                'vectorLength': 15,
                'tooltip': {
                    'valueSuffix': ' m/s'
                }
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
                    'y': -5
                },
                'opposite': True,
                'tickLength': 20,
                'gridLineWidth': 4
            }
        ],
	
        'yAxis': [
            { # temperature axis
                'title': {
                    'text': ''
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
            'name': '',
            'data': ['null'] * 72, # Joonistame tühja graafiku 72 tunniks
            'showInLegend': False
        }, {
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
            'zIndex': 1,
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
	    }, {
            'name': 'Temperatuur (prognoos)', # Prognoos
            'data': 24 * [None]+ andmed_j2rgnevad48h['forecast']['temperatures'],
            'type': 'spline',
            'marker': {
                'enabled': False,
                'states': {
                    'hover': {
                        'enabled': True
                    }
                }
            },
            'zIndex': 1,
            'dashStyle': 'shortdot',
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
	    }, {
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
                    'color': 'gray'
                }
            },
            'lineWidth' : 2, 
            'tooltip': {
                'valueSuffix': ' mm'
            }
	    }, {
            'name': 'Sademed (prognoos)',
            'data': 24 * [None]+ andmed_j2rgnevad48h['forecast']['precipitations'],
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
                    'color': 'gray'
                }
            },
            'lineWidth' : 2, 
            'tooltip': {
                'valueSuffix': ' mm'
            }
	    }, {
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
            'name': 'Õhurõhk (prognoos)',
            'data': 24 * [None]+ andmed_j2rgnevad48h['forecast']['airpressures'],
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
            'name': 'Tuul (mõõdetud)',
            'data': andmed_eelnevad24h['windbarbs'],
            'type': 'windbarb',
	    }, {
            'name': 'Tuul (prognoos)',
            'data': 24 * [None]+ andmed_j2rgnevad48h['forecast']['windbarbs'],
            'type': 'windbarb',
            'color': 'gray'
	    }]
    }

    chart['yrno_symbols'] = andmed_eelnevad24h['symbols'] + andmed_j2rgnevad48h['forecast']['symbols']
    return JsonResponse(chart)
