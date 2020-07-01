from configparser import ConfigParser
from datetime import datetime, timedelta
import json
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

# postgresql andmebaasi lugemiseks seadete lugemine .ini failist
# The following config() function read the database.ini file and returns the connection parameters.
def config(path='', filename='utils/database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(os.path.join(path, filename))
    # get section, default to postgresql
    db_config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_config[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return db_config

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
    # yr['forecast'] = {}
    cat = []
    dt = []
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
        dt.append(datetime.timestamp(date))
        if date.hour == 0:
            dateticks.append(n)
        cat.append(date) # Aeg
        # Sademed
        prec_value = float(data.find("precipitation").attrib['value'])
        try:
            prec_maxvalue = float(data.find("precipitation").attrib['maxvalue'])
            prec_minvalue = float(data.find("precipitation").attrib['minvalue'])
        except:
            prec_minvalue = prec_maxvalue = prec_value

        prec.append([prec_value, prec_minvalue, prec_maxvalue]) # Sademed
        wind.append(
            [float(data.find("windSpeed").attrib['mps']),
            float(data.find("windDirection").attrib['deg'])]
        )
        temp.append(float(data.find("temperature").attrib['value'])) # Temperatuur
        pres.append(float(data.find("pressure").attrib['value'])) # Õhurõhk
        symb.append(data.find("symbol").attrib['var']) # Ilmasümboli kood (YR)
    yr['forecast'] = {
        'start': cat[0], # Mis kellast prognoos algab
        'temperatures': temp,
        'windbarbs': wind,
        'airpressures': pres,
        'precipitations': prec,
        'symbols': symb,
        'dt': dt,
    }
    return yr

def owm_onecall():
    # api_key = settings.OWM_APIKEY
    api_config = config(os.getcwd(), 'ilm/utils/owm.ini', 'OWM')
    api_key = api_config['owm_apikey']
    city_id = 587876  # Valga
    lon = '26.05'
    lat = '57.78'
    owm_url = 'https://api.openweathermap.org/data/2.5/'

    # Hetkeandmed ja prognoos
    params = {
        'lat': lat,
        'lon': lon,
        'appid': api_key,
        'units': 'metric',
    }
    resp = requests.get(
        owm_url + 'onecall',
        # headers=headers,
        params=params
    )
    weather = json.loads(resp.text)

    # Ajalugu
    now = datetime.now()
    dt = int(datetime.timestamp(datetime(now.year, now.month, now.day, now.hour)))
    params['dt'] = dt
    resp = requests.get(
        owm_url + 'onecall/timemachine',
        # headers=headers,
        params=params
    )
    weather['history'] = json.loads(resp.text)

    if weather:
        # weather['current']['datetime'] = datetime.fromtimestamp(weather['current']['dt'], timezone.utc)
        weather['current']['kirjeldus'] = OWM_CODES.get(
            str(weather['current']['weather'][0]['id']),
            weather['current']['weather'][0]['description']
        )
        for hour in weather['hourly']:
            # hour['datetime'] = datetime.fromtimestamp(hour['dt'], timezone.utc)
            hour['kirjeldus'] = OWM_CODES.get(
                str(hour['weather'][0]['id']),
                hour['weather'][0]['description']
            )
        for day in weather['daily']:
            # day['datetime'] = datetime.fromtimestamp(day['dt'], timezone.utc)
            day['kirjeldus'] = OWM_CODES.get(
                str(day['weather'][0]['id']),
                day['weather'][0]['description']
            )
        weather['history']['hourly3h'] = weather['history']['hourly'][-3:]  # viimased kolm tundi
        for hour in weather['history']['hourly']:
            # hour['datetime'] = datetime.fromtimestamp(hour['dt'], timezone.utc)
            hour['kirjeldus'] = OWM_CODES.get(
                str(hour['weather'][0]['id']),
                hour['weather'][0]['description']
            )
    return weather
