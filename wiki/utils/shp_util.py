import json
from pathlib import Path
import re
import time

if __name__ == "__main__":
    import os
    import django
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    # setup_test_environment()
    from django.conf import settings
    UTIL_DIR = Path(__file__).resolve().parent
    print('Töökataloog:', UTIL_DIR)
    # Build paths inside the project like this: UTIL_DIR / 'subdir'.
else:
    from django.conf import settings
    UTIL_DIR = settings.BASE_DIR / 'wiki' / 'utils'

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

from branca.element import CssLink, Element, Figure, JavascriptLink, MacroElement

import folium
from folium.features import GeoJsonPopup, GeoJsonTooltip

import jinja2
import pyproj
import requests
import shapefile
from shapely.geometry.polygon import Polygon

from wiki.models import Kaart, Kaardiobjekt, Objekt

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

DEFAULT_CENTER = settings.DEFAULT_CENTER
DEFAULT_MAP_AASTA = settings.DEFAULT_MAP_AASTA
DEFAULT_MAP = Kaart.objects.get(aasta=settings.DEFAULT_MAP_AASTA) # Vaikimisi OpenStreetMap
DEFAULT_MAP_ZOOM_START = settings.DEFAULT_MAP_ZOOM_START
DEFAULT_MIN_ZOOM = settings.DEFAULT_MIN_ZOOM

# FUCHSIA = '#FF00FF'
# OBJEKT_COLOR = '#2b5797'

GEOJSON_STYLE = settings.GEOJSON_STYLE
LEAFLET_DEFAULT_CSS = settings.LEAFLET_DEFAULT_CSS
LEAFLET_DEFAULT_JS = settings.LEAFLET_DEFAULT_JS
# LEAFLET_DEFAULT_HEADER = settings.LEAFLET_DEFAULT_HEADER
LEAFLET_DEFAULT_HEADER = Element(
    '<frame-options policy="SAMEORIGIN" />'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Raleway">'
    '<style>'
    '.kaart-control-layers,'
    '.kaardiobjekt-tooltip,'
    '.kaart-tooltip {'
    '  font-size: 14px;'
    '  font-family: "Raleway", sans-serif;'
    '}'
    '</style>'
)

# Asendus stamen_toner kaartidele
STAMEN_TONER_NEW = {
    'tiles': 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    'attr': 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
}

# crs to degree converter init
# Kasutatav CRS: EPSG:3301 - Estonian Coordinate System of 1997 - Projected
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
def get_kattuvus(kaardiobjekt_geometry, shp_geometry):
    shape = kaardiobjekt_geometry['coordinates'][0]
    kaardiobjekt_polygon = Polygon(shape)
    shape = shp_geometry['coordinates'][0]
    shp_polygon = Polygon(shape)
    if kaardiobjekt_polygon.is_valid and shp_polygon.is_valid:
        if kaardiobjekt_polygon.intersects(shp_polygon):
            kattuvus = round(kaardiobjekt_polygon.intersection(shp_polygon).area/kaardiobjekt_polygon.area, 2)
            return kattuvus

# Loeb kaardikihi shp failist andmebaasi
def read_shp_to_db(aasta, do=False):
    kaart = Kaart.objects.filter(aasta=aasta).first()
    if kaart:
        # analüüsime olemasolevaid objekte
        print('kaardiobjekte kokku:', Kaardiobjekt.objects.filter(kaart=kaart).count())
        print('sh seotud:', Kaardiobjekt.objects.filter(kaart=kaart).filter(objekt__isnull=False).count())
        if do:
            # kustutame objektiga sidumata kardiobjektid
            d = Kaardiobjekt.objects.filter(kaart=kaart).filter(objekt__isnull=True).delete()
            print('kustutatud:', d)
            # kysime valitud kaardi kaardiobjektid
            kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart)
            lisatud = 0
            olemas = 0
            vigu = 0
            with open(UTIL_DIR / f'{aasta}.shp', 'rb') as shp_file:
                with open(UTIL_DIR / f'{aasta}.dbf', 'rb') as dbf_file:
                    with shapefile.Reader(shp=shp_file, dbf=dbf_file) as sf:
                        # existing Shape objects
                        for shaperec in sf.iterShapeRecords():
                            rec = shaperec.record.as_dict()
                            geometry = shaperec.shape.__geo_interface__
                            tyyp = rec['tyyp']
                            if tyyp not in ['A', 'H']:
                                print('vigane', rec)
                                vigu += 1
                                continue
                            # kontrollitakse, kas selliste piiridega kaardiobjekt on juba andmebaasis
                            kattuv = False
                            for kaardiobjekt in kaardiobjektid:
                                kattuvus = get_kattuvus(kaardiobjekt.geometry, geometry)
                                if kattuvus and kattuvus > 0.2 and kaardiobjekt.tyyp == tyyp:
                                    kattuv = True
                                    ko = kaardiobjekt
                                    break
                            if kattuv:
                                print('olemas:', kattuvus, rec, ko)
                                olemas += 1
                            else:
                                lisatud += 1
                                o = Kaardiobjekt.objects.create(kaart=kaart, geometry=geometry, **rec)
                                print('lisame:', rec, o)
            print(f'Olemas {olemas}, lisatud {lisatud}, vigu {vigu}')
    else:
        print('Sellist kaarti ei ole andmebaasis')

# Kirjutab andmebaasist kaardikihi shp faili
def write_db_to_shp(aasta='1912'):
    kaart = Kaart.objects.filter(aasta=aasta).first()
    if kaart:
        print(os.getcwd())
        # kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart, objekt__isnull=False)
        kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart)
        print(kaardiobjektid)
        if kaardiobjektid:
            with shapefile.Writer(aasta + '_uus') as w:
                with shapefile.Reader('shp_template') as r:
                    w.fields = r.fields[1:]  # skip first deletion field
                for kaardiobjekt in kaardiobjektid:
                    objekt = kaardiobjekt.objekt.id if kaardiobjekt.objekt else None
                    w.record(
                        tn=kaardiobjekt.tn,
                        nr=kaardiobjekt.nr,
                        lisainfo=kaardiobjekt.lisainfo,
                        tyyp=kaardiobjekt.tyyp,
                        kroonika_objekt=objekt
                    )
                    w.shape(kaardiobjekt.geometry)
                print(w.recNum, w.shpNum)
            # Lisame projektsioonifaili
            with open('shp_template.prj') as r:
                with open(f'{aasta}_uus.prj', 'w') as w:
                    w.write(r.read())

# Hoonestuse andmed OpenStreetMap kaardilt OverPass API abil
def get_osm_data(street=None, housenumber=None, country='Eesti', admin_level='9', city='Valga linn'):
    if street and housenumber:
        # query = """
        #         (
        #   way(id: 214327417, 228359022, 228899964);
        # );
        # """ # Kesk 12 hooned

        # Päring aadressi kohta street='Sulevi', housenumber='9a'
        query = f"""
        area['admin_level'='2']['name'='{country}']->.searchArea;
        area['admin_level'='{admin_level}']['name'='{city}'](area.searchArea)->.searchArea;
        (
            nwr["building"]["addr:street"~"{street}"]["addr:housenumber"="{housenumber}"](area.searchArea);
        );
        """

        # K6ik asumid Valga linnas
        # query = f"""
        # area['admin_level'='2']['name'='Eesti']->.searchArea;
        # area['admin_level'='9']['name'='Valga linn'](area.searchArea)->.searchArea;
        # nwr["place"="quarter"](area.searchArea);
        # """

        # Pärime andmed operpass APIst
        overpass_query = f"""
        [out:json][timeout:25];
        {query}
        out body center;
        >;
        out skel qt;
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
            print(json.dumps(elements, indent=2))
            # Kaardipildi keskkoha koordinaadid
            # center = elements[0]['center']
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
            print('H', json.dumps(geometry))
            return geometry #, center

# Hoonestuse andmed OpenStreetMap kaardilt OverPass API abil
def get_osm_data_quarter(quarter=None, country='Eesti', admin_level='9', city='Valga linn'):
    quarter_name = f"['name'='{quarter}']" if quarter is not None else ''
    # K6ik asumid Valga linnas
    query = f"""
    area['admin_level'='2']['name'={country}]->.searchArea;
    area['admin_level'='{admin_level}']['name'='{city}'](area.searchArea)->.searchArea;
    nwr["place"="quarter"]{quarter_name}(area.searchArea);
    """

    # Pärime andmed operpass APIst
    overpass_query = f"""
    [out:json][timeout:25];
    {query}
    out body center;
    >;
    out skel qt;
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
        # print(json.dumps(elements, indent=2))
        if quarter:
            # Kaardipildi keskkoha koordinaadid
            # center = elements[0]['center']
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
                # nodes_in_way = [] # ühe hoone käänupunktid
                for node in way:
                    # nodes_in_way.append(nodes[node])
                    nodes_sets.append(nodes[node])

            geometry = {
                'type': 'Polygon',
                'coordinates': nodes_sets
            }
            print('A', quarter, json.dumps(geometry))
        else:
            quarters = [
                el['tags']['name']
                for el
                in elements
                if (el['type'] == 'node') and ('tags' in el.keys())
            ]
            print(quarters)
            for quarter in quarters:
                get_osm_data_quarter(quarter=quarter)

# katastriüksuse andmed aadressi v6i katastrinumbri järgi Maa-ameti andmetest
def get_shp_data(asukoht=None, kataster=None):
    # asukoht aadress 'Sulevi 9a'
    # kataster katastritunnus '85401:016:0510'
    # asukoht aadress 'Kraavikalda 19'
    # kataster '79517:019:0003'

    shp = "wiki\\utils\\SHP_KATASTRIYKSUS_VALGA" # ainult Valga linn
    shp = "wiki\\utils\\Tartu linn" # ainult Tartu linn
    with shapefile.Reader(shp, encoding="latin1") as sf:
        for rec in sf.iterShapeRecords():
            if asukoht:
                street, housenumber = split_address(asukoht)
                if street in rec.record.l_aadress.split(' ') and housenumber in rec.record.l_aadress.split(' '):
                    points = rec.shape.points
                    parts = rec.shape.parts
                    # print(parts)
                    nodes = [
                        shp_crs_to_degree(el)
                        for el
                        in rec.shape.points
                    ]
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': [nodes]
                    }
                    print('A', rec.record.l_aadress, json.dumps(geometry))
            if kataster:
                if kataster == rec.record.tunnus:
                    points = rec.shape.points
                    parts = rec.shape.parts
                    nodes = [
                        shp_crs_to_degree(el)
                        for el
                        in rec.shape.points
                    ]
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': [nodes]
                    }
                    print('A', rec.record.tunnus, json.dumps(geometry))


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
                    # l_aadress = rec.record.L_AADRESS
                    # l_aadress = re.sub(erisus, '', l_aadress.split('//')[0])
                    # kinnitus = save_current_data(l_aadress)
                    # af.write(kinnitus + '\n')
                    # print(f'{n}/{total}:{kinnitus}')
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

# Loeb kaardiobjekti andmed ja leiab kas on kattuvusi teiste kaartide kaardiobjektidega
def kaardiobjekt_match_db(kaardiobjekt_id):
    kaardiobjekt = Kaardiobjekt.objects.get(id=kaardiobjekt_id)
    shape = kaardiobjekt.geometry['coordinates'][0]
    polygon = Polygon(shape)
    ignore_maps = ['1683', kaardiobjekt.kaart.aasta]
    objs = Kaardiobjekt.objects.exclude(kaart__aasta__in=ignore_maps).filter(tyyp__exact='H')
    if polygon.is_valid:
        kaardiobjekt_match = []
        for obj in objs:
            s = obj.geometry['coordinates'][0]
            p = Polygon(s)
            if p.intersects(polygon):
                try:
                    kattuvus = round(p.intersection(polygon).area/p.area, 2)
                    if kattuvus > 0.2:
                        if obj.objekt:
                            seotud = obj.objekt.nimi
                        else:
                            seotud = '****'
                        # print(obj.kaart.aasta, obj.id, obj.tn, obj.nr, obj.lisainfo, kattuvus, '->', seotud)
                        kaardiobjekt_match.append({'kaardiobjekt': obj, 'kattuvus': kattuvus})
                except:
                    print(obj, polygon.is_valid, p.is_valid)
        return kaardiobjekt_match
    else:
        print('Vigane my:', kaardiobjekt)

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

# Kaardiobjekt geojson failideks
def kaardiobjektid2geojson():
    kaardid = Kaart.objects.exclude(tiles__exact='').order_by('aasta')
    for kaart in kaardid:
        if kaart == DEFAULT_MAP:  # kaasaja kaardil kaardiobjekte liiga palju
            kaardiobjektid = Kaardiobjekt.objects. \
                filter(kaart=kaart). \
                filter(objekt__isnull=False). \
                filter(objekt__gone__exact=False)
        else:
            kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart)
        if kaardiobjektid:
            geojson = {
                "type": "FeatureCollection",
                "name": f'{kaart.aasta} kaardiobjektid',
                "features": []
            }
            for kaardiobjekt in kaardiobjektid:
                objekt = kaardiobjekt.objekt
                tooltip = get_kaardiobjekt_data4tooltip(kaardiobjekt)
                popup = get_kaardiobjekt_data4tooltip(kaardiobjekt)
                status = ''
                href = ''
                if objekt:
                    tooltip = get_object_data4tooltip(objekt)
                    popup = get_object_data4popup(kaardiobjekt)
                    status = 'E'
                    href = objekt.get_absolute_url()
                    if objekt.gone:
                        status = 'H'
                feature = {
                    "type": "Feature",
                    "properties": {
                        "tooltip": tooltip,
                        "popup": popup,
                        "tyyp": f'{kaardiobjekt.tyyp}{status}',
                        "href": href
                    },
                    "geometry": kaardiobjekt.geometry
                }
                geojson['features'].append(feature)

            with open(UTIL_DIR / 'geojson' / f'kaardiobjektid_{kaart.aasta}.geojson', 'w', encoding='utf8') as f:
                json.dump(geojson, f)

###
# Kaardivaadete loomiseks
###

# # https://github.com/prhbrt/folium-jsbutton
# class JsButton(MacroElement):
#     """
#     Button that executes a javascript function.
#     Parameters
#     ----------
#     title : str
#          title of the button, may contain html like
#     function : str
#          function to execute, should have format `function(btn, map) { ... }`
#
#     See https://github.com/prinsherbert/folium-jsbutton.
#     """
#     _template = Template("""
#         {% macro script(this, kwargs) %}
#         L.easyButton(
#             '<span>{{ this.title }}</span>',
#             {{ this.function }}
#         ).addTo({{ this.map_name }});
#         {% endmacro %}
#         """)
#
#     def __init__(
#             self,
#             title='',
#             function="""
#                 function(btn, map){
#                     alert('no function defined yet.');
#                 }
#             """
#     ):
#         super(JsButton, self).__init__()
#         self.title = title
#         self.function = function
#
#     def add_to(self, m):
#         self.map_name = m.get_name()
#         super(JsButton, self).add_to(m)
#
#     def render(self, **kwargs):
#         super(JsButton, self).render()
#
#         figure = self.get_root()
#         assert isinstance(figure, Figure), (
#             'You cannot render this Element if it is not in a Figure.')
#
#         figure.header.add_child(
#             JavascriptLink('https://cdn.jsdelivr.net/npm/leaflet-easybutton@2/src/easy-button.js'),  # noqa
#             name='Control.EasyButton.js'
#         )
#
#         figure.header.add_child(
#             CssLink('https://cdn.jsdelivr.net/npm/leaflet-easybutton@2/src/easy-button.css'),  # noqa
#             name='Control.EasyButton.css'
#         )
#
#         figure.header.add_child(
#             CssLink('https://use.fontawesome.com/releases/v5.3.1/css/all.css'),  # noqa
#             name='Control.FontAwesome.css'
#         )


class leafletJsButton(MacroElement):
    """
    Button that executes a javascript function.
    Parameters
    ----------
    object : str
         function to execute, should have format
         `{
            states:[
                {
                    icon: '<span class="star">&starf;</span>',
                    onClick: function(){ alert('you just clicked the html entity \&starf;'); }
                }
            ]
        }`

    See http://danielmontague.com/projects/easyButton.js/v1/examples/
    """
    _template = jinja2.Template("""
        {% macro script(this, kwargs) %}
        L.easyButton(
            {{ this.object }}
        ).addTo({{ this.map_name }});
        {% endmacro %}
        """)

    def __init__(
            self,
            object="""
                {
                  id: 'any-id-for-your-control',
                  states:[
                    {
                      icon: '<span class="star">&starf;</span>',
                      onClick: function(){ alert('you just clicked the html entity \&starf;'); }
                    }, {
                      ...
                    }
                  ]
                }
            """
    ):
        super(leafletJsButton, self).__init__()
        self.object = object

    def add_to(self, m):
        self.map_name = m.get_name()
        super(leafletJsButton, self).add_to(m)

    def render(self, **kwargs):
        super(leafletJsButton, self).render()

        figure = self.get_root()
        assert isinstance(figure, Figure), (
            'You cannot render this Element if it is not in a Figure.')

        figure.header.add_child(
            JavascriptLink('https://cdn.jsdelivr.net/npm/leaflet-easybutton@2/src/easy-button.js'),  # noqa
            name='Control.EasyButton.js'
        )

        figure.header.add_child(
            CssLink('https://cdn.jsdelivr.net/npm/leaflet-easybutton@2/src/easy-button.css'),  # noqa
            name='Control.EasyButton.css'
        )

        figure.header.add_child(
            CssLink('https://use.fontawesome.com/releases/v5.3.1/css/all.css'),  # noqa
            name='Control.FontAwesome.css'
        )

# objektide markeril hiirega peatudes infoakna kuvamiseks
def get_object_data4tooltip(objekt):
    heading = f'{objekt}'
    if objekt.gone:
        heading += '<br /><span style="color: red;">hävinud</span>'
    if objekt.profiilipildid.exists():
        profiilipilt = objekt.profiilipildid.first()
        img = settings.MEDIA_URL + profiilipilt.pilt_thumbnail.name
        img = f'<br /><img class="tooltip-content-img" src="{img}" alt="{profiilipilt}">'
    else:
        img = ''
    content = f'<div class="kaardiobjekt-tooltip">{heading}{img}</div>'
    return content

# objektide markeril hiirega klikkides infoakna kuvamiseks
def get_object_data4popup(kaardiobjekt):
    # kaardiobjekt_href = kaardiobjekt.get_absolute_url()
    # kaardiobjekt_link = f"""
    # <br />
    # <small><a href="{kaardiobjekt_href}" target="_blank">{kaardiobjekt}</a></small>
    # """
    kaardiobjekt_link = ''
    objekt = kaardiobjekt.objekt
    if objekt:
        objekt_href = objekt.get_absolute_url()
        objekt_link = f"""
        <br />
        <a href="{objekt_href}" target="_blank">{objekt}</a>
        """
    else:
        objekt_link = ''
    content = f"""
    <div class="kaardiobjekt-tooltip">Loe rohkem: 
      {objekt_link}{kaardiobjekt_link}
    </div>
    """
    return content

# kaardiobjektide markeril hiirega peatudes infoakna kuvamiseks
def get_kaardiobjekt_data4tooltip(kaardiobjekt):
    heading = f'{kaardiobjekt.kaart}'
    parts = []
    aadressiobjekt = ' '.join([kaardiobjekt.tn, kaardiobjekt.nr]).strip()
    if aadressiobjekt:
        parts.append(f'{kaardiobjekt.get_tyyp_display()}: {aadressiobjekt}')
    if kaardiobjekt.lisainfo:
        parts.append(kaardiobjekt.lisainfo)
    body = '<br />'.join(parts)
    content = f"""
    <div class='kaardiobjekt-tooltip'>
      {heading}<br /><a href='{kaardiobjekt.get_absolute_url()}' target='_blank'>{body}</a>
    </div>
    """
    return content

# Lisab tuvastatud kaardiobjektid kaartidele aastate kaupa
def add_kaardiobjektid2map(map, kaardid):
    for kaart in kaardid:
        kaart_aasta = kaart.aasta
        path = UTIL_DIR / 'geojson' / f"kaardiobjektid_{kaart_aasta}.geojson"
        if path.is_file():
            # NB! popup ja tooltip on vaja iga geojson kihi jaoks eraldi luua
            popup = GeoJsonPopup(
                fields=["popup"],
                labels=False,
                # style="background-color: yellow;",
                max_width=300,
            )
            tooltip = GeoJsonTooltip(
                fields=["tooltip"],
                labels=False,
                style="""
                    border: none;
                    border-radius: 3px;
                    box-shadow: 3px;
                """,
                max_width=300,
            )
            with open(path) as gf:
                src = json.load(gf)
                name = src['name']
                geojson = folium.GeoJson(
                    src,
                    name=f'<span class="kaart-control-layers">{name}</span>',
                    show=False,
                    tooltip=tooltip,
                    popup=popup,
                    style_function=lambda x: GEOJSON_STYLE[x['properties']['tyyp']],
                )
                geojson.add_to(map)
    return map

def add_objekt2map(feature_groups_kaardid, obj):
    if obj:
        queryset = Kaardiobjekt.objects.filter(objekt=obj)
        objektiga_kaardid_aastad = [kaardiobjekt.kaart.aasta for kaardiobjekt in queryset]
        if objektiga_kaardid_aastad:
            objektiga_kaart_aasta_max = max(objektiga_kaardid_aastad)
            maatriks = {}
            maatriks[objektiga_kaart_aasta_max] = {
                'qs': queryset.filter(kaart__aasta__exact=objektiga_kaart_aasta_max),
                'status': 'E'
            }
            for kaart_aasta in [aasta for aasta in sorted(feature_groups_kaardid.keys()) if aasta != objektiga_kaart_aasta_max]:
                qs = queryset.filter(kaart__aasta__exact=kaart_aasta)
                if qs:
                    maatriks[kaart_aasta] = {
                        'qs': qs,
                        'status': 'E'
                    }
                else:
                    status = 'V'
                    if kaart_aasta > objektiga_kaart_aasta_max and obj.gone:
                        status = 'H'
                    maatriks[kaart_aasta] = {
                        'qs': maatriks[objektiga_kaart_aasta_max]['qs'],
                        'status': status,
                    }

            for kaart_aasta in maatriks.keys():
                fg = feature_groups_kaardid[kaart_aasta]
                status = maatriks[kaart_aasta]['status']
                color = GEOJSON_STYLE[f'H{status}']['color']
                if kaart_aasta == DEFAULT_MAP.aasta and obj.gone:
                    # color = GEOJSON_STYLE['HH']['color']
                    tilelayers = [key for key in fg._children.keys() if key.find('tile_layer_') == 0]
                    if tilelayers:
                        for tilelayer in tilelayers:
                            # fg._children[tilelayer].tiles = folium.TileLayer('Stamen Toner').tiles
                            # fg._children[tilelayer].tiles = folium.TileLayer(
                            #     tiles=STAMEN_TONER_NEW['tiles'],
                            #     attr=STAMEN_TONER_NEW['attr'],
                            # ).tiles
                            fg._children[tilelayer].tiles = STAMEN_TONER_NEW['tiles']
                            fg._children[tilelayer].attr = STAMEN_TONER_NEW['attr']
                name = f'<span class="kaart-control-layers" style="color: {color};">{kaart_aasta}</span>'
                fg.layer_name = name
                kaardiobjektid = maatriks[kaart_aasta]['qs']

                for kaardiobjekt in kaardiobjektid:
                    tyyp = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
                    tooltip = get_kaardiobjekt_data4tooltip(kaardiobjekt)
                    popup = None
                    style = GEOJSON_STYLE[f'{tyyp}{status}']
                    if kaardiobjekt.objekt:  # kui seotud objektiga
                        tooltip = get_object_data4tooltip(kaardiobjekt.objekt)
                        popup = folium.Popup(
                            get_object_data4popup(kaardiobjekt),
                            max_width="100%"
                        )
                    geometry = kaardiobjekt.geometry
                    name = f'{kaardiobjekt.__str__()} ({dict(Kaardiobjekt.TYYP)[tyyp].lower()})'
                    feature_collection = {
                        "type": "FeatureCollection",
                        "name": name,
                        "features": [geometry]
                    }
                    f = json.dumps(feature_collection)
                    geojson = folium.GeoJson(
                        f,
                        name=name,
                        style_function=lambda x, style=style: style,
                        tooltip=tooltip,
                        popup=popup,
                        highlight_function=lambda x: {"fillOpacity": 0.5},
                    )
                    geojson.add_to(feature_groups_kaardid[kaart_aasta])
                # end for kaardiobjekt in kaardiobjektid:
            # end for kaart_aasta in maatriks.keys():
        # end if objektiga_kaardid_aastad:
    # end if obj
    return feature_groups_kaardid

def get_objekt_centroid_location(obj, aasta):
    objekt_centroid_location = None
    try:
        objekt_centroid_location = Kaardiobjekt.objects.filter(kaart__aasta=aasta, objekt=obj).first().centroid
    except:
        kaardiobjektid = Kaardiobjekt.objects.filter(objekt=obj)
        if kaardiobjektid:
            objekt_centroid_location = kaardiobjektid.first().centroid
    return objekt_centroid_location

def get_vectorlayer_borders():
    # Piirid tänapäeval
    style = {'fill': None, 'color': '#00FFFF', 'weight': 5}
    with open(UTIL_DIR / 'geojson' / "piirid.geojson") as gf:
        src = json.load(gf)
    return folium.GeoJson(
        src,
        name=f'<span class="kaart-control-layers">linnapiirid (2021)</span>',
        style_function=lambda x: style
    )

def get_vectorlayer_streets():
    # Tänavatevõrk tänapäeval
    style = {'fill': None, 'color': 'orange', 'weight': 2}
    with open(UTIL_DIR / 'geojson' / "teedev6rk_2021.geojson") as gf:
        src = json.load(gf)
    return folium.GeoJson(
        src,
        name=f'<span class="kaart-control-layers">tänavad (2021)</span>',
        style_function=lambda x: style
    )


def get_big_maps_default(kaardid, obj, aasta):
    aasta = aasta or settings.DEFAULT_BIGMAP_AASTA # kui aastat pole valitud, siis n2itame vaikimisi kaarti
    feature_groups_kaardid = {} # erinevate aastate kaardid

    for kaart in kaardid:
        # loome kaardikihi
        # name = f'<span class="kaart-control-layers" style="color: #A9A9A9;">{kaart.aasta}</span>' # darkgrey
        name = f'<span class="kaart-control-layers">{kaart.aasta}</span>'
        feature_group = folium.FeatureGroup(
            name=name,
            overlay=False,
            kaartAasta=kaart.aasta,
            id=f'fg{kaart.aasta}',
            show=kaart.aasta == aasta
        )
        # lisame kaardikihile rasterkihi
        tilelayer = folium.TileLayer(
            location=DEFAULT_CENTER,
            name=kaart.aasta,
            tiles=kaart.tiles,
            zoom_start=DEFAULT_MAP_ZOOM_START,
            min_zoom=DEFAULT_MIN_ZOOM,
            attr=f'{kaart.__str__()}<br>{kaart.viited.first()}',
            id=f'tl{kaart.aasta}',
        )

        # Lisame kaardile kirjelduse tootipi
        kwargs = {
            'direction': 'center',
            'permanent': False,
            'interactive': True,
            'opacity': 0.9,
        }
        tooltip = folium.Tooltip(
            kaart.kirjeldus_html,
            **kwargs
        )
        tooltip.add_to(tilelayer)
        tilelayer.add_to(feature_group)
        feature_groups_kaardid[kaart.aasta] = feature_group

    # Loome aluskaardi
    map = folium.Map(
        location=DEFAULT_CENTER,  # NB! tagurpidi: [lat, lon],
        zoom_start=DEFAULT_MAP_ZOOM_START,
        min_zoom=DEFAULT_MIN_ZOOM,
        zoom_control=True,
        control_scale=True,
        tiles=None,
    )

    # Teegid mida kasutatakse folium leaflet moodulis
    map.default_css = LEAFLET_DEFAULT_CSS
    map.default_js = LEAFLET_DEFAULT_JS
    LEAFLET_DEFAULT_HEADER.add_to(map.get_root().header)

    if obj:
        feature_groups_kaardid = add_objekt2map(feature_groups_kaardid, obj)
        objekt_centroid_location = get_objekt_centroid_location(obj, aasta)
        if objekt_centroid_location:
            map.location = objekt_centroid_location

    for fg in feature_groups_kaardid.values():
        fg.add_to(map)

    # Lisame tuvastatud kaardiobjektid kaartidele
    map = add_kaardiobjektid2map(map, kaardid)

    # Piirid tänapäeval
    vectorlayer_borders = get_vectorlayer_borders()
    vectorlayer_borders.add_to(map)
    # Tänavatevõrk tänapäeval
    vectorlayer_streets = get_vectorlayer_streets()
    vectorlayer_streets.add_to(map)

    # Lisame infonupu
    leafletJsButton(
        object="""
        {
            states:[
                {
                    stateName: 'show-info',
                    icon: 'fa-info',
                    title: 'Info kaardi kohta',
                    onClick: function(btn, map) {
                        map.eachLayer(function(layer) {
                            layerId = layer.options.id;
                            if (layerId) {
                                layer.openTooltip(map.getCenter());
                                map.once('tooltipclose', function(ev){
                                    btn.state('show-info');
                                });
                            }
                        });
                        btn.state('hide-info');
                    }
                }, {
                    icon: 'fa-close',
                    stateName: 'hide-info',
                    onClick: function(btn, map) {
                        map.eachLayer(function(layer) {
                            layerId = layer.options.id;
                            if (layerId) {
                                layer.closeTooltip();
                            }
                        });
                        btn.state('show-info');
                    },
                    title: 'Sulge infoaken'
                }
            ]
        }
    """
    ).add_to(map)

    # Lisame kihtide kontrolli kaartide jaoks
    layer_control = folium.LayerControl()
    layer_control.add_to(map)

    # Lisame täiendavat javascripti
    el = folium.MacroElement().add_to(map)
    map_name = map.get_name()
    # basemaps = [f'{key}: {item.get_name()}' for key, item in feature_groups_kaardid.items()]

    # Lisame javascripti <script> tagi lõppu selleks, et layer controli kohendada
    js = f'const map = {map_name};\n'
    # js += 'const basemaps = {' + ', '.join(basemaps) + '};\n'
    # js += f'const defaultMap = "{settings.DEFAULT_BIGMAP_AASTA}";\n'
    with open(UTIL_DIR / 'wiki_kaart.js') as jsf:
        js += jsf.read()
    el._template = jinja2.Template('''
        {{% macro script(this, kwargs) %}}
            {0}
        {{% endmacro %}}'''.format(js))

    return map

def make_big_maps_leaflet(aasta=None, objekt=None):
    # print(aasta)
    kaardid = Kaart.objects.exclude(tiles__exact='').order_by('aasta')
    if aasta and Kaart.objects.filter(aasta=aasta).count()==0:
        tekst = f'<h4>{aasta}. aasta kaarti ei ole. Vali järgmistest:</h4>'
        for kaart in kaardid:
            href = reverse('kaart')
            tekst += f'<p class="hover-objekt"><a href="{href}{kaart.aasta}">{kaart}</a><p>'
        return tekst
    else:
        obj = Objekt.objects.none()
        if objekt:
            try:
                obj = Objekt.objects.get(id=objekt)
            except ObjectDoesNotExist:
                pass
        # Loome map objecti
        map = get_big_maps_default(kaardid, obj, aasta)
        map_html = map._repr_html_()
        # v2ike h2kk, mis muudab vertikaalset suuruse sõltuvaks css-ist
        map_html = map_html.replace(
            'style="position:relative;width:100%;height:0;padding-bottom:60%;"',
            'id = "folium-map-big" class="folium-map-big"',
            1
        )
        # v2ike h2kk, mis muudab vaikimis veateksti
        map_html = map_html.replace(
            '<span style="color:#565656">Make this Notebook Trusted to load map: File -> Trust Notebook</span>',
            # '<span style="color:#565656">Kaarti laetakse. Kui see kiri jääb nähtavaks, tekkis laadimisel viga</span>',
            '',
            1
        )
    return map_html

def make_objekt_leaflet_combo_add_tilelayer(kaart, is_objekt_missing_on_defaultmap, tile_kwargs):
    # lisame kaardipildi
    tiles = kaart.tiles
    attr = f'{kaart.__str__()}<br>{kaart.viited.first()}'
    tile_kwargs['aasta'] = kaart.aasta
    # kui objekti kaasajal ei ole
    if kaart == DEFAULT_MAP and is_objekt_missing_on_defaultmap:
        tiles = STAMEN_TONER_NEW['tiles']
        attr = STAMEN_TONER_NEW['attr']

    return folium.TileLayer(
        # location=location,
        name=kaart.aasta,
        tiles=tiles,
        attr=attr,
        min_zoom=DEFAULT_MIN_ZOOM,
        **tile_kwargs
    )

def make_objekt_leaflet_combo_add_vectorlayer(obj, kaardiobjekt, status):
    geometry = kaardiobjekt.geometry
    tyyp = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
    name = f'{kaardiobjekt.__str__()} ({dict(Kaardiobjekt.TYYP)[tyyp].lower()})'
    feature_collection = {
        "type": "FeatureCollection",
        "name": name,
        "features": [geometry]
    }
    # if obj.gone:  # objekti kaasajal pole
    #     tyyp_style = f'{kaardiobjekt.tyyp}H'  # 'HH'-hoonestus, 'AH'-ala, 'MH'-muu
    # else:  # objekt kaasajal olemas
    #     tyyp_style = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
    tyyp_style = f'{kaardiobjekt.tyyp}{status}'
    style = GEOJSON_STYLE[tyyp_style]
    return folium.GeoJson(
        json.dumps(feature_collection),
        name=name,
        style_function=lambda x: style
    )

# Konkreetse objekti erinevate aastate kaardid koos
def make_objekt_leaflet_combo(objekt=1):
    obj = Objekt.objects.get(id=objekt)
    kaardiobjektid_objektiga = obj.kaardiobjekt_set.all()
    kaardid_objektiga_aastad = kaardiobjektid_objektiga.values_list('kaart__aasta', flat=True)

    if kaardid_objektiga_aastad: # kui v2hemalt yhel kaardil objekt m2rgitud

        # Loome aluskaardi
        # zoom_start = DEFAULT_MAP_ZOOM_START
        kaardiobjektide_zoomid = [kaardiobjekt.zoom for kaardiobjekt in kaardiobjektid_objektiga if kaardiobjekt.zoom]
        zoom_start = min(kaardiobjektide_zoomid) if kaardiobjektide_zoomid else DEFAULT_MAP_ZOOM_START
        location = DEFAULT_CENTER
        kwargs = {  # vajalikud mobiilis kerimise h6lbustamiseks
            'dragging': '!L.Browser.mobile',
            'tap': '!L.Browser.mobile'
        }
        map = folium.Map(
            location=location,  # NB! tagurpidi: [lat, lon],
            zoom_start=zoom_start,
            min_zoom=DEFAULT_MIN_ZOOM,
            zoom_control=True,
            tiles=None,
            **kwargs
        )

        map.default_css = LEAFLET_DEFAULT_CSS
        map.default_js = LEAFLET_DEFAULT_JS
        LEAFLET_DEFAULT_HEADER.add_to(map.get_root().header)

        # Piirid tänapäeval
        vectorlayer_borders = get_vectorlayer_borders()
        vectorlayer_borders.add_to(map)
        # Tänavatevõrk tänapäeval
        vectorlayer_streets = get_vectorlayer_streets()
        vectorlayer_streets.add_to(map)

        is_objekt_missing_on_defaultmap = DEFAULT_MAP.aasta not in kaardid_objektiga_aastad  # Objekti kaasajal pole?
        objekt_last_seen_on_map = max([aasta for aasta in kaardid_objektiga_aastad])
        kaardid_objektiga = \
            Kaart.objects.filter(aasta__in=kaardid_objektiga_aastad) | \
            Kaart.objects.filter(id=DEFAULT_MAP.id) # lisame kaasajakaardi

        feature_groups = {} # kaardikihid
        big_map_url = reverse('kaart')
        tile_kwargs = {
            'url': big_map_url,
            'objektId': objekt
        }

        for kaart in kaardid_objektiga:
            # loome kaardikihi
            feature_groups[kaart.aasta] = folium.FeatureGroup(
                name=f'<span class="kaart-control-layers">{kaart.aasta}</span>',
                overlay=False,
                show=kaart==DEFAULT_MAP
            )

            # Lisame kaardipildi
            tilelayer = make_objekt_leaflet_combo_add_tilelayer(kaart, is_objekt_missing_on_defaultmap, tile_kwargs)
            tilelayer.add_to(feature_groups[kaart.aasta])

            # lisame vektorkihid
            if kaart == DEFAULT_MAP and DEFAULT_MAP.aasta != objekt_last_seen_on_map:
                kaardiobjektid = obj.kaardiobjekt_set.filter(kaart__aasta=objekt_last_seen_on_map)
                status = 'H' # pole m2rgitud
            else:
                kaardiobjektid = obj.kaardiobjekt_set.filter(kaart=kaart)
                status = 'E' # sellel kaardil m2rgitud

            for kaardiobjekt in kaardiobjektid:
                vectorlayer = make_objekt_leaflet_combo_add_vectorlayer(obj, kaardiobjekt, status)
                vectorlayer.add_to(feature_groups[kaart.aasta])

            # Parandame kaardi keskpunkti
            if kaart == DEFAULT_MAP and kaardiobjektid and kaardiobjektid[0].geometry:
                map.location = kaardiobjektid[0].centroid

            # Lisame kaardi leaflet combosse
            feature_groups[kaart.aasta].add_to(map)

        # Lisame nupu kaardivaate avamiseks
        leafletJsButton(
            object="""
                    {
                        states:[
                            {
                                stateName: 'show-fullmap',
                                icon: 'glyphicon glyphicon-fullscreen',
                                title: 'Näita suurel kaardil',
                                onClick: function(btn, map) {
                                    map.eachLayer(function(layer) {
                                        if ( layer instanceof L.TileLayer ) {
                                            window.open(
                                              layer.options.url + layer.options.aasta + '?objekt=' + layer.options.objektId,
                                              '_blank' // <- This is what makes it open in a new window.
                                            );
                                        }
                                    });
                                }
                            }
                        ]
                    }
                """
        ).add_to(map)

        # Lisame kihtide kontrolli
        folium.LayerControl().add_to(map)

        map_html = map._repr_html_()
        # v2ike h2kk, mis muudab vertikaalset suurust
        map_html = map_html.replace(';padding-bottom:60%;', ';padding-bottom:100%;', 1)
        # v2ike h2kk, mis muudab vaikimis veateksti
        map_html = map_html.replace(
            '<span style="color:#565656">Make this Notebook Trusted to load map: File -> Trust Notebook</span>',
            '',
            1
        )
        return map_html


# Konkreetse objekti erinevate aastate kaardid koos
# def make_objekt_leaflet_combo_vana(objekt=1):
#     obj = Objekt.objects.get(id=objekt)
#     # Kõigi kaartide ids, kus objekt märgitud: tulemus: <QuerySet ['1', '2', '3']>
#     kaardid_objektiga_ids = obj.kaardiobjekt_set.values_list('kaart__id', flat=True)
#
#     if kaardid_objektiga_ids:
#         kaardid_objektiga = Kaart.objects.filter(id__in=kaardid_objektiga_ids)
#         objekt_missing_on_defaultmap = DEFAULT_MAP not in kaardid_objektiga  # Objekti kaasajal pole?
#         objekt_last_seen_on_map = max([kaart.aasta for kaart in kaardid_objektiga])
#
#         if objekt_missing_on_defaultmap:
#             # Lisame vaate, millel näitame virtuaalset asukohta tänapäeval
#             kaardid_objektiga = kaardid_objektiga | Kaart.objects.filter(id=DEFAULT_MAP.id)
#
#         feature_groups = {}
#         zoom_start = DEFAULT_MAP_ZOOM_START
#         location = DEFAULT_CENTER
#
#         for kaart in kaardid_objektiga:
#             # aasta = kaart.aasta
#             url = reverse('kaart')
#
#             feature_groups[kaart.aasta] = folium.FeatureGroup(
#                 name=f'<span class="kaart-control-layers">{kaart.aasta}</span>',
#                 overlay=False,
#                 show=False
#             )
#
#             tile_kwargs = {
#                 'url': url,
#                 'aasta': kaart.aasta,
#                 'objektId': objekt
#             }
#             if kaart == DEFAULT_MAP and objekt_missing_on_defaultmap:
#                 folium.TileLayer(
#                     location=location,
#                     name=kaart.aasta,
#                     tiles=STAMEN_TONER_NEW['tiles'],
#                     attr=STAMEN_TONER_NEW['attr'],
#                     min_zoom=DEFAULT_MIN_ZOOM,
#                     **tile_kwargs
#                 ).add_to(feature_groups[kaart.aasta])
#                 feature_groups[kaart.aasta].show=True
#             else:
#                 kaardiobjektid = obj.kaardiobjekt_set.filter(kaart=kaart)
#                 if kaardiobjektid[0].geometry:
#                     location = kaardiobjektid[0].centroid
#                 folium.TileLayer(
#                     location=location,
#                     name=kaart.aasta,
#                     tiles=kaart.tiles,
#                     min_zoom=DEFAULT_MIN_ZOOM,
#                     attr=f'{kaart.__str__()}<br>{kaart.viited.first()}',
#                     **tile_kwargs
#                 ).add_to(feature_groups[kaart.aasta])
#
#                 # lisame vektorkihid
#                 for kaardiobjekt in kaardiobjektid:
#                     geometry = kaardiobjekt.geometry
#                     tyyp = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
#                     name = f'{kaardiobjekt.__str__()} ({dict(Kaardiobjekt.TYYP)[tyyp].lower()})'
#                     feature_collection = {
#                         "type": "FeatureCollection",
#                         "name": name,
#                         "features": [geometry]
#                     }
#                     if obj.gone:  # objekti kaasajal pole
#                         tyyp_style = f'{kaardiobjekt.tyyp}H'  # 'HH'-hoonestus, 'AH'-ala, 'MH'-muu
#                     else:  # objekt kaasajal olemas
#                         tyyp_style = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
#                     style = GEOJSON_STYLE[tyyp_style]
#                     f = json.dumps(feature_collection)
#                     folium.GeoJson(
#                         f,
#                         name=name,
#                         style_function=lambda x: style
#                     ).add_to(feature_groups[kaart.aasta])
#                     if kaart.aasta == objekt_last_seen_on_map and objekt_missing_on_defaultmap:
#                         folium.GeoJson(
#                             f,
#                             name=name,
#                             style_function=lambda x: style
#                         ).add_to(feature_groups[DEFAULT_MAP.aasta])
#                     # Kui on antud zoomimise tase, siis kasutame seda
#                     if kaardiobjekt.zoom and (zoom_start != kaardiobjekt.zoom):
#                         zoom_start = kaardiobjekt.zoom
#
#         feature_groups[DEFAULT_MAP.aasta].show = True
#
#         # Loome aluskaardi
#         kwargs = {  # vajalikud mobiilis kerimise h6lbustamiseks
#             'dragging': '!L.Browser.mobile',
#             'tap': '!L.Browser.mobile'
#         }
#         map = folium.Map(
#             location=location,  # NB! tagurpidi: [lat, lon],
#             zoom_start=zoom_start,
#             min_zoom=DEFAULT_MIN_ZOOM,
#             zoom_control=True,
#             tiles=None,
#             **kwargs
#         )
#
#         map.default_css = LEAFLET_DEFAULT_CSS
#         map.default_js = LEAFLET_DEFAULT_JS
#         LEAFLET_DEFAULT_HEADER.add_to(map.get_root().header)
#
#         for aasta in feature_groups.keys():
#             # Lisame kaardi leaflet combosse
#             feature_groups[aasta].add_to(map)
#
#         # Piirid tänapäeval
#         style1 = {'fill': None, 'color': '#00FFFF', 'weight': 5}
#         with open(UTIL_DIR / 'geojson' / "piirid.geojson") as gf:
#             src = json.load(gf)
#             folium.GeoJson(
#                 src,
#                 name=f'<span class="kaart-control-layers">linnapiirid (2021)</span>',
#                 style_function=lambda x: style1
#             ).add_to(map)
#
#         # Tänavatevõrk tänapäeval
#         style2 = {'fill': None, 'color': 'orange', 'weight': 2}
#         with open(UTIL_DIR / 'geojson' / "teedev6rk_2021.geojson") as gf:
#             src = json.load(gf)
#             folium.GeoJson(
#                 src,
#                 name=f'<span class="kaart-control-layers">tänavad (2021)</span>',
#                 style_function=lambda x: style2
#             ).add_to(map)
#
#         # Lisame nupu kaardivaate avamiseks
#         leafletJsButton(
#             object="""
#                 {
#                     states:[
#                         {
#                             stateName: 'show-fullmap',
#                             icon: 'glyphicon glyphicon-fullscreen',
#                             title: 'Näita suurel kaardil',
#                             onClick: function(btn, map) {
#                                 map.eachLayer(function(layer) {
#                                     if ( layer instanceof L.TileLayer ) {
#                                         window.open(
#                                           layer.options.url + layer.options.aasta + '?objekt=' + layer.options.objektId,
#                                           '_blank' // <- This is what makes it open in a new window.
#                                         );
#                                     }
#                                 });
#                             }
#                         }
#                     ]
#                 }
#             """
#         ).add_to(map)
#
#         # Lisame kihtide kontrolli
#         folium.LayerControl().add_to(map)
#
#         map_html = map._repr_html_()
#         # v2ike h2kk, mis muudab vertikaalset suurust
#         map_html = map_html.replace(';padding-bottom:60%;', ';padding-bottom:100%;', 1)
#         # v2ike h2kk, mis muudab vaikimis veateksti
#         map_html = map_html.replace(
#             '<span style="color:#565656">Make this Notebook Trusted to load map: File -> Trust Notebook</span>',
#             '',
#             1
#         )
#         return map_html

# Konkreetse kaardiobjekti kaart
def make_kaardiobjekt_leaflet(kaardiobjekt_id):
    try:
        kaardiobjekt = Kaardiobjekt.objects.get(id=kaardiobjekt_id)
    except:
        return
    if kaardiobjekt:
        map_html = kaardiobjekt.get_leaflet()
        return map_html


if __name__ == "__main__":
    # make_big_maps_leaflet(aasta=1824, objekt=970)
    # kaardiobjektid2geojson()
    # read_kaardiobjekt_csv_to_db('2021')
    # geometry = get_osm_data(street='Rigas', housenumber='9', admin_level='7', country='Latvija', city='Valka')
    # geometry = get_osm_data(street='Kesk', housenumber='12')
    geometry = get_shp_data(kataster='79517:019:0003')
    # geometry = get_osm_data(street='Kraavikalda', housenumber='19', admin_level='9', country='Eesti', city='Tartu linn')
    print(geometry)
    # kaardiobjekt_match_db(20938)
    # read_shp_to_db(aasta='1912') # Loeb kaardikihi shp failist andmebaasi
    # write_db_to_shp(aasta='1800') # Kirjutab andmebaasist kaardikihi shp faili
    # save_current_data() # Salvestame andmebaasi värsked andmed OpenStreetMapist ja Maa-ameti andmefailist
    # find_intersections()
    # update_objekt_from_csv()
    # shp_match_db()
    pass


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

# Lisab javascripti <script> tagi algusesse
# my_js = '''
# let height;
#
# const sendPostMessage = () => {
#     if (height !== document.getElementById('mapcontainer').offsetHeight) {
#         height = document.getElementById('mapcontainer').offsetHeight;
#         window.parent.postMessage({
#             frameHeight: height
#         }, '*');
#         console.log(height);
#     }
# }
#
# window.onload = () => sendPostMessage();
# window.onresize = () => sendPostMessage();
# '''
# from branca.element import Element
# map.get_root().script.add_child(Element(my_js))
#
# Kui on vaja lisada lisa html-i <div class="folium-map" id="map_795eaceab1bb4d5d8a0d91d1a99d36a4" ></div> järele
# map.get_root().html.add_child(Element("<h1>Hello world</h1>"))
