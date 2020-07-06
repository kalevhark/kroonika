#!/home/ec2-user/django/kroonika_env/bin/python3

#
# Ilmaandmete regulaarseks uuendamiseks andmebaasis
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-ilm-app/utils/update.py

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

from .utils import utils

# The following connect() function connects to the suppliers database and prints out the PostgreSQL database version.
def connect(path=''):
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = utils.config(path)

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)

        # create a cursor
        cur = conn.cursor()

        # execute a statement
        print('PostgreSQL database version:')
        cur.execute('SELECT version()')

        # display the PostgreSQL database server version
        db_version = cur.fetchone()
        print(db_version)

        # close the communication with the PostgreSQL
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')

# Viimane mõõtmistulemus
def get_maxtimestamp(path=''):
    """ query maxdate from the ilm_ilm table """
    conn = None
    try:
        params = utils.config(path)
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("SELECT max(timestamp) FROM ilm_ilm")
        print("Viimane kanne: ", cur.rowcount)

        row = cur.fetchone()
        # d = pytz.timezone('Europe/Tallinn').localize(datetime.now())

        # while row is not None:
        #     # print(row[0], (d - row[0]).seconds)
        #     row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return row[0]

# Viimase ööpäeva mõõtmistulemused
def get_observations_24hours(path=''):
    """ query maxdate from the ilm_ilm table """
    conn = None
    try:
        params = utils.config(path)
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("SELECT timestamp FROM ilm_ilm WHERE timestamp > now() - interval '1 day' ORDER BY timestamp")
        print("Kandeid: ", cur.rowcount)
        row = cur.fetchone()

        while row is not None:
            # print(row)
            d = row[0]
            print(utils.utc2eesti_aeg(d))
            row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()


# Mõõtmistulemuse olemasolu kontroll aja järgi
def check_observation_exists(dt, path=''):
    """ query if exists timestamp from the ilm_ilm table """
    conn = None
    row = dict()

    try:
        params = utils.config(path)
        conn = psycopg2.connect(**params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # cur = conn.cursor()
        condition_y = f"date_part('year', timestamp) = {dt.year}"
        condition_m = f"date_part('month', timestamp) = {dt.month}"
        condition_d = f"date_part('day', timestamp) = {dt.day}"
        condition_h = f"date_part('hour', timestamp) = {dt.hour}"
        condition = ' and '.join([condition_y, condition_m, condition_d, condition_h])
        query = f'SELECT * FROM ilm_ilm WHERE {condition}'

        cur.execute(query)
        # print("Kandeid: ", cur.rowcount)

        row = cur.fetchone()

        # while row is not None:
        #     # d = row[0]
        #     # print(f'PostgreSQL datetime          : {d}')
        #     # print(f'PostgreSQL timezone          : {d.tzname()}')
        #     # print(f'PostgreSQL offset UTC ajaga  : {d.utcoffset()}')
        #     # print(f'PostgreSQL Eesti aeg         : {utc2eesti_aeg(d)}')
        #     # print((d - row[0]).seconds)
        #     # print(row)
        #     row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return row

# Lisab uue vaatlusandmete kirje
def insert_new_observations(observation_dict, path=''):
    if not observation_dict:
        return
    # Eemaldame id, kui on
    observation_dict.pop('id', None)
    # Moodustame veergude loendi
    cols = [key for key in observation_dict]
    cols_str = ', '.join(cols)
    # vals = [observation_dict[col] for col in cols]
    vals_str = ", ".join([f"%({col})s" for col in cols])
    sql = f"INSERT INTO ilm_ilm ({cols_str}) VALUES ({vals_str}) RETURNING id;"

    conn = None
    obs_id = None
    try:
        # read database configuration
        params = utils.config(path)
        # connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        # create a new cursor
        cur = conn.cursor()
        # execute the INSERT statement
        cur.execute(sql, {**observation_dict})
        # get the generated id back
        obs_id = cur.fetchone()[0]
        # commit the changes to the database
        conn.commit()
        # close communication with the database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return obs_id

# Kustutab topeltkirjed
def delete_duplicate_observations(path=''):
    conn = None
    rows_deleted = 0
    try:
        # read database configuration
        params = utils.config(path)
        # connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        # create a new cursor
        cur = conn.cursor()
        # execute the UPDATE  statement
        cur.execute("DELETE FROM ilm_ilm a USING ilm_ilm b WHERE a.id < b.id AND a.timestamp = b.timestamp;")
        # get the number of updated rows
        rows_deleted = cur.rowcount
        # Commit the changes to the database
        conn.commit()
        # Close communication with the PostgreSQL database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    # print(f'Kustutati: {rows_deleted}')
    return rows_deleted


if __name__ == '__main__':
    path = os.path.dirname(sys.argv[0])
    # get_maxtimestamp()
    # Kustutame duplikaatread
    rows_deleted = delete_duplicate_observations(path)
    if rows_deleted > 0:
        print(f'Kustutati: {rows_deleted} kirjet')

    # Kontrollime 48 tunni andmete olemasolu, vajadusel lisame
    for hour in range(47, -1, -1): # Viimase 48 tunni andmed
        observation_time = datetime.now() - timedelta(hours=hour)
        observation = check_observation_exists(observation_time, path)
        # print(observation_time, end=': ')
        if not observation:
            ilm_observation_veebist = utils.ilmaandmed_veebist(observation_time)
            # print(ilm_observation_veebist)
            if ilm_observation_veebist:
                id = insert_new_observations(ilm_observation_veebist, path)
                print(f'{ilm_observation_veebist["timestamp"]} lisatud {id}')
            else:
                print(f'{observation_time} uuendamine ebaõnnestus')
        else:
            # print('olemas.')
            pass

    # Ilmaennustuste logi jaoks andmete küsimine
    y = utils.yrno_48h()
    o = utils.owm_onecall()
    i = utils.ilmateenistus_forecast()

    for forecast_hour in [6, 12, 24]: # Salvestame 6, 12, 24 h prognoosid
        now = datetime.now()
        fore_dt = datetime(now.year, now.month, now.day, now.hour) + timedelta(seconds=forecast_hour*3600)
        ref_dt = int(datetime.timestamp(fore_dt))

        # yr.no
        y_temp = None
        y_prec = None
        y_data = y['forecast'].get(str(ref_dt), None)
        if y_data:
            y_temp = y_data['temperature']
            y_prec = y_data['precipitation']

        # openweathermaps.org
        o_temp = None
        o_prec = None
        o_data = o['forecast'].get(str(ref_dt), None)
        if o_data:
            o_temp = o_data['temp']
            try:
                o_prec = o_data['rain']['1h']
            except:
                o_prec = '0.0'

        # ilmateenistus.ee
        i_temp = None
        i_prec = None
        i_data = i['forecast'].get(str(ref_dt), None)
        if i_data:
            i_temp = i_data['temperature']
            i_prec = i_data['precipitation']

        line = ';'.join(
            [
                str(ref_dt),
                str(y_temp), str(y_prec),
                str(o_temp), str(o_prec),
                str(i_temp), str(i_prec),
            ]
        )
        with open(f'logs/forecast_{forecast_hour}h.log', 'a') as f:
            f.write(line + '\n')

    # Viimase täistunnimõõtmise logimine faili
    now = datetime.now()
    observation_time = datetime(now.year, now.month, now.day, now.hour)
    observation = check_observation_exists(observation_time, path)
    if observation:
        with open('logs/observations.log', 'a') as f:
            time = str(int(datetime.timestamp(observation['timestamp'])))
            temp = str(observation['airtemperature'])
            prec = str(observation['precipitations'])
            line = ';'.join([time, temp, prec])
            f.write(line + '\n')

