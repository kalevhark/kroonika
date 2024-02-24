from datetime import datetime, timedelta
import json
import os
import re
import sys
import urllib.request

from ipwhois import IPWhois, HTTPLookupError
import pandas as pd
import pytz

def logfile2df(logfile):
    # fn tagastab logifailist kuup2evav2lja
    def datestrings2date(rows):
        try:
            t = ''.join([rows.time_str, rows.TZ_str])[1:-1]
        except:
            return None
        return datetime.strptime(t, '%d/%b/%Y:%H:%M:%S%z')

    def intorzero(rows):
        try:
            return int(rows.resp_size)
        except:
            return 0
    
    # Logifaili veerunimed
    names = [
        'IP_address',
        'client_ID',
        'user_ID',
        'time_str',
        'TZ_str',
        'request',
        'status_code',
        'resp_size',
        'referer',
        'agent'
        ]
    # Loeme logifaili datafreimiks
    df = pd.read_csv(
        logfile,
        sep=r'\s+',
        quotechar='"',
        # doublequote=True,
        names=names,
        # error_bad_lines=False,
        on_bad_lines='warn' # 'skip'
    )
    # Teisendame kuup2evaveeruks
    df['time'] = df.apply(datestrings2date, axis=1)
    df['resp_size'] = df.apply(intorzero, axis=1)
    # Tagastame ainult vajalikud veerud
    return df.drop(['time_str'], axis=1)


def parse_str(x):
    """
    Returns the string delimited by two characters.
    Example:
        `>>> parse_str('[my string]')`
        `'my string'`
    """
    if x is None:
        print("X : ", x)
        return "AAAAAAAAAAAAAAA"
    return x[1:-1]


def parse_datetime(x):
    '''
    Parses datetime with timezone formatted as:
        `[day/month/year:hour:minute:second zone]`
    Example:
        `>>> parse_datetime('13/Nov/2015:11:45:42 +0000')`
        `datetime.datetime(2015, 11, 3, 11, 45, 4, tzinfo=<UTC>)`
    Due to problems parsing the timezone (`%z`) with `datetime.strptime`, the
    timezone will be obtained using the `pytz` library.
    '''
    try:
        dt = datetime.strptime(x[1:-7], '%d/%b/%Y:%H:%M:%S')
        dt_tz = int(x[-6:-3]) * 60 + int(x[-3:-1])
        return dt.replace(tzinfo=pytz.FixedOffset(dt_tz))
    except:
        x = "[02/May/2021:03:20:40 +0700]"
        dt = datetime.strptime(x[1:-7], '%d/%b/%Y:%H:%M:%S')
        dt_tz = int(x[-6:-3]) * 60 + int(x[-3:-1])
        return dt.replace(tzinfo=pytz.FixedOffset(dt_tz))


def parse_int(x):
    if x.isnumeric():
        return int(x)

    return x
def logfile2df2(logfile):
    data = pd.read_csv(
        logfile,
        sep=r'\s(?=(?:[^"]*"[^"]*")*[^"]*$)(?![^\[]*\])',
        engine='python',
        na_values='-',
        header=None,
        usecols=[0, 3, 4, 5, 6, 7, 8],
        names=['ip', 'time', 'request', 'status', 'size', 'referer', 'user_agent'],
        converters={
            'time': parse_datetime,
            'request': parse_str,
            'status': parse_int,
            'size': parse_int,
            'referer': parse_str,
            'user_agent': parse_str
        }
    )
    print(data.shape, data.columns)
    return data

# Geoinfo hankimine ip-aadressi järgi
def ipggeoinfo(ip_addr=''):
    ip_locate_url = 'https://geolocation-db.com/jsonp/' + ip_addr
    with urllib.request.urlopen(ip_locate_url) as url:
        data = url.read().decode()
        data = data.split("(")[1].strip(")")
        print(data)
    return data

# IP aadressi kohta WHOIS info
# eeldus pip install --upgrade ipwhois
def whoisinfo(ip_addr=''):
    obj = IPWhois(ip_addr)
    whois_data = obj.lookup_rdap(asn_methods=["whois"])
    return whois_data

# Tagastab IP aadressi alusel hosti kirjelduse
def whoisinfo_asn_description(rows):
    try:
        asn_description = whoisinfo(rows.name)['asn_description']
    except HTTPLookupError:
        asn_description = f'Err: {rows.name}'
    return asn_description

# Tagastab, kas on bot
def is_bot(rows):
    bots = ['bot', 'index']
    pat = rf'(?:{"|".join(bots)})'
    return re.search(pat, str(rows.user_agent), re.IGNORECASE)!=None

# Tagastab stringist sõna, millel on boti laadne nimi *bot, *index vms
def find_bot_name(rows):
    bots = ['bot', 'index']
    pat = rf'(\w*{"|".join(bots)})\w*'
    bot = re.search(pat, rows.name, flags=re.IGNORECASE)
    if bot:
        return bot.group()
    else:
        return ''

def is_tiles(rows):
    pat = re.compile('/tiles/')
    try:
        return re.search(pat, rows.request) != None
    except:
        return False

if __name__ == '__main__':
    # path = os.path.dirname(sys.argv[0])
    path = '/usr/local/apache2/logs/'
    logfile = os.path.join(path, 'access_log')
    if not os.path.isfile(logfile):
        path = os.path.dirname(sys.argv[0])
        logfile = os.path.join(path, 'valgalinn.access.log')
    print('Analüüsime logifaili:', logfile)
    log_df = logfile2df2(logfile)

    # log_df = logfile2df(logfile)
    utc = pytz.utc
    now = utc.localize(datetime.now())
    time24hoursago = now - timedelta(days=3)
    log_df_filtered = log_df[log_df.time > time24hoursago]

    # Agendid aadressid allalaadimise mahu järgi
    print('Downloader Agents:')
    result = log_df_filtered.groupby('user_agent')['size']\
        .agg(['sum','count'])\
        .sort_values(by = ['sum'], ascending=[False])\
        .head(10)
    result['sum'] = result['sum'].map('{:,}'.format).str.replace(",", " ", regex=False).str.replace(".", ",", regex=False)
    print(result)
    print()

    # IP aadressid allalaadimise mahu järgi
    print('Downloader IPaddresses traffic:')
    result = log_df_filtered.groupby('ip')['size']\
        .agg(['sum','count'])\
        .sort_values(by = ['sum'], ascending=[False])\
        .head(10)
    print(result)
    result['asn_description'] = result.apply(whoisinfo_asn_description, axis=1)
    result['sum'] = result['sum'].map('{:,}'.format).str.replace(",", " ", regex=False).str.replace(".", ",", regex=False)
    print(result)
    print()

    # IP aadressid allalaadimise kordade järgi
    print('Downloader IPaddresses hits:')
    result = log_df_filtered.groupby('ip')['size'] \
        .agg(['sum', 'count']) \
        .sort_values(by=['count'], ascending=[False]) \
        .head(10)
    result['asn_description'] = result.apply(whoisinfo_asn_description, axis=1)
    result['sum'] = result['sum'].map('{:,}'.format).str.replace(",", " ", regex=False).str.replace(".", ",", regex=False)
    print(result)
    print()

    # IP aadressid, kes said 403
    print('403 status:')
    result = log_df_filtered[log_df_filtered['status'] == 403].groupby('ip')['size'] \
        .agg(['count']) \
        .sort_values(by=['count'], ascending=[False]) \
        .head(30)
    # result['asn_description'] = result.apply(whoisinfo_asn_description, axis=1)
    print(result)
    print()

    print('404 status:')
    result = log_df_filtered[log_df_filtered['status'] == 404].groupby('request')['size'] \
        .agg(['count']) \
        .sort_values(by=['count'], ascending=[False]) \
        .head(10)
    print(result)
    print()

    print('bots')
    result = log_df_filtered[log_df_filtered.apply(is_bot, axis=1)].groupby('user_agent')['size'] \
        .agg(['sum','count'])\
        .sort_values(by = ['sum'], ascending=[False])\
        .head(10)
    result.index = result.apply(find_bot_name, axis=1)
    result['sum'] = result['sum'].map('{:,}'.format).str.replace(",", " ", regex=False).str.replace(".", ",", regex=False)
    print(result)
    print()

    print('tiles')
    result = log_df_filtered[log_df_filtered.apply(is_tiles, axis=1)]['size'] \
        .agg(['sum', 'count'])
    print(result)
    print()

    # Viimase 24h kogumaht
    log_df_filtered_size_sum = log_df_filtered.size.sum()
    print(f'Päringuid {log_df_filtered.ip.count()}, kogumahuga {round(log_df_filtered_size_sum/1024/1024)} Mb')
    # print()