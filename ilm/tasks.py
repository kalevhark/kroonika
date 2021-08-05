#!/home/ec2-user/django/kroonika_env/bin/python3

#
# Ilmaandmete regulaarseks uuendamiseks andmebaasis
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-ilm-app/utils/update.py

from datetime import datetime, timedelta
import os
from pathlib import Path
# import re
import sys
# import xml.etree.ElementTree as ET

# from urllib.request import Request, urlopen
# from urllib.error import URLError

# from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor
# from pytz import timezone
# import pytz
# import requests

try:
    from .utils import utils
except: # kui käivitatakse lokaalselt
    from utils import utils

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
def delete_duplicate_observations(path='', verbose=False):
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
    if verbose and rows_deleted > 0:
        print(f'Kustutati: {rows_deleted} kirjet')
    return rows_deleted

# Täiendab puudulikud kirjed, millel puudub õhutemperatuurinäit
def update_uncomplete_observations(path='', verbose=False):
    conn = None
    rows_uncomplete = 0
    rows_updated = 0
    try:
        # read database configuration
        params = utils.config(path)
        # connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        # create a new cursor
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # leiame jooksva aasta ilma õhutemperatuuri näiduta read
        cur.execute("SELECT id, timestamp FROM ilm_ilm WHERE date_part('year', timestamp) = date_part('year', CURRENT_DATE) AND airtemperature IS NULL;")
        # leiame kõik ilma õhutemperatuuri näiduta read
        # cur.execute(
        #     "SELECT id, timestamp FROM ilm_ilm WHERE airtemperature IS NULL;"
        # )
        # get the number of uncomplete rows
        rows_uncomplete = cur.rowcount
        for record in cur:
            # record:
            # RealDictRow([
            #   ('id', 11322),
            #   ('timestamp', datetime.datetime(2004, 5, 1, 6, 0, tzinfo=psycopg2.tz.FixedOffsetTimezone(offset=0, name=None)))
            # ])
            print(record['timestamp'], 'ebatäielikud andmed', record['id'])
            # 11322 2004-05-01 06:00:00+00:00
            observation_time = record['timestamp']
            ilm_observation_veebist = utils.ilmaandmed_veebist(observation_time)
            if ilm_observation_veebist and (ilm_observation_veebist['airtemperature'] != None):
                id = insert_new_observations(ilm_observation_veebist, path)
                print(f'{ilm_observation_veebist["timestamp"]} lisatud {id}')
                rows_updated += 1
            else:
                print(f'{observation_time} uuendamine ebaõnnestus')

        # Commit the changes to the database
        conn.commit()
        # Close communication with the PostgreSQL database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    if verbose and rows_updated > 0:
        print(f'Täiendati: {rows_updated} kirjet')
    return rows_updated

# Täiendab puudulikud kirjed, millel puudub õhutemperatuurinäit
def update_missing_observations(path='', verbose=False):
    conn = None
    rows_updated = 0
    timestamp_missing_records = []
    try:
        # read database configuration
        params = utils.config(path)
        # connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        # create a new cursor
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # leiame kõik kuupäevaread
        # cur.execute(
        #     "SELECT timestamp FROM ilm_ilm ORDER BY timestamp ASC;"
        # )
        # leiame kõik kuupäevaread köesoleval aastal
        cur.execute(
            "SELECT timestamp FROM ilm_ilm WHERE date_part('year', timestamp) = date_part('year', CURRENT_DATE) ORDER BY timestamp ASC;"
        )
        timestamp_all_records = [record['timestamp'] for record in cur]
        for n in range(0, len(timestamp_all_records)-1):
            if (timestamp_all_records[n+1] - timestamp_all_records[n]) > timedelta(seconds=3600):
                d = timestamp_all_records[n] + timedelta(hours=1)
                while d not in timestamp_all_records:
                    if d != utils.last_sunday(d.year, 10): # oktoobri viimane pühapäev
                        timestamp_missing_records.append(d)
                    d += timedelta(hours=1)

        for timestamp in timestamp_missing_records:
            observation_time = timestamp
            print(observation_time, 'puuduvad andmed')
            ilm_observation_veebist = utils.ilmaandmed_veebist(observation_time)
            if ilm_observation_veebist and (ilm_observation_veebist['airtemperature'] != None):
                id = insert_new_observations(ilm_observation_veebist, path)
                print(f'{ilm_observation_veebist["timestamp"]} lisatud {id}')
                rows_updated += 1
            else:
                print(f'{observation_time} uuendamine ebaõnnestus')

        # Commit the changes to the database
        conn.commit()
        # Close communication with the PostgreSQL database
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    if verbose and rows_updated > 0:
        print(f'Lisati: {rows_updated} kirjet')
    return rows_updated

def update_maxmin(path=''):
    conn = None
    row = dict()

    try:
        params = utils.config(path)
        conn = psycopg2.connect(**params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT 
                "ilm_ilm"."timestamp", 
                MIN("ilm_ilm"."airtemperature_min") 
                    OVER 
                        (
                            ORDER BY 
                                "ilm_ilm"."timestamp" ASC 
                            ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                        ) AS "rolling_min", 
                MAX("ilm_ilm"."airtemperature_max") 
                    OVER 
                        (
                            ORDER BY 
                                "ilm_ilm"."timestamp" ASC 
                            ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                        ) AS "rolling_max" 
                FROM "ilm_ilm"
            ORDER BY "ilm_ilm"."timestamp" DESC
            """
        cur.execute(query)
        print(cur.rowcount)

        from collections import Counter
        above20_year_list = []
        below20_year_list = []
        for row in cur.fetchall():
            if row['rolling_max'] and (row['rolling_max'] <= -20) and (row['timestamp'].hour == 17):
                above20_year_list.append(row['timestamp'].year)
            if row['rolling_min'] and (row['rolling_min'] >= 20) and (row['timestamp'].hour == 2):
                below20_year_list.append(row['timestamp'].year)
        print(Counter(above20_year_list), Counter(below20_year_list))

        # Iga aasta max, min, keskmine temperatuur ja sademete kogus
        query = """
            SELECT 
                EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\'), 
                MAX("ilm_ilm"."airtemperature_max") AS "airtemperature_max__max", 
                MIN("ilm_ilm"."airtemperature_min") AS "airtemperature_min__min", 
                AVG("ilm_ilm"."airtemperature") AS "airtemperature__avg", 
                SUM("ilm_ilm"."precipitations") AS "precipitations__sum" FROM "ilm_ilm" 
            GROUP BY 
                EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') 
            ORDER BY 
                EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') ASC
        """

        cur.execute(query)
        # print("Kandeid: ", cur.rowcount)

        years_top = dict()
        row = cur.fetchone()
        while row is not None:
            #     # d = row[0]
            #     # print(f'PostgreSQL datetime          : {d}')
            #     # print(f'PostgreSQL timezone          : {d.tzname()}')
            #     # print(f'PostgreSQL offset UTC ajaga  : {d.utcoffset()}')
            #     # print(f'PostgreSQL Eesti aeg         : {utc2eesti_aeg(d)}')
            #     # print((d - row[0]).seconds)
            # print(row)
            year = int(row['date_part'])
            airtemperature_max__max = row['airtemperature_max__max']
            airtemperature_min__min = row['airtemperature_min__min']
            airtemperature__avg = round(row['airtemperature__avg'], 1)
            precipitations__sum = row['precipitations__sum']

            cur2 = conn.cursor(cursor_factory=RealDictCursor)

            # Aasta max temp mõõtmise aeg
            subquery_obs_max = f"""
                SELECT 
                    "ilm_ilm"."timestamp" FROM "ilm_ilm" 
                WHERE 
                    (
                        "ilm_ilm"."airtemperature_max" = {airtemperature_max__max} AND 
                        "ilm_ilm"."timestamp" BETWEEN \'{year}-01-01T00:00:00+02:00\'::timestamptz AND \'{year}-12-31T23:59:59.999999+02:00\'::timestamptz
                    ) 
                ORDER BY 
                    "ilm_ilm"."timestamp" DESC 
                    LIMIT 1
            """
            cur2.execute(subquery_obs_max)
            row = cur2.fetchone()
            obs_max= row['timestamp']

            # Aasta min temp mõõtmise aeg
            subquery_obs_min = f"""
                SELECT 
                    "ilm_ilm"."timestamp" FROM "ilm_ilm" 
                WHERE 
                    (
                        "ilm_ilm"."airtemperature_min" = {airtemperature_min__min} AND 
                        "ilm_ilm"."timestamp" BETWEEN \'{year}-01-01T00:00:00+02:00\'::timestamptz AND \'{year}-12-31T23:59:59.999999+02:00\'::timestamptz
                    ) 
                ORDER BY 
                    "ilm_ilm"."timestamp" DESC 
                    LIMIT 1
            """
            cur2.execute(subquery_obs_min)
            row = cur2.fetchone()
            obs_min = row['timestamp']

            subquery_below30 = f"""
            SELECT 
                COUNT(*) FROM 
                    (
                        SELECT 
                            EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') AS Col1, 
                            EXTRACT(\'month\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') AS Col2, 
                            EXTRACT(\'day\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') AS Col3, 
                            MAX("ilm_ilm"."airtemperature_max") AS "airtemperature_max__max", 
                            MIN("ilm_ilm"."airtemperature_min") AS "airtemperature_min__min", 
                            AVG("ilm_ilm"."airtemperature") AS "airtemperature__avg", 
                            SUM("ilm_ilm"."precipitations") AS "precipitations__sum" FROM "ilm_ilm" 
                        WHERE 
                            "ilm_ilm"."timestamp" BETWEEN \'{year}-01-01T00:00:00+02:00\'::timestamptz AND \'{year}-12-31T23:59:59.999999+02:00\'::timestamptz 
                        GROUP BY 
                            EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\'), 
                            EXTRACT(\'month\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\'), 
                            EXTRACT(\'day\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') 
                        HAVING 
                            MIN("ilm_ilm"."airtemperature_min") <=  -30
                    ) 
                subquery
            """
            cur2.execute(subquery_below30)
            row = cur2.fetchone()
            days_below30 = row['count']

            subquery_above30 = f"""
            SELECT 
                COUNT(*) FROM 
                    (
                        SELECT 
                            EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') AS Col1, 
                            EXTRACT(\'month\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') AS Col2, 
                            EXTRACT(\'day\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') AS Col3, 
                            MAX("ilm_ilm"."airtemperature_max") AS "airtemperature_max__max", 
                            MIN("ilm_ilm"."airtemperature_min") AS "airtemperature_min__min", 
                            AVG("ilm_ilm"."airtemperature") AS "airtemperature__avg", 
                            SUM("ilm_ilm"."precipitations") AS "precipitations__sum" FROM "ilm_ilm" 
                        WHERE 
                            "ilm_ilm"."timestamp" BETWEEN \'{year}-01-01T00:00:00+02:00\'::timestamptz AND \'{year}-12-31T23:59:59.999999+02:00\'::timestamptz 
                        GROUP BY 
                            EXTRACT(\'year\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\'), 
                            EXTRACT(\'month\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\'), 
                            EXTRACT(\'day\' FROM "ilm_ilm"."timestamp" AT TIME ZONE \'Europe/Tallinn\') 
                        HAVING 
                            MAX("ilm_ilm"."airtemperature_max") >=  30
                    ) 
                subquery
            """
            cur2.execute(subquery_above30)
            row = cur2.fetchone()
            days_above30 = row['count']

            # print(obs_max, obs_min, days_below30, days_above30)

            cur2.close()

            days_above20 = 0
            days_below20 = 0

            years_top[year] = {
                'year_min': airtemperature_min__min,  # madalaim aasta jooksul mõõdetud õhutemperatuur
                'obs_min': obs_min,  # madalaima aasta jooksul mõõdetud õhutemperatuuri mõõtmise aeg
                'year_max': airtemperature_max__max,  # kõrgeim aasta jooksul mõõdetud õhutemperatuur
                'obs_max': obs_max,  # kõrgeima aasta jooksul mõõdetud õhutemperatuuri mõõtmise aeg
                'year_temp_avg': airtemperature__avg,
                'year_prec_sum': precipitations__sum,
                'days_below20': days_below20,
                'days_above20': days_above20,
                'days_below30': days_below30,
                'days_above30': days_above30
            }

            # järgmine rida:
            row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return row

def update_maxmin_rolling(path=''):
    conn = None
    row = dict()

    start = datetime.now()
    stages = dict()
    try:
        params = utils.config(path)
        conn = psycopg2.connect(**params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            DROP MATERIALIZED VIEW IF EXISTS public.ilm_ilm_rolling_8h;

            CREATE MATERIALIZED VIEW public.ilm_ilm_rolling_8h
            TABLESPACE pg_default
            AS
                SELECT * 
                FROM
                    (SELECT 
                        "ilm_ilm"."timestamp", 
                        MIN("ilm_ilm"."airtemperature_min") 
                            OVER 
                                (
                                    ORDER BY 
                                        "ilm_ilm"."timestamp" ASC 
                                    ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                                ) AS "rolling_min", 
                        MAX("ilm_ilm"."airtemperature_max") 
                            OVER 
                                (
                                    ORDER BY 
                                        "ilm_ilm"."timestamp" ASC 
                                    ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                                ) AS "rolling_max" 
                        FROM "ilm_ilm" 
                    ORDER BY "ilm_ilm"."timestamp" DESC) AS rolling
                WHERE (
                    "rolling"."rolling_min" > 20 AND 
                    EXTRACT(hour FROM "rolling"."timestamp" AT TIME ZONE 'Europe/Tallinn') = 5
                ) OR (
                    "rolling"."rolling_max" < -20 AND 
                    EXTRACT(hour FROM "rolling"."timestamp" AT TIME ZONE 'Europe/Tallinn') = 19
                )
                ORDER BY "rolling"."timestamp" DESC
            WITH DATA;
            
            ALTER TABLE public.ilm_ilm_rolling_8h
                OWNER TO kroonika;
            """
        cur.execute(query)
        stages['1'] = datetime.now() - start
        print(stages['1'].seconds)

        query = """
            DROP MATERIALIZED VIEW IF EXISTS public.ilm_ilm_rolling_1y;

            CREATE MATERIALIZED VIEW public.ilm_ilm_rolling_1y
            TABLESPACE pg_default
            AS
             SELECT "rolling"."timestamp", "rolling"."rolling_avg_1y"
                FROM
                    (SELECT 
                        "ilm_ilm"."timestamp", 
                        AVG("ilm_ilm"."airtemperature")
                            OVER 
                                (
                                    ORDER BY 
                                        "ilm_ilm"."timestamp" ASC 
                                    ROWS BETWEEN 4379 PRECEDING AND 4380 FOLLOWING
                                ) AS "rolling_avg_1y" FROM "ilm_ilm" 
                    ORDER BY 
                        "ilm_ilm"."timestamp" DESC) AS rolling
                WHERE EXTRACT(hour FROM "rolling"."timestamp" AT TIME ZONE 'Europe/Tallinn')=12
            WITH DATA;
            
            ALTER TABLE public.ilm_ilm_rolling_1y
                OWNER TO kroonika;
        """
        cur.execute(query)
        stages['2'] = datetime.now() - start
        print(stages['2'].seconds)

        query = """
            REFRESH MATERIALIZED VIEW public.ilm_ilm_rolling_1y
                WITH DATA;
        """
        cur.execute(query)
        stages['3'] = datetime.now() - start
        # print(stages['3'].seconds)
        query = """
            SELECT COUNT(*) FROM public.ilm_ilm_rolling_8h;
        """
        cur.execute(query)
        stages['4'] = datetime.now() - start
        print(cur.fetchone(), stages['4'].seconds)

        query = """
            SELECT COUNT(*) FROM public.ilm_ilm_rolling_1y;
        """
        cur.execute(query)
        stages['5'] = datetime.now() - start
        print(cur.fetchone(), stages['5'].seconds)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return

def update_lasthours(path, verbose=False, hours=72):
    # Kontrollime 72 tunni andmete olemasolu, vajadusel lisame
    for hour in range(71, -1, -1): # Viimase 72 tunni andmed
        observation_time = datetime.now() - timedelta(hours=hour)
        observation = check_observation_exists(observation_time, path)
        # print(observation_time, end=': ')
        if not observation:
            ilm_observation_veebist = utils.ilmaandmed_veebist(observation_time)
            # print(ilm_observation_veebist)
            if ilm_observation_veebist:
                id = insert_new_observations(ilm_observation_veebist, path)
                if verbose:
                    print(f'{ilm_observation_veebist["timestamp"]} lisatud {id}')
            else:
                if verbose:
                    print(f'{observation_time} uuendamine ebaõnnestus')
        else:
            # print('olemas.')
            pass

def update_forecast_logs(path='', verbose=False):
    yAPI = utils.YrnoAPI()
    y = yAPI.yrno_forecasts
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

def update_lasthour_log(path='', verbose=False):
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

def update_forecast_log_analyze():
    from .utils import forecast_log_analyze
    path = Path(__file__).resolve().parent.parent
    forecast_log_analyze.logs2bigdata(path)

if __name__ == '__main__':
    path = os.path.dirname(sys.argv[0])
    verbose = True
    # path = Path(__file__).resolve().parent.parent.parent
    # get_maxtimestamp()

    # Kustutame duplikaatread
    rows_deleted = delete_duplicate_observations(path, verbose)

    # Täiendame puudulikke kirjeid
    rows_updated = update_uncomplete_observations(path, verbose)
    rows_missing = update_missing_observations(path, verbose)
    update_lasthours(path, verbose, hours=72)

    # Tabelid mahukate arvutuste jaoks
    # update_maxmin(path)
    update_maxmin_rolling(path)

    # Ilmaennustuste logi
    update_forecast_logs(path, verbose)

    # Viimase täistunnimõõtmise logimine faili
    update_lasthour_log(path, verbose)

    # Moodustame uue ilmaennustuste kvaliteedi arvutuste faili
    update_forecast_log_analyze()


