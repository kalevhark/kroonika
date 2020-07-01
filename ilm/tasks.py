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

from .utils import config, utils
# from ilm.views import yrno_48h, owm_onecall

# The following connect() function connects to the suppliers database and prints out the PostgreSQL database version.
def connect():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = config.config()

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
        params = config.config(path)
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
        params = config.config(path)
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
        params = config(path)
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
        params = config(path)
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
        params = config.config(path)
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
    rows_deleted = delete_duplicate_observations(path)
    if rows_deleted > 0:
        print(f'Kustutati: {rows_deleted} kirjet')

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

    # y = yrno_48h()
    # y_dt = y['forecast']['dt'][6]
    # y_temp = y['forecast']['temperatures'][6]
    # y_prec = y['forecast']['precipitations'][6]
    # o = owm_onecall()
    # o_dt = o['hourly'][6]['dt']
    # o_temp = o['hourly'][6]['temp']
    # try:
    #     o_prec = o['hourly'][6]['rain']['1h']
    # except:
    #     o_prec = None
    # line = ';'.join([str(y_dt), str(y_temp), str(y_prec), str(o_dt), str(o_temp), str(o_prec)])
    # with open('forecast_6h.log', 'a') as f:
    #     f.write(line + '\n')