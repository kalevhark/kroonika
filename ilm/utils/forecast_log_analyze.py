from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
from statistics import mean
# import sys

import pandas as pd
import pytz
import requests

dir_logs = 'logs'
# fn_forecast = 'forecast_6h.log'
# a = None

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
    names = [
        'timestamp',
        f'{field_prefix}y_temp', f'{field_prefix}y_prec',
        f'{field_prefix}o_temp', f'{field_prefix}o_prec', # owm out 2024 juuni
        f'{field_prefix}i_temp', f'{field_prefix}i_prec',
    ]
    df = pd.read_csv(
        fn_src,
        delimiter=';',
        skiprows=0,
        header=None,
        index_col = 0,
        converters={2: yrno_prec},
        decimal = '.',
        na_values = ['None'],
        # usecols=[1,2,3,6,11,13],
        names = names,
        # parse_dates=[5]
    )
    df[names[1:]] = df[names[1:]].apply(pd.to_numeric, downcast="float")
    return df

def read_observation_log2pd(path, dir_logs, fn_forecast):
    fn_src_path = [path, dir_logs, fn_forecast]
    fn_src = os.path.join(*fn_src_path)
    names = [
        'timestamp',
        'observed_temp',
        'observed_prec',
    ]
    df = pd.read_csv(
        fn_src,
        delimiter=';',
        skiprows=0,
        header=None,
        index_col = 0,
        decimal = '.',
        na_values = ['None'],
        names = names,
    ).dropna()
    df[names[1:]] = df[names[1:]].apply(pd.to_numeric, downcast="float")
    return df

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
    # print(results['timestamp'])
    return pd.Series([temp, prec], index=['real_temp', 'real_prec'])

def obs_quality(row, fore_hour):
    # 50% hindest temperatuur: 1 kraad erinevust=-5 punkt
    # 50% hindest sademete täpsus: 1 mm erinevust=-10 punkt
    # Kui tegelikult sadas, aga prognoos = 0.0, siis -10 punkti
    columns = row.keys()
    values = [row[column] for column in columns]
    max = 100
    koefitsent = 10
    #yr.no
    y_temp_qual = koefitsent * abs(row['observed_temp'] - row[f'forecast_{fore_hour}_y_temp'])
    y_prec_qual = koefitsent * abs(row['observed_prec'] - row[f'forecast_{fore_hour}_y_prec'])
    y_qual = max - (y_temp_qual + y_prec_qual)
    if (row['observed_prec'] > 0.0) and (row[f'forecast_{fore_hour}_y_prec'] == 0):
        y_qual -= koefitsent
    #owm out 2024 juuni
    # o_temp_qual = koefitsent * abs(row['observed_temp'] - row[f'forecast_{fore_hour}_o_temp'])
    # o_prec_qual = koefitsent * abs(row['observed_prec'] - row[f'forecast_{fore_hour}_o_prec'])
    # o_qual = max - (o_temp_qual + o_prec_qual)
    # if (row['observed_prec'] > 0.0) and (row[f'forecast_{fore_hour}_o_prec'] == 0):
    #     o_qual -= koefitsent
    #ilmateenistus.ee
    # print(type(row[f'forecast_{fore_hour}_i_temp']))
    i_temp_qual = koefitsent * abs(row['observed_temp'] - float(row[f'forecast_{fore_hour}_i_temp']))
    i_prec_qual = koefitsent * abs(row['observed_prec'] - float(row[f'forecast_{fore_hour}_i_prec']))
    i_qual = max - (i_temp_qual + i_prec_qual)
    if (row['observed_prec'] > 0.0) and (row[f'forecast_{fore_hour}_i_prec'] == 0):
        i_qual -= koefitsent
    return pd.Series(
        # [*values, y_qual, o_qual, i_qual],
        [*values, y_qual, i_qual], # owm out 2024 juuni
        dtype="float32",
        # index=[*columns, f'{fore_hour}_y_qual', f'{fore_hour}_o_qual', f'{fore_hour}_i_qual']
        index = [*columns, f'{fore_hour}_y_qual', f'{fore_hour}_i_qual'] # owm out 2024 juuni
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
    bd = pd.\
        merge(fore, obs, how='outer', left_index=True, right_index=True)
    # Arvutame prognoosi kvalteedi
    for hour in ('6h', '12h', '24h'):
        # qual = bd.apply(obs_quality, axis=1, args=(hour,))
        bd = bd.apply(obs_quality, axis=1, args=(hour,))
        # print(qual.dropna().apply(mean))
        # bd = bd.merge(qual, how='outer', left_index=True, right_index=True)
    # Konverteerime timestamp -> datetime -> kohalik ajavöönd
    bd['aeg'] = pd.\
        to_datetime(bd.index, unit='s').\
        tz_localize('EET', ambiguous='NaT', nonexistent=pd.Timedelta('1h'))
    # print(bd.shape, bd.dtypes, bd.memory_usage(deep=True))

    bd.to_pickle(path / dir_logs / 'obs_quality_data.pickle')
    return bd

def main(path=''):
    # from django.utils import timezone
    # kõik mõõtmised
    if os.path.isfile(path / dir_logs / 'obs_quality_data.pickle'):
        bd = pd.read_pickle(path / dir_logs / 'obs_quality_data.pickle')
    else:
        bd = logs2bigdata(path)
    # kõik mõõtmised päevade kaupa
    bd_days = bd.groupby(
        [
            bd.aeg.dt.year.values,
            bd.aeg.dt.month.values,
            bd.aeg.dt.day.values
            ]
        )\
        .mean(numeric_only=True)\
        .dropna()\
        .sort_index(ascending=False) # sorteerime uuemad ette
    bd_mean = bd.mean(numeric_only=True)  # ajaloo keskmine

    tz_EE = pytz.timezone(pytz.country_timezones['ee'][0])
    today = datetime.now(tz=tz_EE)
    now = int(datetime.timestamp(today))  # timestamp

    # viimase 24h andmed
    # now = int(datetime.timestamp(timezone.now()))
    # now24hback = int(datetime.timestamp(timezone.now() - timedelta(hours=24)))
    now24hback = int(datetime.timestamp(today - timedelta(hours=24)))
    bd_last24h = bd[(bd.index >= now24hback) & (bd.index < now)]\
        .dropna()\
        .sort_index(ascending=False) # sorteerime uuemad ette
    bd_last24h_mean = bd_last24h.mean(numeric_only=True)

    # viimase 30p andmed
    now30dback = int(datetime.timestamp(today - timedelta(days=30)))
    bd_last30d_mean = bd[(bd.index >= now30dback) & (bd.index < now)]\
        .dropna()\
        .mean(numeric_only=True)
    # viimase 30p andmed
    now01yback = int(datetime.timestamp(datetime(today.year-1, today.month, today.day)))
    bd_last01y_mean = bd[(bd.index >= now01yback) & (bd.index < now)] \
        .dropna() \
        .mean(numeric_only=True)

    # bd_days.loc[year, month, day] -> filtreerimiseks
    # bd.loc[(2020, 7, 3):(2020, 7, 5)] -> vahemiku filtreerimiseks
    # for hour in ('6h', '12h', '24h'):
    #     print(bd_days[[f'{hour}_y_qual', f'{hour}_o_qual', f'{hour}_i_qual']].round(1))


    return {
        # 'all': bd.to_dict('index'),
        'last24h': bd_last24h.to_dict('index'),
        'days': bd_days.to_dict('index'),
        'bd_mean': bd_mean.to_dict(),
        'bd_last24h_mean': bd_last24h_mean.to_dict(),
        'bd_last30d_mean': bd_last30d_mean.to_dict(),
        'bd_last01y_mean': bd_last01y_mean.to_dict()
    }

if __name__ == "__main__":
    # execute only if run as a script
    path = Path(__file__).resolve().parent.parent.parent
    # Käivitame põhiprotsessi        
    a = main(path)
    # print(a['bd_mean'])