#!/usr/bin/python
from datetime import datetime, timedelta
import psycopg2

from pytz import timezone
import pytz

from config import config

def utc2eesti_aeg(dt):
    eesti_aeg = timezone('Europe/Tallinn')
    return dt.astimezone(eesti_aeg)


# The following connect() function connects to the suppliers database and prints out the PostgreSQL database version.
def connect():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = config()

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
def get_maxtimestamp():
    """ query maxdate from the ilm_ilm table """
    conn = None
    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute("SELECT max(timestamp) FROM ilm_ilm")
        print("Viimane kanne: ", cur.rowcount)

        row = cur.fetchone()
        d = pytz.timezone('Europe/Tallinn').localize(datetime.now())

        while row is not None:
            # print(row)
            print(row[0], (d - row[0]).seconds)
            row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

# Mõõtmistulemuse olemasolu kontroll aja järgi
def check_observation_exists(dt):
    """ query if exists timestamp from the ilm_ilm table """
    conn = None
    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()

        condition_y = f"date_part('year', timestamp) = {dt.year}"
        condition_m = f"date_part('month', timestamp) = {dt.month}"
        condition_d = f"date_part('day', timestamp) = {dt.day}"
        condition_h = f"date_part('hour', timestamp) = {dt.hour}"
        condition = ' and '.join([condition_y, condition_m, condition_d, condition_h])
        query = f'SELECT timestamp FROM ilm_ilm WHERE {condition}'

        cur.execute(query)
        print("Kandeid: ", cur.rowcount)

        row = cur.fetchone()

        eesti_aeg = timezone('Europe/Tallinn')
        print(dt)
        while row is not None:
            d = row[0]
            print(f'PostgreSQL datetime          : {d}')
            print(f'PostgreSQL timezone          : {d.tzname()}')
            print(f'PostgreSQL offset UTC ajaga  : {d.utcoffset()}')
            print(f'PostgreSQL Eesti aeg         : {utc2eesti_aeg(d)}')
            # print((d - row[0]).seconds)
            row = cur.fetchone()

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return cur.rowcount

# Kustutab topeltkirjed
def delete_duplicate_observations():
    """ delete part by part id """
    conn = None
    rows_deleted = 0
    try:
        # read database configuration
        params = config()
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
    print(f'Kustutati: {rows_deleted}')
    return rows_deleted


if __name__ == '__main__':
    get_maxtimestamp()
    check_observation_exists(datetime.now() - timedelta(hours=1))
    check_observation_exists(datetime(2019, 9, 1, 12))
    delete_duplicate_observations()
