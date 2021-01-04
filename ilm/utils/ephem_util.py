from datetime import datetime

import ephem
import pytz

U_ARR = u'\N{UPWARDS ARROW}'
D_ARR = u'\N{DOWNWARDS ARROW}'
SUN = u'\N{WHITE SUN WITH RAYS}'
MOON = u'\N{FIRST QUARTER MOON}'
DEGR = u'\N{DEGREE SIGN}'

tz_EE = pytz.timezone(pytz.country_timezones['ee'][0])
utc = pytz.utc

def to_local(ephem_date):
    date_utc = utc.localize(
        datetime.strptime(str(ephem_date), '%Y/%m/%d %H:%M:%S'),
        utc
    )
    return date_utc.astimezone(tz_EE)

def get_direction(angle):
    angle = int(angle)
    directions = ['N', 'NW', 'W', 'SW', 'S', 'SE', 'E', 'NE']
    angle = (angle + 360) if (angle // 360) < 0 else angle
    return directions[angle // 45 % 8]

def get_observer(date_loc=datetime.now(tz=tz_EE)):
    LON, LAT, ELEV = '26:3:30.23', '57:46:13.08', 75
    date_utc = date_loc.astimezone(utc)
    observer = ephem.Observer()
    observer.lon = LON
    observer.lat = LAT
    observer.elevation = ELEV
    observer.date = date_utc
    return observer

def get_sun_str(date_loc, observer=None):
    if not observer:
        observer = get_observer(date_loc)
    s = ephem.Sun()
    s.compute(observer)
    az, alt = s.az, s.alt
    # print(
    #     str(az).split(':')[0],
    #     get_direction(str(az).split(':')[0]),
    #     str(alt).split(':')[0],
    #     to_local(observer.next_rising(s)),
    #     # to_local(observer.previous_rising(s)),
    #     to_local(observer.next_setting(s)),
    #     # to_local(observer.previous_s(etting(s))
    # )
    if alt > 0:
        sun_string = f"{str(alt).split(':')[0]}{DEGR}@{str(az).split(':')[0]}{DEGR}({get_direction(str(az).split(':')[0])}) " +\
                     f"{D_ARR}{to_local(observer.next_setting(s)):%H:%M:%S}"
    else:
        sun_string = f"{U_ARR}{to_local(observer.next_rising(s)):%H:%M:%S}"
    # print(SUN, sun_string)
    sun_string = f'{SUN} {sun_string}'
    return sun_string

def get_moon_str(date_loc, observer=None):
    if not observer:
        observer = get_observer(date_loc)
    m = ephem.Moon()
    m.compute(observer)
    az, alt = m.az, m.alt
    # print(
    #     m.az,
    #     m.alt,
    #     m.phase,
    #     observer.next_rising(m),
    #     observer.previous_rising(m),
    #     observer.next_setting(m),
    #     observer.previous_setting(m)
    # )
    if alt > 0:
        moon_string = \
            f"{int(round(m.phase, 0))}% " +\
            f"{str(alt).split(':')[0]}{DEGR}" +\
            f"@{str(az).split(':')[0]}{DEGR}({get_direction(str(az).split(':')[0])}) " +\
            f"{D_ARR}{to_local(observer.next_setting(m)):%H:%M:%S}"
    else:
        moon_string = f"{U_ARR}{to_local(observer.next_rising(m)):%H:%M:%S}"
    moon_string = f'{MOON} {moon_string}'
    return moon_string

def main():
    # d = datetime(2021,1,2,8,8,33)
    # s9a = get_observer()
    sun = get_sun_str()
    moon = get_moon_str()

if __name__ == "__main__":
    main()