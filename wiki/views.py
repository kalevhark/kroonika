from collections import Counter, OrderedDict
import datetime
import requests
from typing import Dict, Any

from django.conf import settings
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, BooleanField, DecimalField, IntegerField, ExpressionWrapper
from django.db.models import Count, Max, Min
from django.db.models.functions import ExtractYear
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect
from django.shortcuts import get_list_or_404, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from django.utils.version import get_version
from django.views.generic.dates import ArchiveIndexView, YearArchiveView, MonthArchiveView, DayArchiveView
from django.views.generic.edit import UpdateView

import django_filters
from django_filters.views import FilterView

from .models import Allikas, Artikkel, Isik, Objekt, Organisatsioon, Pilt, Vihje
from .forms import ArtikkelForm, IsikForm, OrganisatsioonForm, ObjektForm
from .forms import VihjeForm
#
# reCAPTCHA kontrollifunktsioon
#
def check_recaptcha(request):
    data = request.POST

    # get the token submitted in the form
    recaptcha_response = data.get('g-recaptcha-response')
    print(settings.GOOGLE_RECAPTCHA_SECRET_KEY)
    # captcha verification
    url = 'https://www.google.com/recaptcha/api/siteverify'
    payload = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    resp = requests.post(
        url,
        data=payload
    )
    result_json = resp.json()
    if result_json.get('success'):
        return True
    else:
        # Päringu teostamise IP aadress
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            # print(ip)
        print(ip, result_json)
        return False

#
# Avalehekülg
#
def info(request):
    andmebaasid = []
    andmebaasid.append(' '.join(['Allikad: ', str(Allikas.objects.count()), 'kirjet']))
    andmebaasid.append(
        ' '.join(
            [
                'Artikkel: ',
                f'kirjeid {Artikkel.objects.count()} ',
                f'viidatud {Artikkel.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Artikkel.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Isik: ',
                f'kirjeid {Isik.objects.count()} ',
                f'viidatud {Isik.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Isik.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Objekt: ',
                f'kirjeid {Objekt.objects.count()} ',
                f'viidatud {Objekt.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Objekt.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Organisatsioon: ',
                f'kirjeid {Organisatsioon.objects.count()} ',
                f'viidatud {Organisatsioon.objects.filter(viited__isnull=False).distinct().count()} ',
                f'pildiga {Organisatsioon.objects.filter(pilt__isnull=False).distinct().count()} '
            ]
        )
    )
    andmebaasid.append(
        ' '.join(
            [
                'Pilt: ',
                f'kirjeid {Pilt.objects.count()} ',
                f'viidatud {Pilt.objects.filter(viited__isnull=False).distinct().count()} '
            ]
        )
    )
    # Artiklite ülevaade
    andmed = Artikkel.objects.aggregate(Count('id'), Min('hist_searchdate'), Max('hist_searchdate'))
    # TODO: Ajutine ümberkorraldamiseks
    revision_data: Dict[str, Any] = {}
    revision_data['kroonika'] = Artikkel.objects.filter(kroonika__isnull=False).count()
    revision_data['revised'] = Artikkel.objects.filter(kroonika__isnull=False).annotate(num_viited=Count('viited')).filter(num_viited__gt=1).count()
    revision_data['viiteta'] = list(Artikkel.objects.filter(viited__isnull=True).values_list('id', flat=True))

    return render(
        request,
        'wiki/wiki_info.html',
        {
            'andmebaasid': andmebaasid,
            'andmed': andmed,
            # 'recaptcha_key': settings.GOOGLE_RECAPTCHA_PUBLIC_KEY,
            'revision_data': revision_data, # TODO: Ajutine ümberkorraldamiseks
        }
    )


def heatmap(request):
    perioodid = Artikkel.objects.\
        filter(hist_searchdate__isnull=False).\
        values('hist_searchdate__year', 'hist_searchdate__month').\
        annotate(ct=Count('id')).\
        order_by('hist_searchdate__year', 'hist_searchdate__month')
    bigdata = ''
    for periood in perioodid:
        bigdata += f"\n{periood['hist_searchdate__year']},{periood['hist_searchdate__month']},{periood['ct']}"
    bigdata = """1224,1,1
1266,1,1
1284,1,1
1286,1,1
1298,1,1
1329,1,1
1334,1,1
1345,1,1
1422,1,1
1460,1,1
1479,1,1
1481,1,1
1498,1,1
1501,1,2
1558,7,1
1582,1,1
1584,6,1
1590,4,1
1600,1,1
1626,2,1
1626,3,1
1634,1,1
1638,1,1
1657,6,1
1669,1,1
1675,1,1
1678,1,1
1682,1,1
1686,1,1
1688,1,1
1702,1,1
1702,7,1
1720,4,1
1720,8,1
1726,1,1
1764,10,1
1769,1,1
1769,5,1
1770,1,1
1772,1,1
1782,1,1
1783,1,1
1783,7,1
1784,2,1
1785,1,1
1786,8,1
1787,3,1
1789,1,1
1805,1,1
1808,1,1
1811,1,1
1816,1,1
1819,1,1
1821,6,1
1821,8,1
1821,9,1
1822,6,1
1822,8,1
1822,9,1
1826,1,1
1827,6,1
1827,8,1
1827,9,1
1829,6,1
1829,8,1
1829,9,1
1834,1,1
1834,6,1
1834,8,1
1834,9,1
1834,12,1
1835,1,2
1836,6,1
1836,8,1
1836,9,1
1836,12,1
1837,6,1
1837,8,1
1837,9,1
1837,12,1
1838,6,1
1838,8,1
1838,9,1
1838,12,1
1839,1,1
1839,6,1
1839,8,1
1839,9,1
1839,11,1
1839,12,1
1840,6,1
1840,8,1
1840,9,1
1840,12,1
1841,6,1
1841,8,1
1841,9,1
1841,12,1
1849,1,1
1849,12,1
1852,12,3
1853,1,2
1853,6,1
1855,1,1
1861,8,1
1862,1,2
1864,2,3
1864,6,1
1865,1,2
1865,2,1
1865,8,1
1866,1,2
1866,2,1
1866,6,1
1866,8,1
1866,9,1
1866,10,1
1866,11,1
1867,1,1
1867,2,2
1867,3,1
1867,4,1
1867,6,1
1867,8,2
1868,3,1
1868,4,1
1868,5,2
1868,6,1
1868,7,1
1868,9,1
1868,10,1
1868,12,1
1869,3,1
1869,6,1
1869,8,2
1870,1,2
1870,3,1
1870,7,1
1871,4,2
1871,10,1
1871,12,1
1872,2,1
1872,3,1
1872,5,1
1872,7,1
1872,9,1
1872,10,1
1873,6,2
1873,7,1
1873,8,1
1874,2,2
1874,5,1
1874,6,3
1874,7,1
1874,9,1
1874,10,1
1874,11,1
1874,12,2
1875,1,1
1875,4,1
1875,5,1
1875,6,4
1875,7,1
1875,9,1
1875,10,1
1876,1,1
1876,5,1
1876,6,1
1876,9,1
1876,10,1
1876,12,2
1877,1,2
1877,5,1
1877,6,3
1877,7,1
1877,8,1
1878,4,1
1878,6,1
1878,9,1
1879,1,3
1879,5,1
1879,8,1
1879,9,2
1879,12,2
1880,1,1
1880,2,1
1880,3,1
1880,4,1
1880,8,2
1880,10,1
1881,1,1
1881,2,2
1881,3,1
1881,4,1
1881,5,1
1881,7,4
1881,10,4
1881,11,1
1881,12,3
1882,1,1
1882,8,3
1882,9,1
1882,12,4
1883,1,2
1883,2,3
1883,3,3
1883,4,2
1883,6,1
1883,8,4
1883,9,1
1883,11,1
1883,12,2
1884,1,1
1884,2,1
1884,3,4
1884,4,1
1884,5,2
1884,6,2
1884,8,1
1884,9,2
1884,10,1
1884,11,1
1884,12,1
1885,1,1
1885,3,1
1885,6,2
1885,7,3
1885,9,2
1885,10,1
1885,11,1
1885,12,1
1886,1,4
1886,3,2
1886,5,2
1886,6,2
1886,7,1
1886,10,1
1887,1,4
1887,5,1
1887,6,3
1887,8,3
1887,9,2
1887,11,2
1888,1,5
1888,2,2
1888,3,2
1888,4,1
1888,5,2
1888,6,3
1888,8,4
1888,9,5
1888,12,3
1889,1,7
1889,2,4
1889,3,4
1889,4,3
1889,5,1
1889,6,4
1889,7,4
1889,8,3
1889,9,5
1889,10,1
1889,11,1
1889,12,3
1890,1,1
1890,3,1
1890,4,2
1890,5,2
1890,6,2
1890,7,5
1890,8,6
1890,9,4
1890,10,5
1890,11,6
1890,12,5
1891,1,3
1891,2,4
1891,3,3
1891,4,6
1891,5,2
1891,6,4
1891,7,5
1891,8,4
1891,9,8
1891,10,6
1891,11,7
1891,12,2
1892,1,6
1892,2,4
1892,3,6
1892,4,6
1892,5,4
1892,6,5
1892,7,5
1892,8,4
1892,9,2
1892,10,5
1892,11,6
1892,12,6
1893,1,3
1893,2,7
1893,3,7
1893,4,5
1893,5,3
1893,6,1
1893,7,6
1893,8,5
1893,9,6
1893,10,7
1893,11,7
1893,12,2
1894,1,7
1894,2,7
1894,3,10
1894,4,5
1894,5,5
1894,6,3
1894,7,3
1894,8,8
1894,9,6
1894,10,8
1894,11,6
1894,12,8
1895,1,1
1895,2,4
1895,3,4
1895,5,1
1896,1,1
1897,11,1
1898,12,1
1900,1,4
1900,3,1
1900,4,3
1900,7,2
1900,8,3
1900,10,2
1900,11,3
1901,1,2
1901,4,2
1901,6,1
1901,7,2
1901,8,3
1901,9,3
1901,11,1
1901,12,4
1902,1,3
1902,2,4
1902,3,2
1902,4,4
1902,5,4
1902,6,4
1902,7,2
1902,8,5
1902,9,4
1902,10,4
1902,11,1
1902,12,4
1903,1,2
1903,2,3
1903,3,4
1903,4,2
1903,5,2
1903,6,1
1903,7,5
1903,8,2
1903,9,3
1903,10,2
1903,11,2
1903,12,2
1904,1,3
1904,2,1
1904,3,2
1904,4,1
1904,5,3
1904,6,4
1904,7,1
1904,8,1
1904,9,4
1904,10,2
1904,11,1
1905,1,2
1905,2,7
1905,3,3
1905,4,1
1905,5,2
1905,6,1
1905,8,2
1905,9,4
1905,10,4
1905,11,4
1905,12,4
1906,1,7
1906,2,3
1906,3,4
1906,4,3
1906,5,2
1906,6,3
1906,7,3
1906,8,1
1906,9,4
1906,10,5
1906,11,1
1906,12,5
1907,1,4
1907,2,10
1907,3,9
1907,4,6
1907,5,7
1907,6,9
1907,7,2
1907,8,3
1907,9,4
1907,10,2
1907,11,4
1907,12,7
1908,1,5
1908,2,6
1908,3,9
1908,4,2
1908,5,6
1908,6,4
1908,7,2
1908,8,6
1908,10,5
1908,11,3
1908,12,3
1909,1,4
1909,2,1
1909,3,5
1909,4,2
1909,5,3
1909,6,2
1909,8,4
1909,9,4
1909,10,2
1909,11,2
1909,12,9
1910,1,3
1910,2,6
1910,3,6
1910,4,7
1910,5,10
1910,6,3
1910,7,1
1910,8,5
1910,9,1
1910,10,2
1910,11,2
1910,12,4
1911,1,2
1911,2,2
1911,3,4
1911,4,4
1911,5,4
1911,6,1
1911,8,1
1911,9,3
1911,10,4
1911,11,1
1911,12,2
1912,1,2
1912,2,3
1912,3,1
1912,4,2
1912,5,9
1912,6,1
1912,7,7
1912,8,1
1912,9,2
1912,10,4
1912,11,4
1912,12,3
1913,1,5
1913,2,6
1913,3,7
1913,4,3
1913,5,1
1913,6,2
1913,7,4
1913,8,3
1913,9,4
1913,10,5
1913,11,5
1913,12,1
1914,1,1
1914,2,3
1914,3,4
1914,4,7
1914,5,6
1914,6,8
1914,7,7
1914,8,4
1914,9,4
1914,11,2
1914,12,3
1915,1,3
1915,2,1
1915,3,6
1915,4,6
1915,5,4
1915,6,2
1915,7,1
1915,8,1
1915,9,1
1915,12,4
1916,1,2
1916,3,2
1916,4,1
1916,5,1
1916,6,1
1916,9,3
1916,10,2
1916,12,1
1917,1,3
1917,2,2
1917,3,8
1917,4,4
1917,7,2
1917,8,1
1917,9,1
1917,11,3
1918,2,3
1918,4,3
1918,6,1
1918,7,3
1918,8,1
1918,10,2
1918,11,3
1918,12,5
1919,1,3
1919,2,10
1919,3,1
1919,4,3
1919,6,3
1919,7,6
1919,8,1
1919,9,3
1919,10,6
1919,11,2
1919,12,2
1920,1,2
1920,2,3
1920,3,4
1920,4,2
1920,5,5
1920,6,6
1920,7,3
1920,8,3
1920,9,3
1920,10,9
1920,12,1
1921,1,5
1921,2,3
1921,3,5
1921,4,4
1921,5,2
1921,6,4
1921,7,4
1921,8,3
1921,9,3
1921,10,1
1921,11,2
1922,1,9
1922,2,1
1922,3,5
1922,4,1
1922,5,2
1922,6,4
1922,7,2
1922,9,6
1922,10,6
1922,11,1
1922,12,2
1923,1,1
1923,2,1
1923,4,8
1923,5,4
1923,6,3
1923,7,2
1923,8,3
1923,9,4
1923,10,2
1923,11,1
1923,12,1
1924,1,5
1924,2,4
1924,3,4
1924,4,4
1924,5,4
1924,6,3
1924,7,2
1924,8,3
1924,9,2
1924,10,5
1924,11,1
1924,12,6
1925,1,10
1925,2,7
1925,3,2
1925,4,5
1925,5,2
1925,6,3
1925,7,1
1925,8,1
1925,9,6
1925,10,2
1925,11,1
1925,12,3
1926,1,3
1926,2,6
1926,3,6
1926,4,1
1926,5,6
1926,6,6
1926,7,3
1926,8,3
1926,9,1
1926,10,4
1926,11,7
1926,12,5
1927,1,6
1927,2,7
1927,3,5
1927,4,6
1927,5,5
1927,6,3
1927,7,2
1927,8,4
1927,9,3
1927,10,5
1927,11,3
1927,12,5
1928,1,13
1928,2,2
1928,3,5
1928,4,4
1928,5,9
1928,6,5
1928,7,1
1928,8,3
1928,11,7
1928,12,10
1929,1,7
1929,2,10
1929,3,2
1929,4,4
1929,5,4
1929,6,8
1929,7,4
1929,8,7
1929,9,13
1929,10,10
1929,11,4
1929,12,4
1930,1,5
1930,2,5
1930,3,10
1930,4,6
1930,5,8
1930,6,6
1930,7,1
1930,8,7
1930,9,9
1930,10,6
1930,11,7
1930,12,5
1931,1,9
1931,2,6
1931,3,4
1931,4,13
1931,5,16
1931,6,4
1931,7,7
1931,8,14
1931,9,11
1931,10,9
1931,11,6
1931,12,12
1932,1,7
1932,2,11
1932,3,6
1932,4,10
1932,5,6
1932,6,6
1932,7,2
1932,8,4
1932,9,9
1932,10,5
1932,11,5
1932,12,5
1933,1,10
1933,2,7
1933,3,4
1933,4,5
1933,5,6
1933,6,7
1933,7,15
1933,8,8
1933,9,14
1933,10,11
1933,11,10
1933,12,13
1934,1,5
1934,2,5
1934,3,2
1934,4,5
1934,5,6
1934,6,10
1934,7,8
1934,8,6
1934,9,15
1934,10,8
1934,11,7
1934,12,6
1935,1,4
1935,2,12
1935,3,5
1935,4,7
1935,5,8
1935,6,5
1935,7,7
1935,8,4
1935,9,12
1935,10,4
1935,11,5
1935,12,4
1936,1,5
1936,2,5
1936,3,4
1936,4,8
1936,5,9
1936,6,9
1936,8,9
1936,9,14
1936,10,11
1936,11,4
1936,12,4
1937,1,4
1937,2,6
1937,3,9
1937,4,4
1937,5,12
1937,6,7
1937,7,6
1937,8,7
1937,9,9
1937,10,5
1937,11,6
1937,12,7
1938,1,3
1938,2,5
1938,3,5
1938,4,6
1938,5,15
1938,6,5
1938,8,2
1938,9,9
1938,10,5
1938,11,8
1938,12,11
1939,1,5
1939,2,13
1939,3,11
1939,4,5
1939,5,11
1939,6,8
1939,7,3
1939,8,4
1939,9,5
1939,10,8
1939,11,6
1939,12,4
1940,1,9
1940,2,5
1940,3,8
1940,4,7
1940,5,7
1940,6,13
1940,7,9
1940,8,15
1940,9,7
1940,10,4
1940,11,4
1940,12,4
1941,1,5
1941,2,6
1941,3,2
1941,4,4
1941,5,4
1941,6,13
1941,7,12
1941,8,4
1941,9,3
1941,10,4
1941,11,1
1942,1,6
1942,2,3
1942,3,4
1942,4,4
1942,5,7
1942,6,7
1942,7,7
1942,8,7
1942,9,7
1942,10,7
1942,11,12
1942,12,4
1943,1,3
1943,2,4
1943,3,7
1943,4,5
1943,5,11
1943,6,8
1943,7,8
1943,8,2
1943,9,4
1943,10,10
1943,11,3
1943,12,4
1944,1,5
1944,2,4
1944,3,3
1944,4,1
1944,5,6
1944,6,5
1944,7,2
1944,8,2
1944,9,2
1945,9,1
1945,10,1
1949,9,1
1971,3,1
1981,9,1
2004,7,1"""
    andmed = Artikkel.objects.aggregate(Count('id'), Min('hist_searchdate'), Max('hist_searchdate'))
    return render(
        request,
        'wiki/wiki_heatmap.html',
        {
            'andmed': andmed,
            'bigdata': bigdata
        }
    )

#
# Tagasiside vormi töötlemine
#
def feedback(request):
    # if this is a POST request we need to process the form data
    http_referer = request.META['HTTP_REFERER'] # mis objektilt tuli vihje
    remote_addr = request.META['REMOTE_ADDR'] # kasutaja IP aadress
    if request.method == 'POST' and check_recaptcha(request):
        # create a form instance and populate it with data from the request:
        form = VihjeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            vihje = {
                'kirjeldus': form.cleaned_data['kirjeldus'],
                'kontakt': form.cleaned_data['kontakt'],
                'http_referer': http_referer,
                'remote_addr': remote_addr,
                'django_version': get_version() # Django versioon
            }
            # Salvestame andmed andmebaasi
            v = Vihje(**vihje)
            v.save()
            vihje['inp_date'] = v.inp_date
            messages.add_message(request, messages.INFO, 'Tagasiside saadetud.')
            context = {
                'vihje': vihje
            }
            return render(
                request,
                'wiki/wiki_feedback.html',
                context
            )

    # Kui on GET või tühi vorm, siis laeme algse lehe
    messages.add_message(request, messages.WARNING, 'Tühja vormi ei saadetud.')
    return HttpResponseRedirect(http_referer)

#
# Avakuva
#
def algus(request):
    andmed = {} # Selle muutuja saadame veebi
    p2ev = datetime.date.today().day
    kuu = datetime.date.today().month
    aasta = datetime.date.today().year
    
    # Andmebaas Artikkel andmed veebi
    a = dict()
    kirjeid = Artikkel.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Artikkel.objects.all().\
            aggregate(
            max_inp_date=Max('inp_date'),
            max_mod_date=Max('mod_date')
        )
        a['viimane_lisatud'] = Artikkel.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Artikkel.objects.filter(mod_date=kp['max_mod_date'])[0]
        # Samal kuupäeval erinevatel aastatel toimunud
        sel_p2eval = Artikkel.objects.filter(
            hist_date__day = p2ev,
            hist_date__month = kuu
        )
        sel_p2eval_kirjeid = len(sel_p2eval)
        if sel_p2eval_kirjeid > 5: # Kui leiti rohkem kui viis kirjet võetakse 2 algusest + 1 keskelt + 2 lõpust
            a['sel_p2eval'] = sel_p2eval[:2] + sel_p2eval[int(sel_p2eval_kirjeid/2-1):int(sel_p2eval_kirjeid/2)] + sel_p2eval[sel_p2eval_kirjeid-2:]
        else:
            a['sel_p2eval'] = sel_p2eval
        a['sel_p2eval_kirjeid'] = sel_p2eval_kirjeid
        # Samal päeval ja kuul toimunud
        sel_kuul = Artikkel.objects.filter(hist_searchdate__month = kuu)
        sel_kuul_kirjeid = len(sel_kuul)
        if sel_kuul_kirjeid > 5: # Kui leiti rohkem kui viis kirjet võetakse 2 algusest + 1 keskelt + 2 lõpust
            a['sel_kuul'] = sel_kuul[:2] + sel_kuul[int(sel_kuul_kirjeid/2-1):int(sel_kuul_kirjeid/2)] + sel_kuul[sel_kuul_kirjeid-2:]
        else:
            a['sel_kuul'] = sel_kuul
        a['sel_kuul_kirjeid'] = sel_kuul_kirjeid
    andmed['artikkel'] = a

    # Andmebaas Isik andmed veebi
    a = dict()
    kirjeid = Isik.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Isik.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        a['viimane_lisatud'] = Isik.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Isik.objects.filter(mod_date=kp['max_mod_date'])[0]
        a['sel_p2eval'] = Isik.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Isik.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        a['sel_p2eval_surnud'] = Isik.objects.filter(hist_enddate__day = p2ev, hist_enddate__month = kuu)
        a['sel_p2eval_surnud_kirjeid'] = len(a['sel_p2eval_surnud'])
        a['sel_kuul_surnud'] = Isik.objects.filter(hist_enddate__month = kuu).order_by('hist_enddate__day')
        a['sel_kuul_surnud_kirjeid'] = len(a['sel_kuul_surnud'])
        juubilarid = Isik.objects.exclude(hist_date=None).annotate(
            nulliga=ExpressionWrapper(
                (datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
            vanus_gen=ExpressionWrapper(
                    datetime.date.today().year - ExtractYear('hist_date'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        a['juubilarid'] = juubilarid
    andmed['isik'] = a

    # Andmebaas Organisatsioon andmed veebi
    a = dict()
    kirjeid = Organisatsioon.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Organisatsioon.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        a['viimane_lisatud'] = Organisatsioon.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Organisatsioon.objects.filter(mod_date=kp['max_mod_date'])[0]
        a['sel_p2eval'] = Organisatsioon.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Organisatsioon.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = Organisatsioon.objects.exclude(hist_year=None).annotate(
            nulliga=ExpressionWrapper(
                (datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()), vanus_gen=ExpressionWrapper(
                    datetime.date.today().year - F('hist_year'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        a['juubilarid'] = juubilarid
    andmed['organisatsioon'] = a
    
    # Andmebaas Objekt andmed veebi
    a = dict()
    kirjeid = Objekt.objects.count()
    a['kirjeid'] = kirjeid
    if kirjeid > 0:
        kp = Objekt.objects.all().aggregate(max_inp_date=Max('inp_date'), max_mod_date=Max('mod_date'))
        a['viimane_lisatud'] = Objekt.objects.filter(inp_date=kp['max_inp_date'])[0]
        a['viimane_muudetud'] = Objekt.objects.filter(mod_date=kp['max_mod_date'])[0]
        a['sel_p2eval'] = Objekt.objects.filter(hist_date__day = p2ev, hist_date__month = kuu)
        a['sel_p2eval_kirjeid'] = len(a['sel_p2eval'])
        a['sel_kuul'] = Objekt.objects.filter(hist_date__month = kuu).order_by('hist_date__day')
        a['sel_kuul_kirjeid'] = len(a['sel_kuul'])
        juubilarid = Objekt.objects.exclude(hist_year=None).annotate(
            nulliga=ExpressionWrapper(
                (datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()), vanus_gen=ExpressionWrapper(
                    datetime.date.today().year - F('hist_year'), output_field=IntegerField())).filter(nulliga=0).order_by('-vanus_gen')
        a['juubilarid'] = juubilarid
    andmed['objekt'] = a
    
    return render(request, 'wiki/wiki.html', {'andmed': andmed})


#
# Kuupäeva väljalt võetud andmete põhjal suunatakse kuupäevavaatesse
#
def mine_krono_kp(request):
    if not (request.method == 'POST' and check_recaptcha(request)):
        return redirect('wiki:info')

    kuup2ev = request.POST.get('kuup2ev').split('-')

    return HttpResponseRedirect(
        reverse(
            'wiki:artikkel_day_archive',
            kwargs={'year': kuup2ev[0], 'month': kuup2ev[1], 'day': kuup2ev[2]})
        )

def mis_kuul(kuu, l6pp='s'):
    kuud = ['jaanuari',
            'veebruari',
            'märtsi',
            'aprilli',
            'mai',
            'juuni',
            'juuli',
            'augusti',
            'septembri',
            'oktoobri',
            'novembri',
            'detsembri'
            ]
    return kuud[kuu - 1] + l6pp


def mainitud_aastatel(model, obj):
    # Artiklites mainimine läbi aastate
    if model == 'Isik':
        qs = Artikkel.objects.filter(isikud__id=obj.id)
    elif model == 'Objekt':
        qs = Artikkel.objects.filter(objektid__id=obj.id)
    elif model == 'Organisatsioon':
        qs = Artikkel.objects.filter(organisatsioonid__id=obj.id)

    aastad = list(qs.all().values_list('hist_year', flat=True).distinct())
    if obj.hist_date:
        synniaasta = obj.hist_date.year
    elif obj.hist_year:
        synniaasta = obj.hist_year
    else:
        synniaasta = None
    if synniaasta:
        aastad.append(synniaasta)
    if obj.hist_enddate:
        surmaaasta = obj.hist_enddate.year
    elif obj.hist_year:
        surmaaasta = obj.hist_endyear
    else:
        surmaaasta = None
    if surmaaasta:
        aastad.append(surmaaasta)
    aastad = Counter(aastad)  # loetleme kõik aastad ja mainimised

    return dict(
        OrderedDict(
            sorted(
                aastad.items(), key=lambda t: t[0]
            )
        )
    )
#
# Artikli vaatamiseks
#
class ArtikkelDetailView(generic.DetailView):
    model = Artikkel
    template_name = 'wiki/artikkel_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Kas artiklile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            artiklid__id=self.object.id).filter(profiilipilt_artikkel=True).first()
        kuup2ev = context['artikkel'].hist_searchdate
        obj_id = context['artikkel'].id
        # Järjestame artiklid kronoloogiliselt
        loend = Artikkel.objects.order_by('hist_searchdate', 'id').values('id')
        # Leiame valitud artikli järjekorranumbri
        n = next((i for i, x in enumerate(loend) if x['id'] == obj_id), -1)
        context['n'] = n
        if n > -1:
            # Leiame ajaliselt järgneva artikli
            if n < Artikkel.objects.count() - 1:
                context['next_obj'] = Artikkel.objects.get(id=loend[n+1]['id'])
            # Leiame ajaliselt eelneva artikli
            if n > 0:
                context['prev_obj'] = Artikkel.objects.get(id=loend[n-1]['id'])
        # Lisame vihjevormi
        context['feedbackform'] = VihjeForm()
        return context

    def get_object(self):
        obj = super().get_object()
        # Record the last accessed date
        obj.last_accessed = timezone.now()
        obj.total_accessed += 1
        obj.save()
        return obj

#
# Artikli muutmiseks
#
class ArtikkelUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Artikkel
    pk_url_kwarg = 'pk'

    form_class = ArtikkelForm

    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_artikkel_detail', pk=self.object.id)


class IsikUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Isik
    pk_url_kwarg = 'pk'
    form_class = IsikForm
    
    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_isik_detail', pk=self.object.id)


class OrganisatsioonUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Organisatsioon
    form_class = OrganisatsioonForm
    pk_url_kwarg = 'pk'

    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_organisatsioon_detail', pk=self.object.id)
    
class ObjektUpdate(LoginRequiredMixin, UpdateView):
    redirect_field_name = 'next'
    model = Objekt
    form_class = ObjektForm
    pk_url_kwarg = 'pk'

    def form_valid(self, form):
        objekt = form.save(commit=False)
        # Lisaja/muutja andmed
        if not objekt.id:
            objekt.created_by = self.request.user
        else:
            objekt.updated_by = self.request.user
        # Täidame tühjad kuupäevaväljad olemasolevate põhjal
        if objekt.hist_date:
            objekt.hist_year = objekt.hist_date.year
            objekt.hist_month = objekt.hist_date.month
            objekt.hist_searchdate = objekt.hist_date
        else:
            if objekt.hist_year:
                y = objekt.hist_year
                if objekt.hist_month:
                    m = objekt.hist_month
                else:
                    m = 1
                objekt.hist_searchdate = datetime.datetime(y, m, 1)
            else:
                objekt.hist_searchdate = None
        if objekt.hist_enddate:
            objekt.hist_endyear = objekt.hist_enddate.year
        objekt.save()
        form.save_m2m()
        return redirect('wiki:wiki_objekt_detail', pk=self.object.id)

#
# Artiklite otsimise/filtreerimise seaded
#
class ArtikkelFilter(django_filters.FilterSet):
    
    class Meta:
        model = Artikkel
        fields = {
            'hist_year': ['exact'],
            'body_text': ['icontains'],
            'isikud__perenimi': ['icontains'],
            }

    def __init__(self, *args, **kwargs):
        super(ArtikkelFilter, self).__init__(*args, **kwargs)
        # at startup user doen't push Submit button, and QueryDict (in data) is empty
        if self.data == {}:
            self.queryset = self.queryset.none()


#
# Artiklite otsimise/filtreerimise vaade
#
class ArtikkelFilterView(FilterView):
    model = Artikkel
    paginate_by = 10
    template_name = 'wiki/artikkel_filter.html'
    filterset_fields = {
            'hist_year',
            'body_text',
            'isikud__perenimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        list = Artikkel.objects.all().order_by('hist_searchdate')
        filter = ArtikkelFilter(self.request.GET, queryset=list)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            artiklid = paginator.page(page)
        except PageNotAnInteger:
            artiklid = paginator.page(1)
        except EmptyPage:
            artiklid = paginator.page(paginator.num_pages)
        context['object_list'] = artiklid
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
            

#
# Kronoloogia
#
class ArtikkelArchiveIndexView(ArchiveIndexView):
    queryset = Artikkel.objects.all()
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    paginate_by = 20
    ordering = ('hist_searchdate', 'id')

class ArtikkelYearArchiveView(YearArchiveView):
    queryset = Artikkel.objects.all()
    date_field = "hist_searchdate"
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 20
    ordering = ('hist_searchdate', 'id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aasta = context['year'].year
        # Eelnev ja järgnev artikleid sisaldav aasta
        context['aasta_eelmine'] = Artikkel.objects.filter(hist_year__lt=aasta).aggregate(Max('hist_year'))['hist_year__max']
        context['aasta_j2rgmine'] = Artikkel.objects.filter(hist_year__gt=aasta).aggregate(Min('hist_year'))['hist_year__min']
        
        # Leiame samal aastal sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__year = aasta).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. aastal sündinud isikud'.format(aasta)
        # Leiame samal aastal surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__year = aasta).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. aastal surnud isikud'.format(aasta)
        # Leiame samal aastal loodud organisatsioonid
        loodud_organisatsioonid = (
            Organisatsioon.objects.filter(hist_date__year = aasta) | Organisatsioon.objects.filter(hist_year = aasta)).distinct().annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - F('hist_year'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. aastal loodud organisatsioonid'.format(aasta)
        # Leiame samal aastal avatud objektid
        valminud_objektid = (
            Objekt.objects.filter(hist_date__year = aasta) | Objekt.objects.filter(hist_year = aasta)).distinct().annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. aastal valminud objektid'.format(aasta)
        
        return context


class ArtikkelMonthArchiveView(MonthArchiveView):
    queryset = Artikkel.objects.all()
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    paginate_by = 10
    ordering = ('hist_searchdate', 'id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aasta = context['month'].year
        kuu = context['month'].month
        p2ev = context['month']
        # Leiame samal kuul teistel aastatel märgitud artiklid
        sel_kuul = Artikkel.objects.exclude(hist_searchdate__year = aasta).filter(hist_searchdate__month = kuu)
        context['sel_kuul'] = sel_kuul
        # Leiame samal kuul sündinud isikud
        syndinud_isikud = Isik.objects.filter(
            hist_date__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0} sündinud isikud'.format(mis_kuul(kuu))
        # Leiame samal kuul surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(p2ev.year - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0} surnud isikud'.format(mis_kuul(kuu))
        # Leiame samal kuul loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0} loodud organisatsioonid'.format(mis_kuul(kuu))
        # Leiame samal kuul avatud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0} valminud objektid'.format(mis_kuul(kuu))
        return context
    
class ArtikkelDayArchiveView(DayArchiveView):
    queryset = Artikkel.objects.all()
    date_field = 'hist_searchdate'
    make_object_list = True
    allow_future = True
    allow_empty = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aasta = context['day'].year
        kuu = context['day'].month
        p2ev = context['day'].day
        # Leiame samal kuupäeval teistel aastatel märgitud artiklid
        sel_p2eval = Artikkel.objects.exclude(hist_searchdate__year = aasta).filter(hist_date__month = kuu, hist_date__day = p2ev)
        context['sel_p2eval'] = sel_p2eval
        # Leiame samal kuupäeval sündinud isikud
        syndinud_isikud = Isik.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['syndinud_isikud'] = syndinud_isikud
        context['syndinud_isikud_pealkiri'] = '{0}. {1} sündinud isikud'.format(p2ev, mis_kuul(kuu, 'l'))
        # Leiame samal kuupäeval surnud isikud
        surnud_isikud = Isik.objects.filter(hist_enddate__month = kuu, hist_enddate__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['surnud_isikud'] = surnud_isikud
        context['surnud_isikud_pealkiri'] = '{0}. {1} surnud isikud'.format(p2ev, mis_kuul(kuu, 'l'))
        # Leiame samal kuupäeval loodud organisatsioonid
        loodud_organisatsioonid = Organisatsioon.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['loodud_organisatsioonid'] = loodud_organisatsioonid
        context['loodud_organisatsioonid_pealkiri'] = '{0}. {1} loodud organisatsioonid'.format(p2ev, mis_kuul(kuu, 'l'))
        # Leiame samal kuupäeval loodud objektid
        valminud_objektid = Objekt.objects.filter(hist_date__month = kuu, hist_date__day = p2ev).annotate(
                nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField()),
                vanus_gen=ExpressionWrapper(aasta - ExtractYear('hist_date'), output_field=IntegerField()))
        context['valminud_objektid'] = valminud_objektid
        context['valminud_objektid_pealkiri'] = '{0}. {1} valminud objektid'.format(p2ev, mis_kuul(kuu, 'l'))
        
        return context

#
# Isikute otsimiseks/filtreerimiseks
#
class IsikFilter(django_filters.FilterSet):
    
    class Meta:
        model = Isik
        fields = {
            'eesnimi': ['icontains'],
            'perenimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(IsikFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()


class IsikFilterView(FilterView):
    model = Isik
    paginate_by = 20
    template_name = 'wiki/isik_filter.html'
    filterset_fields = {
            'eesnimi',
            'perenimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        list = Isik.objects.all().annotate(
            nulliga=ExpressionWrapper((datetime.date.today().year - ExtractYear('hist_date'))%5, output_field=IntegerField())).order_by('perenimi')
        filter = IsikFilter(self.request.GET, queryset=list)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            isikud = paginator.page(page)
        except PageNotAnInteger:
            isikud = paginator.page(1)
        except EmptyPage:
            isikud = paginator.page(paginator.num_pages)
        context['object_list'] = isikud
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
    

def seotud_isikud_artiklikaudu(seotud_artiklid, isik_ise):
    # Isikuga artiklite kaudu seotud teised isikud
    isikud = Isik.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().all().exclude(pk=isik_ise)
    andmed = {}
    for seotud_isik in isikud:
        kirje = {}
        kirje['id'] = seotud_isik.id
        kirje['perenimi'] = seotud_isik.perenimi
        kirje['eesnimi'] = seotud_isik.eesnimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(isikud=seotud_isik).\
            order_by('hist_searchdate').\
            values('id', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_isik.id] = kirje
    return andmed
        

class IsikDetailView(generic.DetailView):
    model = Isik

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Kas isikule on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            isikud__id=self.object.id).filter(profiilipilt_isik=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel('Isik', self.object)

        # Isikuga seotud artiklid
        seotud_artiklid = Artikkel.objects.filter(isikud__id=self.object.id)
        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        context['feedbackform'] = VihjeForm()
        return context


#
# Organisatsioonide otsimiseks/filtreerimiseks
#
class OrganisatsioonFilter(django_filters.FilterSet):
    
    class Meta:
        model = Organisatsioon
        fields = {
            'nimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(OrganisatsioonFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()


class OrganisatsioonFilterView(FilterView):
    model = Organisatsioon
    paginate_by = 20
    template_name = 'wiki/organisatsioon_filter.html'
    filterset_fields = {
            'nimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        list = Organisatsioon.objects.all().annotate(
            nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField())).order_by('nimi')
        filter = OrganisatsioonFilter(self.request.GET, queryset=list)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            organisatsioonid = paginator.page(page)
        except PageNotAnInteger:
            organisatsioonid = paginator.page(1)
        except EmptyPage:
            organisatsioonid = paginator.page(paginator.num_pages)
        context['object_list'] = organisatsioonid
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
    
def seotud_organisatsioonid_artiklikaudu(seotud_artiklid, organisatsiooni_ise):
    # Isikuga artiklite kaudu seotud organisatsioonid
    organisatsioonid = Organisatsioon.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().all().exclude(pk=organisatsiooni_ise)
    andmed = {}
    for seotud_organisatsioon in organisatsioonid:
        kirje = {}
        kirje['id'] = seotud_organisatsioon.id
        kirje['nimi'] = seotud_organisatsioon.nimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(organisatsioonid=seotud_organisatsioon).\
            order_by('hist_searchdate').\
            values('id', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_organisatsioon.id] = kirje
    return andmed


class OrganisatsioonDetailView(generic.DetailView):
    model = Organisatsioon

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Kas organisatsioonile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            organisatsioonid__id=self.object.id).filter(profiilipilt_organisatsioon=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel('Organisatsioon', self.object)

        # Organisatsiooniga seotud artiklid
        seotud_artiklid = Artikkel.objects.filter(organisatsioonid__id=self.object.id)

        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        context['feedbackform'] = VihjeForm()
        return context


#
# Objektide otsimiseks/filtreerimiseks
#
class ObjektFilter(django_filters.FilterSet):
    
    class Meta:
        model = Objekt
        fields = {
            'nimi': ['icontains'],
            }

##    def __init__(self, *args, **kwargs):
##        super(ObjektFilter, self).__init__(*args, **kwargs)
##        # at startup user doen't push Submit button, and QueryDict (in data) is empty
##        if self.data == {}:
##            self.queryset = self.queryset.none()


class ObjektFilterView(FilterView):
    model = Objekt
    paginate_by = 20
    template_name = 'wiki/objekt_filter.html'
    filterset_fields = {
            'nimi',
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        list = Objekt.objects.all().annotate(
            nulliga=ExpressionWrapper((datetime.date.today().year - F('hist_year'))%5, output_field=IntegerField())).order_by('nimi')
        filter = ObjektFilter(self.request.GET, queryset=list)
        list = filter.qs

        paginator = Paginator(list, self.paginate_by)
        page = self.request.GET.get('page', 1)
        try:
            objektid = paginator.page(page)
        except PageNotAnInteger:
            objektid = paginator.page(1)
        except EmptyPage:
            objektid = paginator.page(paginator.num_pages)
        context['object_list'] = objektid
        context['kirjeid'] = len(list)
        context['filter'] = filter
        return context
    
def seotud_objektid_artiklikaudu(seotud_artiklid, objekt_ise):
    # Objektiga artiklite kaudu seotud organisatsioonid
    objektid = Objekt.objects.filter(artikkel__pk__in=seotud_artiklid).distinct().all().exclude(pk=objekt_ise)
    andmed = {}
    for seotud_objekt in objektid:
        kirje = {}
        kirje['id'] = seotud_objekt.id
        kirje['nimi'] = seotud_objekt.nimi
        kirje['artiklid'] = seotud_artiklid.\
            filter(objektid=seotud_objekt).\
            order_by('hist_searchdate').\
            values('id', 'body_text', 'hist_date', 'hist_year', 'hist_month', 'hist_enddate')
        andmed[seotud_objekt.id] = kirje
    return andmed
    
class ObjektDetailView(generic.DetailView):
    model = Objekt

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Kas objektile on määratud profiilipilt
        context['profiilipilt'] = Pilt.objects.filter(
            objektid__id=self.object.id).filter(profiilipilt_objekt=True).first()

        # Mainimine läbi aastate
        context['mainitud_aastatel'] = mainitud_aastatel('Objekt', self.object)

        # Objektiga seotud artiklid
        seotud_artiklid = Artikkel.objects.filter(objektid__id=self.object.id)
        context['seotud_artiklid'] = seotud_artiklid
        context['seotud_isikud_artiklikaudu'] = seotud_isikud_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_organisatsioonid_artiklikaudu'] = seotud_organisatsioonid_artiklikaudu(seotud_artiklid, self.object.id)
        context['seotud_objektid_artiklikaudu'] = seotud_objektid_artiklikaudu(seotud_artiklid, self.object.id)

        # Lisame vihjevormi
        context['feedbackform'] = VihjeForm()
        return context


# Loendab kõik sisse logitud kasutajad
def get_all_logged_in_users():
    # Query all non-expired sessions
    # use timezone.now() instead of datetime.now() in latest versions of Django
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = []

    # Build a list of user ids from that query
    for session in sessions:
        data = session.get_decoded()
        uid_list.append(data.get('_auth_user_id', None))

    # Query all logged in users based on id list
    return User.objects.filter(id__in=uid_list)
