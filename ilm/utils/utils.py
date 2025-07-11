import calendar
from configparser import ConfigParser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json

import locale
locale.setlocale(locale.LC_NUMERIC, "et_EE.UTF-8")

import os
import re
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from astral import LocationInfo, moon
from astral.sun import sun

from bs4 import BeautifulSoup

import django
from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()

# try:
#     from django.core.cache import cache
#     from django.core.serializers.json import DjangoJSONEncoder
# except:
#     pass

import pytz
import redis
import requests

if settings.REDIS_INUSE:
    redis_client = redis.Redis(host=settings.REDIS_HOST, port=6379, db=0)

from ilm.models import Ilm
import ilm.utils.ephem_util as ephem_data

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

# Teisendab noTZ -> Eesti aeg
def utc2eesti_aeg(dt):
    eesti_aeg = pytz.timezone('Europe/Tallinn')
    return dt.astimezone(eesti_aeg)

# Decimal andmeväljade teisendamiseks, mis võivad olla tühjad <NULL>
def float_or_none(value):
    try:
        return locale.atof(value)
    except:
        return None

# tagastab kuu viimase pühapäeva UTC
def last_sunday(year, month):
    last_sunday = max(week[-1] for week in calendar.monthcalendar(year, month))
    return pytz.utc.localize(datetime(year, month, last_sunday))

def sun_moon(dt):
    # Tagastab konkreetese kuupäeva (ajavööndi väärtusega) päikese- ja kuuandmed
    tallinn_tz = ZoneInfo('Europe/Tallinn')
    city = LocationInfo("Valga", "Estonia", "Europe/Tallinn", 57.776944, 26.031111)
    s = {}
    sun_states = sun(city.observer, dt)
    for state in sun_states.keys():
        sun_states[state] = sun_states[state].astimezone(tallinn_tz)
    s['sun'] = sun_states
    s['moon'] = moon.phase(date=dt)
    return s

def ilman2htus_yrnosymboliks(phenomenon, dt):
    """
    Tagastab symboli väärtuse vastavalt tabelile:
    https://cdn.jsdelivr.net/gh/YR/weather-symbols@7.0.0/dist/svg/
    prognoosi sümbolile lisatakse vastavalt päeva- või ööajale 'd' või 'n'
    """
    if phenomenon == None:
        # return None
        phenomenon = 'nähtusteta'
    phenomenon = phenomenon.lower()
    phenomenons = {
        'clear': '01',
        'selge': '01',
        'nähtusteta': '01',
        'few clouds': '02',
        'vähene pilvisus': '02',
        'variable clouds': '03',
        'poolpilves': '03',
        'cloudy with clear spells': '03',
        'peamiselt pilves': '03',
        'cloudy': '04',
        'pilves': '04',
        'light snow shower': '44',
        'nõrk hooglumi': '44',
        'moderate snow shower': '08',
        'mõõdukas hooglumi': '08',
        'heavy snow shower': '45',
        'tugev hooglumi': '08',
        'light shower': '46',
        'nõrk hoogvihm': '46',
        'moderate shower': '09',
        'mõõdukas hoogvihm': '09',
        'heavy shower': '10',
        'tugev hoogvihm': '10',
        'uduvihm': '46',
        'light rain': '46',
        'nõrk vihm': '46',
        'moderate rain': '09',
        'mõõdukas vihm': '09',
        'vihm': '09',
        'heavy rain': '10',
        'tugev vihm': '10',
        'glaze': '15',
        'jäide': '15',
        'jäätuv uduvihm': '15',
        'jääkruubid': '15',
        'light sleet': '47',
        'nõrk lörtsisadu': '47',
        'nõrk vihm koos lumega': '47',
        'sademed': '47',
        'moderate sleet': '12',
        'mõõdukas lörtsisadu': '12',
        'light snowfall': '44',
        'nõrk lumesadu': '44',
        'nõrk lumi': '44',
        'moderate snowfall': '08',
        'mõõdukas lumesadu': '08',
        'lumi': '08',
        'heavy snowfall': '45',
        'tugev lumesadu': '45',
        'blowing snow': '45',
        'üldtuisk': '45',
        'drifting snow': '44',
        'pinnatuisk': '44',
        'hail': '48',
        'rahe': '48',
        'mist': '15',
        'uduvine': '15',
        'fog': '15',
        'udu': '15',
        'thunder': '06',
        'äike': '06',
        'thunderstorm': '25',
        'äikesevihm': '25'
    }
    if phenomenon in phenomenons:
        symbol = phenomenons[phenomenon]
    else:
        symbol = None
    # Kas lisada d või n vastavalt valgele või pimedale ajale
    if symbol == None or symbol in [
            '04', '09', '10', '11', '12', '13', '14', '15',
            '22', '23', '30', '31', '32', '33', '34',
            '46', '47', '48', '49', '50'
            ]:
        return symbol
    sun = sun_moon(dt)['sun']
    if dt > sun['sunrise'] and dt < sun['sunset']:
        symbol = symbol + 'd'
    else:
        symbol = symbol + 'n'
    return symbol

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
    # href = 'http://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
    href = 'https://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
    r = requests.get(href)
    try:
        root = ET.fromstring(r.text)
    except:
        # Kontrollime kas vaatlusandmed ikkagi olemas
        observation_exists = r.text.find('<observations')
        if observation_exists > 0:
            root = ET.fromstring(r.text[observation_exists:])
        else:
            return None
    # Leiame xmlist Valga andmed
    station = root.findall("./station/[name='" + jaam + "']")
    i = dict()
    # Mõõtmise aeg
    dt = datetime.fromtimestamp(int(root.attrib['timestamp']))
    i['timestamp'] = pytz.timezone('Europe/Tallinn').localize(dt)

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
    i['symbol'] = ilman2htus_yrnosymboliks(i['phenomenon'], i['timestamp'])
    return i

# Ilmateenistuse veebist tunni max+min andmed
def get_maxmin_airtemperature(dt_utc):
    dt_loc = utc2eesti_aeg(dt_utc)
    p2ev = dt_loc.strftime("%d.%m.%Y")
    tund = dt_loc.strftime("%H")

    # url = 'https://www.ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/maxmin-ohutemp/'
    url = 'https://vana.ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/maxmin-ohutemp/'
    params = {
        'lang': 'et',
        r'filter%5BmaxDate%5D': p2ev,
        r'filter%5BminDate%5D': p2ev,
        r'filter%5Bdate%5D': p2ev,
        r'filter%5Bhour%5D': tund
    }
    headers = {'User-Agent': 'Mozilla/5.0'}

    maxmin_data = dict()
    try:
        r = requests.get(
            url=url,
            params=params,
            headers=headers
        )

        # print(r.status_code, r.text.find('Valga'))
        soup = BeautifulSoup(r.text, 'html.parser')

        tables = soup.find_all('table')
        for table in tables:
            if table.thead.get_text().find('Maksimaalne') > 0:
                trs = table.tbody.find_all('tr')
                for tr in trs:
                    if tr.text.find('Valga') > 0:
                        weather_data = tr.find_all('td')
                        maxmin_data['airtemperature_max'] = float_or_none(
                            weather_data[1]
                                .text
                                .strip()
                                .replace(',', '.')
                        )
                        maxmin_data['airtemperature_min'] = float_or_none(
                            weather_data[2]
                                .text
                                .strip()
                                .replace(',', '.')
                        )
                        break
    except Exception as error:
        print(error)
    return maxmin_data

# Ilmateenistuse etteantud täistunni mõõtmise andmed APIst
# https://ilmmicroservice.envir.ee/api_doc/
def ilmaandmed_apist(dt, verbose=False):
    """
    Tagastab etteantud dt (aware v6i naive) viimase möödunud täistunni ilmaandmed
    ilmateenistus.ee veebilehelt
    """
    if dt.tzinfo == None:
        aware_from_dt = dt.astimezone(tz=ZoneInfo('Europe/Tallinn'))
    else:
        aware_from_dt = dt
    
    jaam = 'Valga'
    # NB! päringuks vajalik UTC aeg
    utc_datetime = aware_from_dt.astimezone(timezone.utc)

    url_observation_data_hourly = "https://publicapi.envir.ee/v1/combinedWeatherData/observationDataHourly"
    url_observation_temperature_extremums = "https://publicapi.envir.ee/v1/temperature/observationTemperatureExtremums" # temp min max

    headers = {"accept": "application/json"}
    payload = {
        'date': utc_datetime.strftime("%Y-%m-%d"),
        'hour': utc_datetime.strftime("%H")
    }
    
    response = requests.get(
        url_observation_data_hourly, 
        headers=headers,
        params=payload
    )
    data = response.json()
    
    entries = data['entries']['entry']
    entries_filtered = [entry for entry in entries if entry.get('Jaam') == jaam]
    data_observation_data_hourly = entries_filtered[0]
    if verbose:
        print(data_observation_data_hourly)

    response = requests.get(
        url_observation_temperature_extremums, 
        headers=headers,
        params=payload
    )
    data = response.json()

    entries = data['entries']['entry']
    entries_filtered = [entry for entry in entries if entry.get('Jaam') == jaam]
    data_observation_temperature_extremums = entries_filtered[0]
    if verbose:
        print(data_observation_temperature_extremums)
    
    ilmaandmed = {}
    ilmaandmed['airtemperature'] = float_or_none(data_observation_data_hourly['tains']) # Õhutemperatuur, 1 m keskmine
    ilmaandmed['relativehumidity'] = float_or_none(data_observation_data_hourly['rhins']) # Suhteline õhuniiskus
    ilmaandmed['airpressure'] = float_or_none(data_observation_data_hourly['qffins']) # Õhurõhk merepinnal
    ilmaandmed['airpressure_delta'] = float_or_none(data_observation_data_hourly['qffmuutus']) # Õhurõhk merepinnal
    ilmaandmed['winddirection'] = float_or_none(data_observation_data_hourly['wd10ma']) # Tuule suund, 10 m valdav kraad
    ilmaandmed['windspeedmax'] = float_or_none(data_observation_data_hourly['ws1hx']) # Tuule kiirus, 1 h maksimum
    ilmaandmed['cloudiness'] = data_observation_data_hourly['ccins'] # Üldpilvisus 1 m avg manuaalvaatlus
    ilmaandmed['phenomenon'] = data_observation_data_hourly['pw15maEst'] # Tuule kiirus, 1 h maksimum
    ilmaandmed['phenomenon_observer'] = data_observation_data_hourly['pwm15maEst'] # Nähtus 15 min avg manuaalvaatlus Est
    ilmaandmed['precipitations'] = float_or_none(data_observation_data_hourly['pr1hs']) # Sademed, 1 h summa (näha kodukal)
    ilmaandmed['visibility'] = float_or_none(data_observation_data_hourly['vis1ma']) # Nähtavuskaugus, 1 m keskmine
    # 'airtemperature': 20.4,	'tains': '20,4',	Õhutemperatuur, 1 m keskmine
    # 'relativehumidity': 53.0,	'rhins': '53.0',	Suhteline õhuniiskus
    # 'airpressure': 1009.5,	'qffins': '1009,5',	Õhurõhk merepinnal
    # 'airpressure_delta': -0.9,	'qffmuutus': '-0,9',	Õhurõhk merepinnal
    # 'winddirection': 201.0,	'wd10ma': '201.0',	Tuule suund, 10 m valdav kraad
    # 'windspeed': 4.4,	'ws10ma': '4,4',	Tuule kiirus 10 min avg
    # 'windspeedmax': 9.3,	'ws1hx': '9,3',	Tuule kiirus, 1 h maksimum
    # 'cloudiness': None,	'ccins': None,	Üldpilvisus 1 m avg manuaalvaatlus
    # 'phenomenon': 'nähtusteta',	'pw15maEst': 'nähtusteta',	Nähtus 15 min avg Est
    # 'phenomenon_observer': '',	'pwm15maEst': None,	Nähtus 15 min avg manuaalvaatlus Est
    # 'precipitations': 0.0,	'pr1hs': '0,0',	Sademed, 1 h summa (näha kodukal)
    # 'visibility': 28.0,	'vis1ma': '28,0'	Nähtavuskaugus, 1 m keskmine
    ilmaandmed['airtemperature_max'] = float_or_none(data_observation_temperature_extremums['ta1hx']) # õhutemperatuur 1 h max
    ilmaandmed['airtemperature_min'] = float_or_none(data_observation_temperature_extremums['ta1hm']) # õhutemperatuur 1 h min
    # 'airtemperature_max': 20.8,	'ta1hx': '20,8'	õhutemperatuur 1 h max
    # 'airtemperature_min': 19.0	'ta1hm': '19,0',	õhutemperatuur 1 h min
    ilmaandmed['station_id'] = 1
    ilmaandmed['timestamp'] = aware_from_dt
    # 'station_id': 1,
    # 'timestamp': datetime.datetime(2025, 6, 7, 17, 0, tzinfo=<DstTzInfo 'Europe/Tallinn' EEST+3:00:00 DST>),
    if verbose:
        print(dt, ilmaandmed)
    return ilmaandmed

# Ilmateenistuse etteantud täistunni mõõtmise andmed veebist
def ilmaandmed_veebist(dt, verbose=False):
    """
    Tagastab etteantud dt (aware v6i naive) viimase möödunud täistunni ilmaandmed
    ilmateenistus.ee veebilehelt
    """
    if dt.tzinfo != None:
        dt = dt.astimezone(tz=ZoneInfo('Europe/Tallinn'))
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
    href = 'https://www.ilmateenistus.ee/ilm/ilmavaatlused/vaatlusandmed/tunniandmed/'
    p2ev = dt.strftime("%d.%m.%Y")
    tund = dt.strftime("%H:00")
    # Päringu aadress
    p2ring = ''.join(
        [
            href,
            f'?filter[date]={p2ev}',
            f'&filter[hour]={tund}',
            f'&filter[maxDate]={p2ev}&filter[minDate]=30.01.2004'
        ]
    )
    # Loeme veebist andmed

    # proovime filter p2ringut ja kui see ei 6nnestu, siis viimaste andmete p2ringut
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}
    for link in [p2ring, href]:
        # Kasutame vaheldumisi kahte erinevat strateegiat
        if datetime.now().hour%2 == 0:
            # Alternatiiv 1
            try:
                request = urllib.request.Request(link, headers=headers)
                with urllib.request.urlopen(request) as req:
                    response = req.read()
                    # print(response)
            except urllib.error.HTTPError as e:
                if e.code != 200:
                    print(f'{link} {e}')
                    ## can add authentication here
                else:
                    print('http error', e)
                return {}
        else:
            # Alternatiiv 2
            req = requests.get(link, headers=headers)
            if req.status_code == requests.codes.ok:
                response = req.text
            else:
                print(f'{dt}: {link} {req.text}')
                return {}

        # Struktueerime ja kontrollime vastavust
        soup = BeautifulSoup(response, 'html.parser')
        kontroll_datetime_soup = soup.find(attrs={'class': 'utc-info'}) # formaat: 'UTC 11.07.2022 20:00'
        kontroll_datetime = datetime.strptime(kontroll_datetime_soup.text.strip(), 'UTC %d.%m.%Y %H:%M')
        if all([
            kontroll_datetime.year == dt.astimezone(timezone.utc).year,
            kontroll_datetime.month == dt.astimezone(timezone.utc).month,
            kontroll_datetime.day == dt.astimezone(timezone.utc).day,
            kontroll_datetime.hour == dt.astimezone(timezone.utc).hour
        ]):
            andmed = dict()
            # Leiame lehelt tabeli
            table = soup.table
            # Leiame tabelist rea
            row = table.find(string=re.compile(jaam))
            data = row.find_parent().find_next_siblings()
            for i in range(len(data)):
                # print(dt_naive, data[i])
                if data[i]:  # kui andmeväli pole tühi
                    if cols[i] in ['phenomenon', 'phenomenon_observer']:  # tekstiväli
                        andmed[cols[i]] = data[i].text.strip()
                    else:  # numbriväli
                        value = data[i].text.strip().replace(',', '.')
                        andmed[cols[i]] = float_or_none(value)
                else:
                    andmed[cols[i]] = None
            # andmed['station'] = Jaam.objects.filter(name=jaam).first()
            if andmed['airtemperature'] == None and andmed['airpressure'] == None:  # Kui andmed puudulikud
                andmed = {}
                continue
            andmed['station_id'] = 1
            andmed['timestamp'] = pytz.timezone('Europe/Tallinn'). \
                localize(datetime(dt.year, dt.month, dt.day, dt.hour))
            # küsime andmed maxmin andmed juurde
            maxmin_andmed = get_maxmin_airtemperature(dt)
            if maxmin_andmed:
                andmed['airtemperature_max'] = maxmin_andmed['airtemperature_max']
                andmed['airtemperature_min'] = maxmin_andmed['airtemperature_min']
            break
        else:
            print(f'{dt}: {link} Vale! {dt} vs {kontroll_datetime}')
            # Kui vastus vale kellaaja või kuupäevaga, saadame tagasi tühja tabeli
            andmed = {}

    if verbose:
        print(dt, andmed)
    return andmed

def yrno_forecast():
    # Weather forecast from Yr, delivered by the Norwegian Meteorological Institute and the NRK
    href = "https://api.met.no/weatherapi/locationforecast/2.0/complete?lat=57.78&lon=26.05"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Accept": "application/json"
    }
    r = requests.get(
        href,
        headers=headers,
    )
    print(r.status_code, r.text[:100])
    yr = json.loads(r.text)
    print(yr['properties']['timeseries'][0])
    return yr

def yrno_48h():
    # Weather forecast from Yr, delivered by the Norwegian Meteorological Institute and the NRK
    href = 'http://www.yr.no/place/Estonia/Valgamaa/Valga/forecast_hour_by_hour.xml'
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
    }
    r = requests.get(
        href,
        headers=headers,
    )
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
        time = pytz.timezone('Europe/Tallinn').localize(datetime.strptime(data.attrib['from'], '%Y-%m-%dT%H:%M:%S'))
        time_stamp = int(datetime.timestamp(time))
        dt.append(time_stamp)
        if time.hour == 0:
            dateticks.append(n)
        cat.append(time) # Aeg
        # Sademed
        prec_value = float(data.find("precipitation").attrib['value'])
        try:
            prec_maxvalue = float(data.find("precipitation").attrib['maxvalue'])
            prec_minvalue = float(data.find("precipitation").attrib['minvalue'])
        except:
            prec_minvalue = prec_maxvalue = prec_value
        if prec_maxvalue > 2:
            prec_color = 'heavy'
        elif prec_maxvalue > 1:
            prec_color = 'moderate'
        elif prec_maxvalue > 0:
            prec_color = 'light'
        else:
            prec_color = 'none'
        prec.append([prec_value, prec_minvalue, prec_maxvalue])
        # Tuul
        windspeed_value = float(data.find("windSpeed").attrib['mps'])
        winddirection_value = float(data.find("windDirection").attrib['deg'])
        wind.append(
            [windspeed_value, winddirection_value]
        )
        # Temperatuur
        temp_value = float(data.find("temperature").attrib['value'])
        temp.append(temp_value)
        # Õhurõhk
        pres_value = float(data.find("pressure").attrib['value'])
        pres.append(pres_value)
        # Sümbolid
        symb_value = data.find("symbol").attrib['var']
        symb.append(symb_value) # Ilmasümboli kood (YR)
        yr['forecast'][str(time_stamp)] = {
            'time': time,
            'precipitation': f'{prec_value}' if prec_value==prec_maxvalue else f'{prec_minvalue}-{prec_maxvalue}',
            # 'precipitation': {
            #     'value': prec_value,
            #     'minvalue': prec_minvalue,
            #     'maxvalue': prec_maxvalue
            # },
            'precipitation_color': prec_color,
            'temperature': temp_value,
            'pressure': pres_value,
            'windSpeed': windspeed_value,
            'windDirection': winddirection_value,
            'symbol': symb_value
        }
    yr['series'] = {
        'start': cat[0], # Mis kellast prognoos algab
        'temperatures': temp,
        'windbarbs': wind,
        'airpressures': pres,
        'precipitations': prec,
        'symbols': symb,
        'dt': dt,
    }
    return yr

def get_ilmateenistus_history():
    history = {}
    n = datetime.now().astimezone(ZoneInfo('Europe/Tallinn'))
    ilm_last3h = Ilm.objects.filter(timestamp__range=(n - timedelta(hours=3), n)).order_by('timestamp')
    for hour in ilm_last3h:
        history[hour.timestamp] = {}
        history[hour.timestamp]['airtemperature'] = hour.airtemperature
        history[hour.timestamp]['precipitations'] = hour.precipitations
        history[hour.timestamp]['phenomenon'] = hour.phenomenon
        history[hour.timestamp]['symbol'] = ilman2htus_yrnosymboliks(hour.phenomenon, hour.timestamp)
        precipitation_color = 'none'
        if hour.precipitations:
            if hour.precipitations > 2:
                precipitation_color = 'heavy'
            elif hour.precipitations > 1:
                precipitation_color = 'moderate'
            elif hour.precipitations > 0:
                precipitation_color = 'light'
        history[hour.timestamp]['precipitation_color'] = precipitation_color
    return history

def owm_onecall(path=os.getcwd()):
    try:
        from django.conf import settings
        api_key = settings.OWM_APIKEY
    except:
        api_config = config(path, 'ilm/utils/owm.ini', 'OWM')
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
    # print(resp.status_code)
    weather['history'] = json.loads(resp.text)

    weather['forecast'] = dict()
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
            try:
                prec_maxvalue = float(hour['rain']['1h'])
            except:
                prec_maxvalue = 0
            if prec_maxvalue > 2:
                prec_color = 'heavy'
            elif prec_maxvalue > 1:
                prec_color = 'moderate'
            elif prec_maxvalue > 0:
                prec_color = 'light'
            else:
                prec_color = 'none'
            hour['precipitation_color'] = prec_color
            weather['forecast'][str(hour['dt'])] = hour
        for day in weather['daily']:
            # day['datetime'] = datetime.fromtimestamp(day['dt'], timezone.utc)
            day['kirjeldus'] = OWM_CODES.get(
                str(day['weather'][0]['id']),
                day['weather'][0]['description']
            )
            try:
                prec_maxvalue = float(day['rain'])
            except:
                prec_maxvalue = 0
            if prec_maxvalue > 2:
                prec_color = 'heavy'
            elif prec_maxvalue > 1:
                prec_color = 'moderate'
            elif prec_maxvalue > 0:
                prec_color = 'light'
            else:
                prec_color = 'none'
            day['precipitation_color'] = prec_color
        try:
            weather['history']['hourly3h'] = weather['history']['hourly'][-3:]  # viimased kolm tundi
        except:
            weather['history']['hourly3h'] = None
        if weather['history']['hourly3h']:
            for hour in weather['history']['hourly']:
                # hour['datetime'] = datetime.fromtimestamp(hour['dt'], timezone.utc)
                hour['kirjeldus'] = OWM_CODES.get(
                    str(hour['weather'][0]['id']),
                    hour['weather'][0]['description']
                )
                try:
                    prec_maxvalue = float(hour['rain']['1h'])
                except:
                    prec_maxvalue = 0
                if prec_maxvalue > 2:
                    prec_color = 'heavy'
                elif prec_maxvalue > 1:
                    prec_color = 'moderate'
                elif prec_maxvalue > 0:
                    prec_color = 'light'
                else:
                    prec_color = 'none'
                hour['precipitation_color'] = prec_color
    return weather

# küsib Ilmateenistuse hetkeandmed
def get_ilmateenistus_now():
    # hetkeilm = bdi.ilm_praegu()
    hetkeilm = ilm_praegu()
    return hetkeilm

def get_ilmateenistus_location_data(headers):
    url = 'https://www.ilmateenistus.ee/wp-json/emhi/locationAutocomplete?location=Valga%20linn'
    params = {
        "location": "Valga linn"
    }
    response = requests.get(
        url,
        headers=headers,
        params=params
    )
    if response.status_code == 200:
        data = json.loads(response.text)
        return data


def get_ilmateenistus_forecast() -> dict or None:
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Accept": "application/json"
    }
    # t2psustame asukoha
    try:
        location_data = get_ilmateenistus_location_data(headers=headers)
        coordinates = location_data['data'][0]['coordinates']
    except:
        coordinates = '57.776678;26.030958' # fallback if location not found
    url = f"https://www.ilmateenistus.ee/wp-content/themes/ilm2020/meteogram.php/?locationId=784&coordinates={coordinates}"

    response = requests.get(
        url,
        headers=headers
    )
    if response.status_code == requests.codes.ok:
        data = json.loads(response.text)

        hours = [hour for hour in data['forecast']['tabular']['time']]

        forecast = dict()
        for hour in hours:
            time = pytz.timezone('Europe/Tallinn').localize(
                datetime.strptime(hour['@attributes']['from'], '%Y-%m-%dT%H:%M:%S'))
            timestamp = int(datetime.timestamp(time))
            try:
                prec_maxvalue = float(hour['precipitation']['@attributes']['value'])
            except:
                prec_maxvalue = 0
            if prec_maxvalue > 2:
                prec_color = 'heavy'
            elif prec_maxvalue > 1:
                prec_color = 'moderate'
            elif prec_maxvalue > 0:
                prec_color = 'light'
            else:
                prec_color = 'none'
            PHENOMEN_ICONS_24H = [ # ilmaikoon samasugune p2eval ja öösel
                'overcast', 'moderate_rain',
                'light_snowfall', 'moderate_snowfall',
                'light_sleet', 'moderate_sleet',
            ]
            if hour['phenomen']['@attributes']['className'] in PHENOMEN_ICONS_24H:
                symbol = hour['phenomen']['@attributes']['className']
            else:
                symbol = '_'.join([hour['phenomen']['@attributes']['className'], ephem_data.get_dayornight(time)])
            forecast[str(timestamp)] = {
                'time': time,
                'phenomen': hour['phenomen']['@attributes'],
                'windDirection': hour['windDirection']['@attributes'],
                'windSpeed': hour['windSpeed']['@attributes']['mps'],
                'temperature': hour['temperature']['@attributes']['value'],
                'precipitation': hour['precipitation']['@attributes']['value'],
                'precipitation_color': prec_color,
                'pressure': hour['pressure']['@attributes']['value'],
                'symbol': symbol
            }
            if settings.REDIS_INUSE:
                redis_client.set(
                    'ilmateenistus_forecast',
                    json.dumps({'forecast': forecast}, cls=DjangoJSONEncoder),
                    ex=10*60
                )
        return {'forecast': forecast}
    else: # korrektset ilmaennustust ei saadud
        print(url, response.status_code)
        return None

def ilmateenistus_forecast() -> dict or None:
    if settings.REDIS_INUSE and redis_client.exists('ilmateenistus_forecast'):
        forecast_jsondumps = redis_client.get('ilmateenistus_forecast')
        forecast = json.loads(forecast_jsondumps)
    else:
        forecast = get_ilmateenistus_forecast()
    return forecast

# yrno API ver 2 andmete päring
class YrnoAPI():

    def __init__(self):
        self.utc = pytz.utc
        self.local = pytz.timezone("Europe/Tallinn")
        # Uued ilmasymbolid vs vanad koodid
        # symobol_codes day&night [4, 15, 10, 11, 48, 32, 50, 34, 46, 30, 47, 31, 49,33, 9, 22, 12, 23, 13, 14]
        self.symbol_codes = {
            'clearsky': '1',
            'cloudy': '4',
            'fair': '2',
            'fog': '15',
            'heavyrain': '10',
            'heavyrainandthunder': '11',
            'heavyrainshowers': '41',
            'heavyrainshowersandthunder': '25',
            'heavysleet': '48',
            'heavysleetandthunder': '32',
            'heavysleetshowers': '43',
            'heavysleetshowersandthunder': '27',
            'heavysnow': '50',
            'heavysnowandthunder': '34',
            'heavysnowshowers': '45',
            'heavysnowshowersandthunder': '29',
            'lightrain': '46',
            'lightrainandthunder': '30',
            'lightrainshowers': '40',
            'lightrainshowersandthunder': '24',
            'lightsleet': '47',
            'lightsleetandthunder': '31',
            'lightsleetshowers': '42',
            'lightsnow': '49',
            'lightsnowandthunder': '33',
            'lightsnowshowers': '44',
            'lightssleetshowersandthunder': '26',
            'lightssnowshowersandthunder': '28',
            'partlycloudy': '3',
            'rain': '9',
            'rainandthunder': '22',
            'rainshowers': '5',
            'rainshowersandthunder': '6',
            'sleet': '12',
            'sleetandthunder': '23',
            'sleetshowers': '7',
            'sleetshowersandthunder': '20',
            'snow': '13',
            'snowandthunder': '14',
            'snowshowers': '8',
            'snowshowersandthunder': '21'
        }

        # Küsime ilmaennustuse json täielikud andmed
        self.yrno_forecast_json = self.get_data('yrno')
        if self.yrno_forecast_json:
            # Filtreerime järgmise 48h ennustuse andmed
            self.timeseries_48h = self.yrno_next48h(self.yrno_forecast_json)
            # Töötleme veebi jaoks sobivateks andmepakkideks
            self.yrno_forecasts = self.yrno_next48h_forecasts(self.timeseries_48h)

    # Andmete pärimine APIst
    def get_api_data(self, url, headers, params):
        r = requests.get(
            url,
            headers=headers,
            params=params
        )
        if r.status_code == 200:
            meta = {
                'Expires': r.headers['Expires'],
                'Last-Modified': r.headers['Last-Modified']
            }
            data = json.loads(r.text)
            return {'meta': meta, 'data': data}
        else:
            return None

    # Kas andmed on värsked või vaja värskendada
    def get_data(self, src):
        # Kas värsked andmed olemas (django cache)
        try:
            if cache.get(src):
                data = cache.get(src)
                now = datetime.now(timezone.utc)
                exp = parsedate_to_datetime(data['meta']['Expires'])
                if now < exp:
                    # print('Andmed: cache Django')
                    return data
        except:
            pass

        # Küsime värsked andmed
        # kohaandmed = Valga
        altitude = "64"
        lat = "57.77781"
        lon = "26.0473"
        # yr.no API Valga: https://api.met.no/weatherapi/locationforecast/2.0/complete?lat=57.77781&lon=26.0473&altitude=64
        url = 'https://api.met.no/weatherapi/locationforecast/2.0/complete'
        params = {
            'lat': lat,
            'lon': lon,
            'altitude': altitude
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "*/*",
        }
        data = self.get_api_data(url, headers, params)

        # Salvestame cache (django)
        try:
            cache.set(src, data)
        except:
            pass

        return data

    # Filtreerime täielikust ennustusandmestikust järgmised 48h
    def yrno_next48h(self, yrno_forecast_json):
        data = yrno_forecast_json['data']
        # yrno API annab uue ennustuse iga tunni aja tagant
        # alates sellele järgnevast täistunnist
        timeseries = data['properties']['timeseries']
        now = datetime.now(timezone.utc).isoformat()
        # Filtreerime hetkeajast hilisemad järgmise 48h ennustused
        filter_pastnow = filter(lambda hour: hour['time'] > now, timeseries)
        timeseries_48h = list(filter_pastnow)[:48]
        return timeseries_48h

    # Töötleme andmed ilmveebile sobivateks pakkideks: 'meta', 'forecast', 'series'
    def yrno_next48h_forecasts(self, timeseries_48h):
        yr = {}
        meta = self.yrno_forecast_json['data']['properties']['meta']
        updated_at = datetime.strptime(
            meta['updated_at'],
            '%Y-%m-%dT%H:%M:%SZ'
        )
        updated_at_utc = pytz.utc.localize(updated_at)
        updated_at_loc = updated_at_utc.astimezone(self.local)
        yr['meta'] = meta
        yr['meta']['lastupdate'] = updated_at_loc
        yr['forecast'] = {}
        cat = []
        dt = []
        prec = []
        wind = []
        temp = []
        pres = []
        symb = []
        dateticks = [0]  # Graafikul kuupäevatikkerite jaoks
        for hour in timeseries_48h:
            # data = tag_forecast[n]
            # time = pytz.timezone('Europe/Tallinn').localize(datetime.strptime(data.attrib['from'], '%Y-%m-%dT%H:%M:%S'))
            date_string = hour['time']
            utc_time = self.utc.localize(datetime.strptime(
                date_string,
                '%Y-%m-%dT%H:%M:%SZ'
            )
            )
            loc_time = utc_time.astimezone(self.local)
            cat.append(loc_time)  # Aeg
            time_stamp = int(datetime.timestamp(loc_time))
            dt.append(time_stamp)
            if loc_time.hour == 0:
                n = loc_time - cat[0]
                dateticks.append(int(n.total_seconds() / 3600))
            instant = hour['data']['instant']['details']
            # print(hour['time'])
            try:
                next_1_hours = hour['data']['next_1_hours']
            except KeyError:
                next_1_hours = hour['data']['next_6_hours']
            # Sademed
            prec_minvalue = float(next_1_hours['details']['precipitation_amount_min'])
            prec_maxvalue = float(next_1_hours['details']['precipitation_amount_max'])
            prec_value = prec_minvalue  # ühildumiseks eelmise versiooniga
            # except:
            if prec_maxvalue > 2:
                prec_color = 'heavy'
            elif prec_maxvalue > 1:
                prec_color = 'moderate'
            elif prec_maxvalue > 0:
                prec_color = 'light'
            else:
                prec_color = 'none'
            prec.append([prec_value, prec_minvalue, prec_maxvalue])
            # Tuul
            wind_from_direction = float(instant['wind_from_direction'])
            wind_speed = float(instant['wind_speed'])
            wind.append(
                [wind_speed, wind_from_direction]
            )
            # Temperatuur
            air_temperature = float(instant['air_temperature'])
            temp.append(air_temperature)
            # Õhurõhk
            air_pressure_at_sea_level = float(instant['air_pressure_at_sea_level'])
            pres.append(air_pressure_at_sea_level)
            # Sümbolid
            symbol_code = next_1_hours['summary']['symbol_code']
            symb.append(symbol_code)  # Ilmasümboli kood (YR)

            yr['forecast'][str(time_stamp)] = {
                'time': loc_time,
                'precipitation': f'{prec_value}' if prec_minvalue == prec_maxvalue else f'{prec_minvalue}-{prec_maxvalue}',
                # 'precipitation': {
                #     'value': prec_value,
                #     'minvalue': prec_minvalue,
                #     'maxvalue': prec_maxvalue
                # },
                'precipitation_color': prec_color,
                'temperature': air_temperature,
                'pressure': air_pressure_at_sea_level,
                'windSpeed': wind_speed,
                'windDirection': wind_from_direction,
                'symbol': symbol_code
            }
        yr['series'] = {
            'start': cat[0],  # Mis kellast prognoos algab
            'temperatures': temp,
            'windbarbs': wind,
            'airpressures': pres,
            'precipitations': prec,
            'symbols': symb,
            'dt': dt,
        }
        return yr

    # uue ilmasümboli teisendamine vanaks
    def yrno_2old_symbol_code(self, symbol_code_str):
        symbol_code = symbol_code_str.split('_')
        if symbol_code[-1] == 'night':
            dayornight = 'n'
        elif symbol_code[-1] == 'day':
            dayornight = 'd'
        else:
            dayornight = ''
        old_symbol_code = self.symbol_codes.get(symbol_code[0], None)
        if old_symbol_code:
            return ''.join([old_symbol_code, dayornight])
        else:
            return ''

    # vana ilmasümboli teisendamine uueks
    def yrno_2new_symbol_code(self, symbol_code_str):
        new_symbol_codes = {self.symbol_codes[el]: el for el in self.symbol_codes}
        if symbol_code_str[-1] == 'd':
            dayornight = '_day'
            old_symbol_code = symbol_code_str.replace('d', '')
        elif symbol_code_str[-1] == 'n':
            dayornight = '_night'
            old_symbol_code = symbol_code_str.replace('n', '')
        else:
            dayornight = ''
            old_symbol_code = symbol_code_str
        new_symbol_code = new_symbol_codes.get(old_symbol_code, None)
        if new_symbol_code:
            return ''.join([new_symbol_code, dayornight])
        else:
            return ''

# küsib ilmaandmed ja moodustab nendest sõnastiku
def get_forecasts(hours=48):
    yAPI = YrnoAPI()
    y = yAPI.yrno_forecasts
    # o = owm_onecall()
    i = ilmateenistus_forecast()
    now = datetime.now()
    forecast = dict()

    for forecast_hour in range(1, hours):
        fore_dt = datetime(now.year, now.month, now.day, now.hour) + timedelta(hours=forecast_hour)
        ref_dt = int(datetime.timestamp(fore_dt))

        # yr.no
        y_temp = None
        y_prec = None
        y_prec_color = ''
        y_pres = None
        y_icon = ''
        y_data = y['forecast'].get(str(ref_dt), None)
        if y_data:
            y_temp = y_data['temperature']
            y_icon = y_data['symbol']
            y_prec = y_data['precipitation']
            y_prec_color = y_data['precipitation_color']
            y_pres = float_or_none(y_data['pressure'])
        # openweathermaps.org
        # o_temp = None
        # o_prec = None
        # o_prec_color = ''
        # o_pres = None
        # o_icon = ''
        # o_data = o['forecast'].get(str(ref_dt), None)
        # if o_data:
        #     o_temp = o_data['temp']
        #     o_icon = o_data['weather'][0]['icon']
        #     try:
        #         o_prec = o_data['rain']['1h']
        #     except:
        #         o_prec = None
        #     o_prec_color = o_data['precipitation_color']
        #     o_pres = float_or_none(o_data['pressure'])

        # ilmateenistus.ee
        i_temp = None
        i_prec = None
        i_prec_color = ''
        i_pres = None
        i_icon = ''
        i_data = i['forecast'].get(str(ref_dt), None)
        if i_data:
            i_temp = float_or_none(i_data['temperature'])
            i_prec = i_data['precipitation']
            i_prec_color = i_data['precipitation_color']
            i_pres = float_or_none(i_data['pressure'])
            i_icon = i_data['symbol']

        forecast[str(ref_dt)] = {
            'y_temp': y_temp,
            'y_icon': y_icon,
            'y_prec': str(y_prec),
            'y_prec_color': y_prec_color,
            'y_pres': y_pres,
            # 'o_temp': o_temp,
            # 'o_icon': o_icon,
            # 'o_prec': str(o_prec),
            # 'o_prec_color': o_prec_color,
            # 'o_pres': o_pres,
            'i_temp': i_temp,
            'i_icon': i_icon,
            'i_prec': str(i_prec),
            'i_prec_color': i_prec_color,
            'i_pres': i_pres,
        }
    return forecast

if __name__ == "__main__":
    # ilmaandmed_veebist(datetime(2022, 7, 16, 22), verbose=True)
    # ilmaandmed_veebist(datetime(2022, 7, 16, 23), verbose=True)
    pass