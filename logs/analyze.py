from datetime import datetime, timedelta
import json
import os
import re
import sys
import urllib.request

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
        sep='\s+',
        quotechar='"',
        doublequote=True,
        names=names,
        error_bad_lines=False
        )
    # Teisendame kuup2evaveeruks
    df['time'] = df.apply(datestrings2date, axis=1)
    df['resp_size'] = df.apply(intorzero, axis=1)
    # Tagastame ainult vajalikud veerud
    return df.drop(['time_str'], axis=1)


def ipinfo(ip_addr=''):
    ip_locate_url = 'https://geolocation-db.com/jsonp/' + ip_addr
    with urllib.request.urlopen(ip_locate_url) as url:
        data = url.read().decode()
        data = data.split("(")[1].strip(")")
        print(data)

# IP aadressi kohta WHOIS info
# eeldus pip install --upgrade ipwhois
def whoisinfo(ip_addr=''):
    # from ipwhois import IPWhois
    # obj = IPWhois(ip_addr)
    # obj.lookup_rdap(asn_methods=["whois"])
    pass

if __name__ == '__main__':
    # path = os.path.dirname(sys.argv[0])
    path = '/usr/local/apache2/logs/'
    logfile = os.path.join(path, 'access_log')
    if not os.path.isfile(logfile):
        path = os.path.dirname(sys.argv[0])
        logfile = os.path.join(path, 'access_log')
    log_df = logfile2df(logfile)
    utc = pytz.utc
    now = utc.localize(datetime.now())
    time24hoursago = now - timedelta(days=1)
    log_df_filtered = log_df[log_df.time > time24hoursago]
    print(f'Päringuid {log_df_filtered.IP_address.count()}, kogumahuga {log_df_filtered.resp_size.sum()} b')
    # Agendid aadressid allalaadimise mahu järgi
    print('Downloader Agents')
    result = log_df_filtered.groupby('agent')['resp_size']\
        .agg(['sum','count'])\
        .sort_values(by = ['sum'], ascending=[False])\
        .head(10)
    print(result)
    # IP aadressid allalaadimise mahu järgi
    print('Downloader IPaddresses traffic')
    result = log_df_filtered.groupby('IP_address')['resp_size']\
        .agg(['sum','count'])\
        .sort_values(by = ['sum'], ascending=[False])\
        .head(10)
    print(result)
    # IP aadressid allalaadimise kordade järgi
    print('Downloader IPaddresses hits')
    result = log_df_filtered.groupby('IP_address')['resp_size'] \
        .agg(['sum', 'count']) \
        .sort_values(by=['count'], ascending=[False]) \
        .head(10)
    print(result)