from pathlib import Path

if __name__ == "__main__":
    import os
    import django
    from django.test.utils import setup_test_environment

    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    setup_test_environment()
    from django.conf import settings
    UTIL_DIR = Path(__file__).resolve().parent
    print('Töökataloog:', UTIL_DIR)
    # Build paths inside the project like this: UTIL_DIR / 'subdir'.
else:
    from django.conf import settings
    UTIL_DIR = settings.BASE_DIR / 'wiki' / 'utils'

import csv
import json
import re
import time

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

from branca.element import CssLink, Element, Figure, JavascriptLink, MacroElement

import folium

import jinja2
import pyproj
import requests
import shapefile
from shapely.geometry.polygon import Polygon

from wiki.models import Kaart, Kaardiobjekt, Objekt

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
DEFAULT_CENTER = (57.7769268, 26.0308911) # {'lon': 26.0308911, 'lat': 57.7769268} # Jaani kiriku koordinaadid
DEFAULT_MAP = Kaart.objects.filter(aasta='2021').first() # Vaikimisi Stamen Toner internetikaart
DEFAULT_MAP_ZOOM_START = 16
DEFAULT_MIN_ZOOM = 13

# BLUEVIOLET = '#8A2BE2'
FUCHSIA = '#FF00FF'
OBJEKT_COLOR = '#2b5797'

GEOJSON_STYLE = {
    'H': {'fill': None, 'color': FUCHSIA, 'weight': 3}, # hoonestus (default)
    'A': {'fill': None, 'color': FUCHSIA, 'weight': 3}, # ala (default)
    'M': {'fill': None, 'color': FUCHSIA, 'weight': 3}, # muu (default)
    'HH': {'fill': 'red', 'color': 'red', 'weight': 3}, # hoonestus (puudub kaasajal)
    'AH': {'fill': None, 'color': 'red', 'weight': 3}, # ala (puudub kaasajal)
    'MH': {'fill': None, 'color': 'red', 'weight': 3}, # muu (puudub kaasajal)
    'HE': {'fill': OBJEKT_COLOR, 'color': OBJEKT_COLOR, 'weight': 3}, # hoonestus (olemas kaasajal)
    'AE': {'fill': None, 'color': OBJEKT_COLOR, 'weight': 3}, # ala (olemas kaasajal)
    'ME': {'fill': None, 'color': OBJEKT_COLOR, 'weight': 3}, # muu (olemas kaasajal)
}

# https://python-visualization.github.io/folium/modules.html#module-folium.map
LEAFLET_DEFAULT_CSS = [
    ('leaflet_css', 'https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/leaflet.css'),
    ('bootstrap_css', 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css'),
    ('bootstrap_theme_css', 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css'),
    ('awesome_markers_font_css', 'https://maxcdn.bootstrapcdn.com/font-awesome/4.6.3/css/font-awesome.min.css'),
    ('awesome_markers_css', 'https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css'),
    ('awesome_rotate_css', 'https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css')
]
LEAFLET_DEFAULT_JS = [
    ('leaflet', 'https://unpkg.com/leaflet@1.8.0/dist/leaflet.js'),
    ('jquery', 'https://code.jquery.com/jquery-1.12.4.min.js'),
    ('bootstrap', 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js'),
    ('awesome_markers', 'https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js')
]

# Kroonika default font kasutamiseks + custom elementide css
LEAFLET_DEFAULT_HEADER = Element(
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

# LEAFLET_DEFAULT_CSS_ver_1_93 = [
#     ("leaflet", "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"),
#     ("jquery", "https://code.jquery.com/jquery-1.12.4.min.js"),
#     ("bootstrap","https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.bundle.min.js",),
#     ("awesome_markers", "https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js",),
# ]
#
# LEAFLET_DEFAULT_JS_ver_1_93 = [
#     ("leaflet_css", "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"),
#     ("bootstrap_css", "https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css",),
#     # glyphicons came from Bootstrap 3 and are used for Awesome Markers
#     ("glyphicons_css", "https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap.min.css",),
#     ("awesome_markers_font_css", "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css",),
#     ("awesome_markers_css", "https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css",),
#     ("awesome_rotate_css", "https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css",),
# ]


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
        lisatud = 0
        olemas = 0
        with open(UTIL_DIR / f'{aasta}.shp', 'rb') as shp_file:
            with open(UTIL_DIR / f'{aasta}.dbf', 'rb') as dbf_file:
                with shapefile.Reader(shp=shp_file, dbf=dbf_file) as sf:
                    # existing Shape objects
                    for shaperec in sf.iterShapeRecords():
                        rec = shaperec.record.as_dict()
                        geometry = shaperec.shape.__geo_interface__
                        # kontrollitakse, kas selliste piiridega kaardiobjekt on juba andmebaasis
                        kontroll = Kaardiobjekt.objects.filter(kaart=kaart, geometry=geometry)
                        print(rec, end=' ')
                        if kontroll:
                            print('olemas')
                            olemas += 1
                        else:
                            print('lisame:')
                            lisatud += 1
                            o = Kaardiobjekt.objects.create(kaart=kaart, geometry=geometry, **rec)
                            print(o)
        print(f'Olemas {olemas}, lisatud {lisatud}')
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
def get_osm_data(street=None, housenumber=None, country='Eesti', admin_level='9', city='Valga linn'):
    if street and housenumber:
        # print(asukoht, end=' ')
        # street, housenumber = split_address(aadress)

        query = """
                (
          way(id: 214327417, 228359022, 228899964);
        );
        """ # Kesk 12 hooned

        query = f"""
        area['admin_level'='2']['name'='{country}']->.searchArea;
        area['admin_level'='{admin_level}']['name'='{city}'](area.searchArea)->.searchArea;
        (
            nwr["building"]["addr:street"~"{street}"]["addr:housenumber"="{housenumber}"](area.searchArea);
        );
        """

        # Pärime andmed operpass APIst
        overpass_query = f"""
        [out:json][timeout:25];
        {query}
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
            print('H', json.dumps(geometry))
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
                    print('A', json.dumps(geometry))
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
def get_object_data4tooltip(obj):
    heading = f'{obj}'
    if obj.gone:
        heading += '<br /><span style="color: red;">hävinud</span>'
    if obj.profiilipildid.exists():
        profiilipilt = obj.profiilipildid.first()
        img = settings.MEDIA_URL + profiilipilt.pilt_thumbnail.name
        img = f'<br /><img class="tooltip-content-img" src="{img}" alt="{profiilipilt}">'
    else:
        img = ''
    content = f'<div class="kaardiobjekt-tooltip">{heading}{img}</div>'
    return content

def make_big_maps_leaflet(aasta=None, objekt=None):
    kaardid = Kaart.objects.exclude(tiles__exact='').order_by('aasta')
    if aasta and Kaart.objects.filter(aasta=aasta).count()==0:
        tekst = f'<h4>{aasta}. aasta kaarti ei ole. Vali järgmistest:</h4>'
        for kaart in kaardid:
            href = reverse('kaart')
            tekst += f'<p class="hover-objekt"><a href="{href}{kaart.aasta}">{kaart}</a><p>'
        return tekst
    else:
        # Kas vaja näidata kaartidel objekti?
        obj = Objekt.objects.none()
        objektiga_kaardid = []
        objektiga_kaart_max = DEFAULT_MAP
        if objekt:
            try:
                obj = Objekt.objects.get(id=objekt)
            except ObjectDoesNotExist:
                pass
            if obj:
                objektiga_kaardiobjektid = obj.kaardiobjekt_set.filter()
                if objektiga_kaardiobjektid:
                    objektiga_kaardid = [kaardiobjekt.kaart.aasta for kaardiobjekt in objektiga_kaardiobjektid]
                    objektiga_kaart_max = max(objektiga_kaardid)
                    # objektiga_kaart_min = min(objektiga_kaardid)

        # Loome aluskaardi
        # zoom_start = DEFAULT_MAP_ZOOM_START
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

        map_name = map.get_name()
        feature_groups = {} # erinevate aastate kaardid
        feature_groups_kaardiobjektid = {} # erinevate aastate kaartidel m2rgitud kaardiobjektid

        for kaart in kaardid:
            kaart_aasta = kaart.aasta
            if kaart_aasta in objektiga_kaardid:
                color = GEOJSON_STYLE['HE']['color']
                name = f'<span class="kaart-control-layers" style="color: {color};">{kaart_aasta}</span>' # fuchsia
            elif kaart_aasta == DEFAULT_MAP.aasta and objektiga_kaardid and obj.gone:
                color = GEOJSON_STYLE['HH']['color']
                name = f'<span class="kaart-control-layers" style="color: {color};">{kaart_aasta}</span>' # red
            else:
                name = f'<span class="kaart-control-layers" style="color: #A9A9A9;">{kaart_aasta}</span>' # darkgrey

            # loome kaardikihi
            feature_group = folium.FeatureGroup(
                name=name,
                overlay=False,
            )
            feature_groups[kaart_aasta] = feature_group.get_name()

            # lisame kaardikihile rasterkihi
            tilelayer = folium.TileLayer(
                location=DEFAULT_CENTER,
                # name=kaart.aasta,
                tiles=kaart.tiles,
                zoom_start=DEFAULT_MAP_ZOOM_START,
                min_zoom=DEFAULT_MIN_ZOOM,
                attr=f'{kaart.__str__()}<br>{kaart.viited.first()}',
                id=kaart.aasta
            )

            if obj: # lisame kaardikihile vektorkihi kui on objekti kaardiobjektid
                if kaart == DEFAULT_MAP:
                    kaardiobjektid = obj.kaardiobjekt_set.filter(kaart__aasta__exact=objektiga_kaart_max)
                    if obj.gone:
                        tilelayer_stamen_toner = folium.TileLayer("Stamen Toner")
                        tilelayer.tiles = tilelayer_stamen_toner.tiles
                else:
                    kaardiobjektid = obj.kaardiobjekt_set.filter(kaart=kaart)

                for kaardiobjekt in kaardiobjektid:
                    geometry = kaardiobjekt.geometry
                    tyyp = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
                    name = f'{kaardiobjekt.__str__()} ({dict(Kaardiobjekt.TYYP)[tyyp].lower()})'
                    if kaart == DEFAULT_MAP and obj.gone:
                        fillColor = GEOJSON_STYLE[f'{tyyp}H']["fill"]
                        color = GEOJSON_STYLE[f'{tyyp}H']["color"]
                        weight = GEOJSON_STYLE[f'{tyyp}H']["weight"]
                    else:
                        fillColor = GEOJSON_STYLE[f'{tyyp}E']["fill"]
                        color = GEOJSON_STYLE[f'{tyyp}E']["color"]
                        weight = GEOJSON_STYLE[f'{tyyp}E']["weight"]
                    feature_collection = {
                        "type": "FeatureCollection",
                        "name": name,
                        "features": [geometry]
                    }
                    f = json.dumps(feature_collection)
                    geojson = folium.GeoJson(
                        f,
                        name=name,
                        style_function=lambda x, fillColor=fillColor, color=color: {
                            "fillColor": fillColor,
                            "color": color,
                            "weight": weight
                        },
                        tooltip=get_object_data4tooltip(obj),
                        highlight_function=lambda x: {"fillOpacity": 0.5},
                    )
                    geojson.add_to(feature_group)

            # Loome kaardi olemasolevate m2rgtud kaardiobjektide kihi
            if kaart == DEFAULT_MAP: # kaasaja kaardil kaardiobjekte liiga palju
                kaardiobjektid = Kaardiobjekt.objects.\
                    filter(kaart=kaart).\
                    filter(objekt__isnull=False).\
                    filter(objekt__gone__exact=False)
            else:
                kaardiobjektid = Kaardiobjekt.objects.filter(kaart=kaart)

            if kaardiobjektid:
                feature_group_kaardiobjektid = folium.FeatureGroup(
                    name=f'<span class="kaart-control-layers">Kaardiobjektid {kaart.aasta}</span>',
                    show=False
                )
                for kaardiobjekt in kaardiobjektid:
                    tyyp = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
                    tooltip = f'<div class="kaardiobjekt-tooltip">{kaardiobjekt}</div>'
                    fillColor = GEOJSON_STYLE[tyyp]["fill"]
                    color = GEOJSON_STYLE[tyyp]["color"]
                    weight = GEOJSON_STYLE[tyyp]["weight"]
                    if kaardiobjekt.objekt: # kui seotud objektiga
                        tooltip = get_object_data4tooltip(kaardiobjekt.objekt)
                        if kaardiobjekt.objekt.gone: # hävinud
                            fillColor = GEOJSON_STYLE[f'{tyyp}H']["fill"]
                            color = GEOJSON_STYLE[f'{tyyp}H']["color"]
                            weight = GEOJSON_STYLE[f'{tyyp}H']["weight"]
                        else: # alles
                            fillColor = GEOJSON_STYLE[f'{tyyp}E']["fill"]
                            color = GEOJSON_STYLE[f'{tyyp}E']["color"]
                            weight = GEOJSON_STYLE[f'{tyyp}E']["weight"]
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
                        style_function=lambda x, fillColor=fillColor, color=color: {
                            "fillColor": fillColor,
                            "color": color,
                            "weight": weight
                        },
                        tooltip=tooltip,
                        highlight_function=lambda x: {"fillOpacity": 0.5},
                    )
                    geojson.add_to(feature_group_kaardiobjektid)
                # end for kaardiobjekt in kaardiobjektid:

                feature_group_kaardiobjektid.add_to(map)
                feature_groups_kaardiobjektid[aasta] = feature_group_kaardiobjektid
            # end if kaardiobjektid:

            # Lisame kaardile kirjelduse tootipi
            kwargs = {
                'direction': 'center',
                'permanent': False,
                # 'sticky': False,
                'interactive': True,
                'opacity': 0.9,
            }
            tooltip = folium.Tooltip(
                kaart.kirjeldus_html,
                **kwargs
            )
            tooltip.add_to(tilelayer)
            tilelayer.add_to(feature_group)
            feature_group.add_to(map)

        # Piirid tänapäeval
        style1 = {'fill': None, 'color': '#00FFFF', 'weight': 5}
        with open(UTIL_DIR / 'geojson' / "piirid.geojson") as gf:
            src = json.load(gf)
            geojson = folium.GeoJson(
                src,
                name=f'<span class="kaart-control-layers">linnapiirid (2021)</span>',
                style_function=lambda x: style1
            )
            geojson.add_to(map)

        # Tänavatevõrk tänapäeval
        style2 = {'fill': None, 'color': 'orange', 'weight': 2}
        with open(UTIL_DIR / 'geojson' / "teedev6rk_2021.geojson") as gf:
            src = json.load(gf)
            geojson = folium.GeoJson(
                src,
                name=f'<span class="kaart-control-layers">tänavad (2021)</span>',
                style_function=lambda x: style2
            )
            geojson.add_to(map)

        # Lisame kihtide kontrolli kaartide jaoks
        layer_control = folium.LayerControl()
        layer_control.add_to(map)

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

        el = folium.MacroElement().add_to(map)
        # js = map_name + """
        # .on('baselayerchange', function (eventLayer) {
        #     // console.log(eventLayer.name);
        # });\n
        # """
        js = ''

        if aasta:
            for kaart in feature_groups.keys():
                fg = feature_groups[kaart]
                if kaart == aasta:
                    # js += f'console.log({layer_control.get_name()});\n'
                    js += f'{map_name}.addLayer({fg});\n'
                else:
                    js += f'{map_name}.removeLayer({fg});\n'

        # Lisab javascripti <script> tagi lõppu
        el._template = jinja2.Template('''
        {{% macro script(this, kwargs) %}}
            {0}
        {{% endmacro %}}'''.format(js))

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

# Konkreetse objekti erinevate aastate kaardid koos
def make_objekt_leaflet_combo(objekt=1):
    obj = Objekt.objects.get(id=objekt)
    # Kõigi kaartide ids, kus objekt märgitud: tulemus: <QuerySet ['1', '2', '3']>
    kaart_ids = obj.kaardiobjekt_set.values_list('kaart__id', flat=True)

    if kaart_ids:
        kaardid = Kaart.objects.filter(id__in=kaart_ids)
        objekt_missing_on_defaultmap = DEFAULT_MAP.id not in kaart_ids  # Objekti kaasajal pole?
        hiliseim_kaart_aasta = max([kaart.aasta for kaart in kaardid])

        if objekt_missing_on_defaultmap:
            # Lisame vaate, millel näitame virtuaalset asukohta tänapäeval
            kaardid = kaardid | Kaart.objects.filter(id=DEFAULT_MAP.id)

        feature_group = {}
        zoom_start = DEFAULT_MAP_ZOOM_START
        location = DEFAULT_CENTER

        for kaart in kaardid:
            aasta = kaart.aasta
            url = reverse('kaart')

            feature_group[aasta] = folium.FeatureGroup(
                name=f'<span class="kaart-control-layers">{aasta}</span>',
                overlay=False
            )

            tile_kwargs = {
                'url': url,
                'aasta': aasta,
                'objektId': objekt
            }
            if kaart == DEFAULT_MAP and objekt_missing_on_defaultmap:
                folium.TileLayer(
                    location=location,
                    name=aasta,
                    tiles="Stamen Toner",
                    zoom_start=zoom_start,
                    min_zoom=DEFAULT_MIN_ZOOM,
                    **tile_kwargs
                ).add_to(feature_group[aasta])
            else:
                kaardiobjektid = obj.kaardiobjekt_set.filter(kaart=kaart)
                if kaardiobjektid[0].geometry:
                    location = kaardiobjektid[0].centroid
                folium.TileLayer(
                    location=location,
                    name=aasta,
                    tiles=kaart.tiles,
                    zoom_start=zoom_start,
                    min_zoom=DEFAULT_MIN_ZOOM,
                    attr=f'{kaart.__str__()}<br>{kaart.viited.first()}',
                    **tile_kwargs
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
                    if obj.gone:  # objekti kaasajal pole
                        tyyp_style = f'{kaardiobjekt.tyyp}H'  # 'HH'-hoonestus, 'AH'-ala, 'MH'-muu
                    else:  # objekt kaasajal olemas
                        tyyp_style = kaardiobjekt.tyyp  # 'H'-hoonestus, 'A'-ala, 'M'-muu
                    style = GEOJSON_STYLE[tyyp_style]
                    f = json.dumps(feature_collection)
                    folium.GeoJson(
                        f,
                        name=name,
                        style_function=lambda x: style
                    ).add_to(feature_group[aasta])
                    if kaart.aasta == hiliseim_kaart_aasta and objekt_missing_on_defaultmap:
                        folium.GeoJson(
                            f,
                            name=name,
                            style_function=lambda x: style
                        ).add_to(feature_group[DEFAULT_MAP.aasta])
                    # Kui on antud zoomimise tase, siis kasutame seda
                    if kaardiobjekt.zoom and (zoom_start > kaardiobjekt.zoom):
                        zoom_start = kaardiobjekt.zoom

                # Parandame zoomi, kui mõnel kihil on määratud TODO: ei toimi
                # tilelayer.zoom_start = zoom_start

        # Loome aluskaardi
        kwargs = {  # vajalikud mobiilis kerimise h6lbustamiseks
            'dragging': '!L.Browser.mobile',
            'tap': '!L.Browser.mobile'
        }
        map = folium.Map(
            location=location,  # NB! tagurpidi: [lat, lon],
            zoom_start=zoom_start,
            min_zoom=DEFAULT_MIN_ZOOM,
            zoom_control=True,
            # control_scale=True,
            tiles=None,
            **kwargs
        )

        map.default_css = LEAFLET_DEFAULT_CSS
        map.default_js = LEAFLET_DEFAULT_JS
        LEAFLET_DEFAULT_HEADER.add_to(map.get_root().header)

        for aasta in feature_group.keys():
            # Lisame kaardi leaflet combosse
            feature_group[aasta].add_to(map)

        # Piirid tänapäeval
        style1 = {'fill': None, 'color': '#00FFFF', 'weight': 5}
        with open(UTIL_DIR / 'geojson' / "piirid.geojson") as gf:
            src = json.load(gf)
            folium.GeoJson(
                src,
                name=f'<span class="kaart-control-layers">linnapiirid (2021)</span>',
                style_function=lambda x: style1
            ).add_to(map)

        # Tänavatevõrk tänapäeval
        style2 = {'fill': None, 'color': 'orange', 'weight': 2}
        with open(UTIL_DIR / 'geojson' / "teedev6rk_2021.geojson") as gf:
            src = json.load(gf)
            folium.GeoJson(
                src,
                name=f'<span class="kaart-control-layers">tänavad (2021)</span>',
                style_function=lambda x: style2
            ).add_to(map)

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
            # '<span style="color:#565656">Kaarti laetakse. Kui see kiri jääb nähtavaks, tekkis laadimisel viga</span>',
            '',
            1
        )
        return map_html

# Konkreetse kaardiobjekti kaart
def make_kaardiobjekt_leaflet(kaardiobjekt_id=1):
    kaardiobjekt = Kaardiobjekt.objects.get(id=kaardiobjekt_id)
    if kaardiobjekt:
        zoom_start = kaardiobjekt.zoom if kaardiobjekt.zoom else DEFAULT_MAP_ZOOM_START
        # Loome aluskaardi
        map = folium.Map(
            location=kaardiobjekt.centroid, # kaardiobjekt.centroid,  # NB! tagurpidi: [lat, lon],
            zoom_start=zoom_start,
            min_zoom=DEFAULT_MIN_ZOOM,
            zoom_control=True,
            name=kaardiobjekt.kaart.aasta,
            tiles=kaardiobjekt.kaart.tiles,
            attr=f'{kaardiobjekt.kaart.__str__()}',
        )
        map.default_css = LEAFLET_DEFAULT_CSS
        map.default_js = LEAFLET_DEFAULT_JS

        # lisame vektorkihid
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
        ).add_to(map)

        # Lisame kihtide kontrolli
        folium.LayerControl().add_to(map)

        map_html = map._repr_html_()
        # v2ike h2kk, mis muudab vertikaalset suurust
        map_html = map_html.replace(';padding-bottom:60%;', ';padding-bottom:100%;', 1)
        return map_html


if __name__ == "__main__":
    make_big_maps_leaflet(aasta=1824, objekt_id=970)
    # read_kaardiobjekt_csv_to_db('2021')
    # geometry = get_osm_data(street='Rigas', housenumber='9', admin_level='7', country='Latvija', city='Valka')
    # geometry = get_osm_data(street='Kesk', housenumber='12')
    # print(geometry)
    # geometry = get_shp_data('Maleva 3')
    # print(geometry)
    # kaardiobjekt_match_db(20938)
    # read_shp_to_db(aasta='1905') # Loeb kaardikihi shp failist andmebaasi
    # write_db_to_shp(aasta='1905') # Kirjutab andmebaasist kaardikihi shp faili
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