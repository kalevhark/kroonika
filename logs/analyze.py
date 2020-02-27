from datetime import datetime
import os
import re
import sys

import pandas as pd

def logfile2df(logfile):
    # fn tagastab logifailist kuup2evav2lja
    def datestrings2date(rows):
        t = ''.join([rows.time_str, rows.TZ_str])[1:-1]
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
    # Loeme faili datafreimiks
    df = pd.read_csv(
        logfile,
        sep='\s+',
        quotechar='"',
        doublequote=True,
        names=names
        )
    # Teisendame kuup2evaveeruks
    df['time'] = df.apply(datestrings2date, axis=1)
    df['resp_size'] = df.apply(intorzero, axis=1)
    # Tagastame ainult vajalikud veerud
    return df.drop(['time_str'], axis=1)


if __name__ == '__main__':
    # path = os.path.dirname(sys.argv[0])
    path = '/usr/local/apache2/logs/'
    logfile = os.path.join(path, 'access_log')
    if not os.path.isfile(logfile):
        path = os.path.dirname(sys.argv[0])
        logfile = os.path.join(path, 'access_log')
    log_df = logfile2df(logfile)
    # IP aadressid allalaadimise mahu järgi
    result = log_df.groupby(['agent']).sum().sort_values(by = ['resp_size'], ascending=[False])['resp_size']
    print(result.head())