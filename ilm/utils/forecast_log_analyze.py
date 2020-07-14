import csv
from datetime import datetime, timedelta
import json
import os
import re
from statistics import mean
import sys

import pandas as pd
import requests

dir_logs = 'logs'
fn_forecast = 'forecast_6h.log'
a = None

# pole kasutusel
def convert_yrno_prec():
    fn_src_path = [path, dir_logs, fn_forecast]
    fn_src = os.path.join(*fn_src_path)
    fn_dst_path = [path, dir_logs, 'new_' + fn_forecast]
    fn_dst = os.path.join(*fn_dst_path)
    
    with open(fn_src, 'r') as src_logfile:
        with open(fn_dst, 'w') as dst_logfile:
            for line in src_logfile:
                dst_logfile.write(convert_yrno_prec_line(line))

# pole kasutusel
def convert_yrno_prec_line(line):
    pattern = re.compile(r"\[(.*)\]", re.DOTALL)
    matches = pattern.search(line)
    if matches:
        data = matches.group(1)
        precs = data.split(',')
        min = precs[0].strip()
        max = precs[-1].strip()
        if min == max:
            new_data = min
        else:
            new_data = '-'.join([min, max])
        # print(new_data)
        cleanr = re.compile(r'\[.*?\]')
        line = re.sub(cleanr, new_data, line)
    return line

def read_forecast_log2pd(path, dir_logs, fn_forecast):
    yrno_prec = lambda x : (
        mean(
            [
                float(x.split('-')[0]),
                float(x.split('-')[-1])
            ]
            )
        )
    
    fn_src_path = [path, dir_logs, fn_forecast]
    fn_src = os.path.join(*fn_src_path)
    field_prefix = fn_forecast.split('.')[0] + '_'

    df = pd.read_csv(
        fn_src,
        delimiter=';',
        skiprows=0,
        header=None,
        index_col = 0,
        converters={2: yrno_prec},
        decimal = '.',
        # usecols=[1,2,3,6,11,13],
        names = [
            'timestamp',
            f'{field_prefix}y_temp', f'{field_prefix}y_prec',
            f'{field_prefix}o_temp', f'{field_prefix}o_prec',
            f'{field_prefix}i_temp', f'{field_prefix}i_prec',
            ],
        # parse_dates=[5]
    )
    return df

def read_observation_log2pd(path, dir_logs, fn_forecast):
    fn_src_path = [path, dir_logs, fn_forecast]
    fn_src = os.path.join(*fn_src_path)
    df = pd.read_csv(
        fn_src,
        delimiter=';',
        skiprows=0,
        header=None,
        index_col = 0,
        decimal = '.',
        na_values = ['None'],
        names = [
            'timestamp',
            'observed_temp',
            'observed_prec',
            ],
    )
    return df.dropna()

def timestamp2date(row):
    date = datetime.fromtimestamp(row.name)
    y = date.year
    m = date.month
    d = date.day
    h = date.hour
    api_url = 'https://valgalinn.ee/api/i/'
    params = {'y': y, 'm': m, 'd': d, 'h': h}
    r = requests.get(api_url, params=params)
    data = json.loads(r.text)
    results = data['results'][0]
    temp = results['airtemperature']
    prec = results['precipitations']
    print(results['timestamp'])
    return pd.Series([temp, prec], index=['real_temp', 'real_prec'])

def obs_quality(row, fore_hour):
    # 50% hindest temperatuur: 1 kraad erinevust=-5 punkt
    # 50% hindest sademete täpsus: 1 mm erinevust=-10 punkt
    # Kui tegelikult sadas, aga prognoos = 0.0, siis -10 punkti
    max = 100
    koefitsent = 10
    #yr.no
    y_temp_qual = koefitsent*abs(row['observed_temp'] - row[f'forecast_{fore_hour}_y_temp'])
    y_prec_qual = koefitsent*abs(row['observed_prec'] - row[f'forecast_{fore_hour}_y_prec'])
    if (row[f'forecast_{fore_hour}_y_prec'] > 0) and (row['observed_prec'] == 0.0):
        y_prec_qual -= koefitsent
    y_qual = max - (y_temp_qual + y_prec_qual)
    #owm
    o_temp_qual = koefitsent*abs(row['observed_temp'] - row[f'forecast_{fore_hour}_o_temp'])
    o_prec_qual = koefitsent*abs(row['observed_prec'] - row[f'forecast_{fore_hour}_o_prec'])
    if (row[f'forecast_{fore_hour}_o_prec'] > 0) and (row['observed_prec'] == 0.0):
        o_prec_qual -= koefitsent
    o_qual = max - (o_temp_qual + o_prec_qual)
    #it.ee
    i_temp_qual = koefitsent*abs(row['observed_temp'] - row[f'forecast_{fore_hour}_i_temp'])
    i_prec_qual = koefitsent*abs(row['observed_prec'] - row[f'forecast_{fore_hour}_i_prec'])
    if (row[f'forecast_{fore_hour}_i_prec'] > 0) and (row['observed_prec'] == 0.0):
        i_prec_qual -= koefitsent
    i_qual = max - (i_temp_qual + i_prec_qual)
    return pd.Series(
        [y_qual, o_qual, i_qual],
        index=[f'{fore_hour}_y_qual', f'{fore_hour}_o_qual', f'{fore_hour}_i_qual']
        )

def logs2bigdata(path):
    # Loeme prognooside logid
    fore_xh = dict()
    for hour in ('6h', '12h', '24h'):
        fore_xh[hour] = read_forecast_log2pd(path, dir_logs, f'forecast_{hour}.log')
        # print(hour, fore_xh[hour].shape)
    # Ühendame üheks tabeliks
    fore = pd.merge(fore_xh['6h'], fore_xh['12h'], left_index=True, right_index=True)
    fore = pd.merge(fore, fore_xh['24h'], left_index=True, right_index=True)
    # print(fore.shape)
    # Loeme mõõtmisandmed
    obs = read_observation_log2pd(path, dir_logs, 'observations.log')
    # print('obs', obs.shape)
    # Ühendame prognoosid ja mõõtmised
    bd = pd.merge(fore, obs, how='outer', left_index=True, right_index=True)
    # Arvutame prognoosi kvalteedi
    for hour in ('6h', '12h', '24h'):
        qual = bd.apply(obs_quality, axis=1, args=(hour,))
        # print(qual.dropna().apply(mean))
        bd = bd.merge(qual, how='outer', left_index=True, right_index=True)
    # Konverteerime timestamp -> datetime -> kohalik ajavöönd
    bd['aeg'] = pd.to_datetime(bd.index, unit='s').tz_localize('EET', ambiguous='infer')
    # print('qual', bd.shape)
    return bd
    
def main(path=''):
    from django.utils import timezone
    bd = logs2bigdata(path)
    bd_days = bd.groupby(
        [
            bd.aeg.dt.year.values,
            bd.aeg.dt.month.values,
            bd.aeg.dt.day.values
            ]
        ).mean().dropna()
    now = int(datetime.timestamp(timezone.now()))
    now24hback = int(datetime.timestamp(timezone.now() - timedelta(hours=24)))
    bd_last24h = bd[(bd.index >= now24hback) & (bd.index < now)].dropna()
    # bd_days.loc[year, month, day] -> filtreerimiseks
    # bd.loc[(2020, 7, 3):(2020, 7, 5)] -> vahemiku filtreerimiseks
    # for hour in ('6h', '12h', '24h'):
    #     print(bd_days[[f'{hour}_y_qual', f'{hour}_o_qual', f'{hour}_i_qual']].round(1))
    
##    fn_dst_path = [path, dir_logs, 'observations.log']
##    fn_dst = os.path.join(*fn_dst_path)
##    real.to_csv(fn_dst, sep=';', header=False)
    return {
        # 'all': bd.to_dict('index'),
        'last24h': bd_last24h.to_dict('index'),
        'days': bd_days.to_dict('index')
    }

if __name__ == "__main__":
    # execute only if run as a script
    path = os.path.dirname(sys.argv[0])
    if len(sys.argv) < 2:
        # Argumente ei ole
        pass
    else:
        for arg in sys.argv:
            print(arg)

    # Käivitame põhiprotsessi        
    a = main(path)
