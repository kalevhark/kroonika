from pathlib import Path

if __name__ == "__main__":
    import os
    import django
    from django.test.utils import setup_test_environment

    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    setup_test_environment()
    from django.conf import settings
    UTIL_DIR = Path('.')
else:
    from django.conf import settings
    UTIL_DIR = settings.BASE_DIR / 'wiki' / 'utils'

# Build paths inside the project like this: BASE_DIR / 'subdir'.

import csv
import json
import re
import time

from django.contrib.auth.models import User

import folium
import pyproj
import requests
import shapefile
from shapely.geometry.polygon import Polygon

from wiki.models import Kaart, Kaardiobjekt, Objekt

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
DEFAULT_CENTER = (57.7769268, 26.0308911) # {'lon': 26.0308911, 'lat': 57.7769268} # Jaani kiriku koordinaadid
DEFAULT_MAP = Kaart.objects.filter(aasta='2021').first() # Vaikimisi Stamen Toner internetikaart
DEFAULT_MAP_ZOOM_START = 17
DEFAULT_MIN_ZOOM = 13

GEOJSON_STYLE = {
    'H': {'fill': 'red', 'color': 'red', 'weight': 1}, # hoonestus
    'A': {'fill': None, 'color': 'red', 'weight': 3}, # ala
    'M': {'fill': None, 'color': 'red', 'weight': 3}, # muu
}

# crs to degree converter init
proj = pyproj.Transformer.from_crs(3301, 4326, always_xy=True)

def split_address(aadress):
    l2hiaadress = aadress.split(' ')
    erisus = re.compile('(\.|Julius|Ernst|Alfred)')
    if re.search(erisus, l2hiaadress[0]):
        street = l2hiaadress[1].strip()
    else:
        street = l2hiaadress[0].strip()
    housenumber = l2hiaadress[-1].strip()
    # print(street, housenumber)
    return street, housenumber

def shp_crs_to_degree(coordinates, reverse=False):
    x1, y1 = coordinates
    x2, y2 = proj.transform(x1, y1)
    x2 = round(x2, 7)
    y2 = round(y2, 7)
    if reverse:
        return (y2, x2) # QGIS annab vastupidi järjestuses
    else:
        return (x2, y2)

###
# Abifunktsioonid haldamiseks
###

# Loeb kaardikihi shp failist andmebaasi
def read_shp_to_db(aasta):
    kaart = Kaart.objects.filter(aasta=aasta).first()
    if kaart:
        with shapefile.Reader(aasta) as sf:
            # existing Shape objects
            for shaperec in sf.iterShapeRecords():
                rec = shaperec.record.as_dict()
                geometry = shaperec.shape.__geo_interface__
                kontroll = Kaardiobjekt.objects.filter(kaart=kaart, geometry=geometry)
                print(rec, end=' ')
                if kontroll:
                    print('olemas')
                else:
                    print('lisame:')
                    o = Kaardiobjekt.objects.create(kaart=kaart, geometry=geometry, **rec)
                    print(o)
    else:
        print('Sellist kaarti ei ole andmebaasis')

# Loeb kaardid csv failist andmebaasi
def read_kaart_csv_to_db():
    user = User.objects.get(id=1)
    with open(UTIL_DIR / 'kaart.csv', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', quotechar="'")
        for row in reader:
            # print(row)
            o = Kaart.objects.create(created_by=user, **row)
            print(o)

# Loeb kaardid csv failist andmebaasi
def read_kaardiobjekt_csv_to_db(aasta):
    # Kaardiobjekt.objects.all().delete()
    user = User.objects.get(id=1)
    kaart = Kaart.objects.filter(aasta=aasta).first()
    with open(UTIL_DIR / 'kaardiobjekt.csv', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', quotechar="'", escapechar='|')
        for row in reader:
            # print(row)
            geometry = json.loads(row['geometry'])
            o = Kaardiobjekt.objects.create(
                kaart=kaart,
                tyyp=row['tyyp'],
                tn=row['tn'],
                nr=row['nr'],
                geometry=geometry,
                created_by=user
            )
            print(o)

# Kirjutab andmebaasist kaardikihi shp faili
def write_db_to_shp(aasta='1912'):
    kaart = Kaart.objects.filter(aasta=aasta).first()
    if kaart:
        kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart, objekt__isnull=False)
        print(kaardiobjektid)
        if kaardiobjektid:
            with shapefile.Writer(aasta + '_uus') as w:
                with shapefile.Reader(aasta) as r:
                    w.fields = r.fields[1:]  # skip first deletion field
                for kaardiobjekt in kaardiobjektid:
                    w.record(
                        tn=kaardiobjekt.tn,
                        nr=kaardiobjekt.nr,
                        lisainfo=kaardiobjekt.lisainfo,
                        tyyp=kaardiobjekt.tyyp,
                        kroonika_objekt=kaardiobjekt.objekt.id
                    )
                    w.shape(kaardiobjekt.geometry)
                print(w.recNum, w.shpNum)
            # Lisame projektsioonifaili
            with open(f'{aasta}.prj') as r:
                with open(f'{aasta}_uus.prj', 'w') as w:
                    w.write(r.read())

# Hoonestuse andmed OpenStreetMap kaardilt OverPass API abil
def get_osm_data(asukoht=None):
    if asukoht:
        # print(asukoht, end=' ')
        street, housenumber = split_address(asukoht)
        # Pärime andmed operpass APIst
        overpass_query = f"""
        [out:json][timeout:25];
        area['admin_level'='2']['name'='Eesti']->.searchArea;
        area['admin_level'='9']['name'='Valga linn'](area.searchArea)->.searchArea; 
        ( 
            nwr["building"]["addr:street"~"{street}"]["addr:housenumber"="{housenumber}"](area.searchArea); 
        );
        out body center;
        >;
        out center;
        """
        attempts = 3
        elements = None

        while attempts > 0:
            response = requests.get(OVERPASS_URL, params={'data': overpass_query})
            try:
                data = response.json()
                elements = data['elements']
                break
            except:
                # print('viga!')
                attempts -= 1
                time.sleep(3)
                # return # ei saadud korrektset vastust

        if elements:
            # Kaardipildi keskkoha koordinaadid
            center = elements[0]['center']
            # print(center)
            # center = (center['lat'], center['lon'])
            # print(json.dumps((center['lon'], center['lat'])))

            # Eristame kõik sama aadressiga hooned maaüksusel loendisse
            ways = [
                el['nodes']
                for el
                in elements
                if el['type'] == 'way'
            ]

            # Loome sõnastiku kõigist käänupunktidest maaüksusel
            nodes = {
                # el['id']: (el['lat'], el['lon'])
                el['id']: (el['lon'], el['lat'])
                for el
                in elements
                if el['type'] == 'node'
            }

            # Sorteerime käänupunktid hoonete kaupa loendiks
            nodes_sets = [] # list hoonete kaupa
            for way in ways:
                nodes_in_way = [] # ühe hoone käänupunktid
                for node in way:
                    nodes_in_way.append(nodes[node])
                nodes_sets.append(nodes_in_way)

            geometry = {
                'type': 'Polygon',
                'coordinates': nodes_sets
            }
            return geometry #, center
        else:
            pass # print('ei leidnud')

# katastriüksuse andmed aadressi järgi Maa-ameti andmetest
def get_shp_data(asukoht):
    if asukoht:
        street, housenumber = split_address(asukoht)
        with shapefile.Reader("SHP_KATASTRIYKSUS_VALGA", encoding="latin1") as sf:
            for rec in sf.iterShapeRecords():
                if street in rec.record.L_AADRESS.split(' ') and housenumber in rec.record.L_AADRESS.split(' '):
                    nodes = [
                        shp_crs_to_degree(el)
                        for el
                        in rec.shape.points
                    ]
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': [nodes]
                    }
                    return geometry

# Loeb katastriyksuse failist ja leiab kas on kattuvusi andmebaasi kaardiobjektidega
def shp_match_db():
    ignore_maps = ['2021', '1683']
    erisus = re.compile('( tn| pst| tänav)')
    objs = Kaardiobjekt.objects.exclude(kaart__aasta__in=ignore_maps).filter(tyyp__exact='H')
    with shapefile.Reader("SHP_KATASTRIYKSUS_VALGA", encoding="latin1") as sf:
        with open('l2hiaadressid.txt', 'w') as af:
            total = len(sf.shapes())
            n = 0
            for rec in sf.iterShapeRecords():
                if rec.record.SIHT1 != "Transpordimaa":
                    n += 1
                    l_aadress = rec.record.L_AADRESS
                    l_aadress = re.sub(erisus, '', l_aadress.split('//')[0])
                    kinnitus = save_current_data(l_aadress)
                    af.write(kinnitus + '\n')
                    print(f'{n}/{total}:{kinnitus}')
                    continue # TODO: ajutiselt siin katkestame
                    points = rec.shape.points
                    parts = rec.shape.parts
                    endpoint = len(points) if len(parts)==1 else parts[1]
                    nodes = [
                        shp_crs_to_degree(el)
                        for el
                        in points[:endpoint] # juhuks kui 'aukudega' my
                    ]
                    poly = Polygon(nodes)
                    if poly.is_valid:
                        for obj in objs:
                            s = obj.geometry['coordinates'][0]
                            p = Polygon(s)
                            if p.intersects(poly):
                                try:
                                    kattuvus = round(p.intersection(poly).area/p.area, 2)
                                    if kattuvus > 0.2:
                                        print(rec.record.L_AADRESS, obj, kattuvus)
                                except:
                                    print(rec.record.L_AADRESS, poly.is_valid, p.is_valid)
                    else:
                        print('Vigane my:', rec.record.L_AADRESS)
                        print(rec.shape.parts)

# Salvestame andmebaasi värsked andmed OpenStreetMapist ja Maa-ameti andmefailist
def save_current_data(asukoht):
    # Valime aluseks OpenStreetMapi kaardi
    kaart = Kaart.objects.get(id=2)
    tn, nr = split_address(asukoht)
    kinnitus = asukoht

    # Lisame katastriükuse ala
    geometry = get_shp_data(asukoht)
    if geometry:
        kaardiobjekt = Kaardiobjekt.objects.create(
            kaart=kaart,
            tyyp='A',
            geometry=geometry,
            tn=tn, nr=nr
        )
        # print('andmebaasi: ', kaardiobjekt, 'A')
        kinnitus += ' A'

    # Lisame hoonestuse
    geometry = get_osm_data(asukoht)
    if geometry:
        kaardiobjekt = Kaardiobjekt.objects.create(
            kaart=kaart,
            tyyp='H',
            geometry=geometry,
            tn=tn, nr=nr
        )
        # print('andmebaasi: ', kaardiobjekt, 'H')
        kinnitus += ' H'
    return kinnitus

# Kattuvate kujundite leidmiseks 2021 objekti katastriüksuse alusel
def find_intersections(id=1):
    objekt = Objekt.objects.get(id=id)
    # Millise objektiga võrrelda
    obj = Kaardiobjekt.objects.filter(objekt=objekt, tyyp__exact='H').first()
    # aasta = obj.kaart.aasta
    shp = obj.geometry['coordinates'][0]
    poly = Polygon(shp)

    # Millistest objektidest otsida
    objs = Kaardiobjekt.objects.exclude(kaart__aasta=obj.kaart.aasta)
    for o in objs:
        s = o.geometry['coordinates'][0]
        p = Polygon(s)
        if poly.intersects(p):
            new = '+' if o.objekt else '*'
            print(new, objekt, obj, o)

def update_objekt_from_csv():
    with open('objekt.csv', encoding='utf-8', newline='') as csvfile:
        reader = csv.DictReader(csvfile, fieldnames=['id', 'tyyp', 'nimi', 'asukoht', 'kir', 'objs', 'muuta'], delimiter=';')
        for row in reader:
            if row['muuta'] == 'X':
                obj = Objekt.objects.filter(id=row['id']).first()
                if obj:
                    print(row['asukoht'], '->', obj.asukoht)


###
# Kaardivaadete loomiseks
###

# Konkreetse objekti erinevate aastate kaardid koos
def make_objekt_leaflet_combo(objekt_id=1):
    obj = Objekt.objects.get(id=objekt_id)
    # Kõigi kaartide ids, kus objekt märgitud: tulemus: <QuerySet ['1', '2', '3']>
    kaart_ids = obj.kaardiobjekt_set.values_list('kaart__id', flat=True)

    if kaart_ids:
        kaardid = Kaart.objects.filter(id__in=kaart_ids)
        gone = DEFAULT_MAP.id not in kaart_ids # Objekti kaasajal pole?
        hiliseim_kaart_aasta = max([kaart.aasta for kaart in kaardid])

        if gone:
            # Lisame vaate, millel näitame virtuaalset asukohta tänapäeval
            kaardid = kaardid | Kaart.objects.filter(id=DEFAULT_MAP.id)

        # Loome aluskaardi
        map = folium.Map(
            location=DEFAULT_CENTER,  # NB! tagurpidi: [lat, lon],
            zoom_start=DEFAULT_MAP_ZOOM_START,
            min_zoom=DEFAULT_MIN_ZOOM,
            zoom_control=False,
            # control_scale=True,
            tiles=None,
        )
        # map_name = map.get_name()

        feature_group = {}
        for kaart in kaardid:
            aasta = kaart.aasta

            feature_group[aasta] = folium.FeatureGroup(
                name=aasta,
                overlay=False
            )
            if kaart == DEFAULT_MAP and gone:
                folium.TileLayer(
                    location=map.location,
                    name=aasta,
                    tiles="Stamen Toner",
                    zoom_start=DEFAULT_MAP_ZOOM_START,
                    min_zoom=DEFAULT_MIN_ZOOM
                ).add_to(feature_group[aasta])
            else:
                kaardiobjektid = obj.kaardiobjekt_set.filter(kaart=kaart)
                if kaardiobjektid[0].geometry:
                    map.location = kaardiobjektid[0].centroid
                folium.TileLayer(
                    location=map.location,
                    name=aasta,
                    tiles=kaart.tiles,
                    zoom_start=DEFAULT_MAP_ZOOM_START,
                    min_zoom=DEFAULT_MIN_ZOOM,
                    attr=f'{kaart.__str__()}<br>{kaart.viited.first()}',
                ).add_to(feature_group[aasta])

                # lisame vektorkihid
                for kaardiobjekt in kaardiobjektid:
                    geometry = kaardiobjekt.geometry
                    tyyp = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
                    name = f'{kaardiobjekt.__str__()} ({dict(Kaardiobjekt.TYYP)[tyyp].lower()})'
                    feature_collection = {
                        "type": "FeatureCollection",
                        "name": name,
                        "features": [geometry]
                    }
                    style = GEOJSON_STYLE[tyyp]
                    f = json.dumps(feature_collection)
                    folium.GeoJson(
                        f,
                        name=name,
                        style_function=lambda x: style
                    ).add_to(feature_group[aasta])
                    if kaart.aasta == hiliseim_kaart_aasta and gone:
                        folium.GeoJson(
                            f,
                            name=name,
                            style_function=lambda x: style
                        ).add_to(feature_group[DEFAULT_MAP.aasta])

            # Lisame kaardi leaflet combosse
            feature_group[aasta].add_to(map)
            # print(feature_group[aasta].get_name())

        # Piirid tänapäeval
        style1 = {'fill': None, 'color': '#00FFFF', 'weight': 5}
        with open(UTIL_DIR / 'geojson' / "piirid.geojson") as gf:
            src = json.load(gf)
            folium.GeoJson(src, name="piirid", style_function=lambda x: style1).add_to(map)

        # Tänavatevõrk tänapäeval
        style2 = {'fill': None, 'color': 'red', 'weight': 2}
        with open(UTIL_DIR / 'geojson' / "teedev6rk_2021.geojson") as gf:
            src = json.load(gf)
            folium.GeoJson(src, name="teedevõrk", style_function=lambda x: style2).add_to(map)

        # Lisame kihtide kontrolli
        folium.LayerControl().add_to(map)

        # Legendi lisamiseks TODO: Hetkel ei kasuta
        # import branca
        #
        # legend_html = '''
        # {% macro html(this, kwargs) %}
        # <div style="
        #     position: fixed;
        #     bottom: 50px;
        #     left: 50px;
        #     width: 250px;
        #     height: 80px;
        #     z-index:9999;
        #     font-size:14px;
        #     ">
        #     <p><a style="color:#000000;font-size:150%;margin-left:20px;">&diams;</a>&emsp;[aasta]</p>
        # </div>
        # <div style="
        #     position: fixed;
        #     bottom: 50px;
        #     left: 50px;
        #     width: 150px;
        #     height: 80px;
        #     z-index:9998;
        #     font-size:14px;
        #     background-color: #ffffff;
        #
        #     opacity: 0.7;
        #     ">
        # </div>
        # <script>
        #
        # </script>
        # {% endmacro %}
        # '''
        # legend = branca.element.MacroElement()
        # legend._template = branca.element.Template(legend_html)
        # map.get_root().add_child(legend)

        # map.save("index.html")
        map_html = map._repr_html_()

        # v2ike h2kk, mis muudab vertikaalset suurust
        map_html = map_html.replace(';padding-bottom:60%;', ';padding-bottom:100%;', 1)
        # with open(f"ajutine_{objekt_id}-{kaart_id}.html", "w") as f:
        #     pass # f.write(map_html)
        # map.save(f"ajutine_{objekt_id}")
        return map_html

if __name__ == "__main__":
    # read_kaardiobjekt_csv_to_db('2021')
    read_shp_to_db(aasta='1912') # Loeb kaamap.save("map.html")rdikihi shp failist andmebaasi
    # write_db_to_shp(aasta='1905') # Kirjutab andmebaasist kaardikihi shp faili
    # save_current_data() # Salvestame andmebaasi värsked andmed OpenStreetMapist ja Maa-ameti andmefailist
    # find_intersections()
    # update_objekt_from_csv()
    # shp_match_db()

"""
https://tools.ietf.org/html/rfc7946
A GeoJSON FeatureCollection:
{
   "type": "FeatureCollection",
   "features": [{
       "type": "Feature",
       "geometry": {
           "type": "Point",
           "coordinates": [102.0, 0.5]
       },
       "properties": {
           "prop0": "value0"
       }
   }, {
       "type": "Feature",
       "geometry": {
           "type": "LineString",
           "coordinates": [
               [102.0, 0.0],
               [103.0, 1.0],
               [104.0, 0.0],
               [105.0, 1.0]
           ]
       },
       "properties": {
           "prop0": "value0",
           "prop1": 0.0
       }
   }, {
       "type": "Feature",
       "geometry": {
           "type": "Polygon",
           "coordinates": [
               [
                   [100.0, 0.0],
                   [101.0, 0.0],
                   [101.0, 1.0],
                   [100.0, 1.0],
                   [100.0, 0.0]
               ]
           ]
       },
       "properties": {
           "prop0": "value0",
           "prop1": {
               "this": "that"
           }
       }
   }]
}
"""