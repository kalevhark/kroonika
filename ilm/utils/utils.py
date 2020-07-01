from datetime import datetime, timedelta
import os
import re
import sys
import xml.etree.ElementTree as ET

from urllib.request import Request, urlopen
from urllib.error import URLError

from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor
from pytz import timezone
import pytz
import requests

# Teisendab UTC -> Eesti aeg
def utc2eesti_aeg(dt):
    eesti_aeg = timezone('Europe/Tallinn')
    return dt.astimezone(eesti_aeg)

# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return float(value)
    except:
        return None

# Ilmateenistuse viimase mõõtmise andmed veebist
def ilm_praegu():
    jaam = 'Valga'
    href = 'http://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
    r = requests.get(href)
    root = ET.fromstring(r.text)
    i = dict()
    # Mõõtmise aeg
    dt = datetime.fromtimestamp(int(root.attrib['timestamp']))
    i['timestamp'] = pytz.timezone('Europe/Tallinn').localize(dt)
    station = root.findall("./station/[name='"+jaam+"']")
    for el in station:
        for it in el:
            data = it.text
            # Kui ei ole tekstiväli, siis teisendame float tüübiks
            if it.tag not in ['name',
                              'station',
                              'phenomenon',
                              'phenomenon_observer']:
                data = float_or_none(data)
            i[it.tag] = data
    return i

# Ilmateenistuse etteantud täistunni mõõtmise andmed veebist
def ilmaandmed_veebist(dt):
    """
    Tagastab etteantud ajahetke (d) viimase möödunud täistunni ilmaandmed
    ilmateenistus.ee veebilehelt
    """
    jaam = 'Valga'
    cols = ['airtemperature',
            'relativehumidity',
            'airpressure',
            'airpressure_delta',
            'winddirection',
            'windspeed',
            'windspeedmax',
            'cloudiness',
            'phenomenon',
            'phenomenon_observer',
            'precipitations',
            'visibility']
    href = 'http://ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/tunniandmed/'
    dt = utc2eesti_aeg(dt)
    p2ev = dt.strftime("%d.%m.%Y")
    tund = dt.strftime("%H")
    # Päringu aadress
    p2ring = ''.join(
        [href,
         '?filter[date]=',
         p2ev,
         '&filter[hour]=',
         tund]
    )
    andmed = dict()
    # Loeme veebist andmed
    req = Request(p2ring, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urlopen(req).read()
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
    else:
        # Struktueerime
        soup = BeautifulSoup(response, 'html.parser')
        kontroll_hour = soup.find(attrs={"name": "filter[hour]"})
        kontroll_date = soup.find(attrs={"name": "filter[date]"})
        if kontroll_hour:
            if kontroll_hour['value'].zfill(2) != tund.zfill(2) or kontroll_date['value'] != p2ev:
                print(dt, 'Vale!')
                # Kui vastus vale kellaajaga või kuupäevaga, saadame tagasi tühja tabeli
                return andmed
        # Leiame lehelt tabeli
        table = soup.table
        # Leiame tabelist rea
        row = table.find(string=re.compile(jaam))
        data = row.find_parent().find_next_siblings()
        for i in range(len(data)):
            if data[i]: # kui andmeväli pole tühi
                if cols[i] in ['phenomenon', 'phenomenon_observer']: # tekstiväli
                    andmed[cols[i]] = data[i].text.strip()
                else: # numbriväli
                    value = data[i].text.strip().replace(',', '.')
                    andmed[cols[i]] = float_or_none(value)
            else:
                andmed[cols[i]] = None

        # andmed['station'] = Jaam.objects.filter(name=jaam).first()
        andmed['station_id'] = 1
        andmed['timestamp'] = pytz.timezone('Europe/Tallinn').localize(
            datetime(dt.year, dt.month, dt.day, dt.hour))
        # Ilmaandmed andmebaasi juhul kui põhiandmed olemas
        # if andmed['airtemperature'] != None:
        #     i = Ilm(**andmed)
        #     i.save()
        #     print('Salvestan andmebaasi:', d)
    return andmed
