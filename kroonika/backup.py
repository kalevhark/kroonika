from datetime import datetime
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

if __name__ == "__main__":
    import os
    import django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()

from django.conf import settings
from django.core import serializers

from wiki.models import (
    Artikkel, Isik, Organisatsioon, Objekt, Pilt,
    Kaardiobjekt,
    Viide, Allikas
)

MEDIA_DIR = settings.MEDIA_ROOT

# Andmete varundamiseks offline kasutuseks
# Loob valgalinn.ee ajalookroonika koopia json ja xml formaatides

# Salvestame ainult kasutatud allikad
def serverless_save_allikad(path, method, allikas):
    SAVE_PATH = path / method / 'allikad'
    FILE_NAME = SAVE_PATH / f'allikas_{allikas.id}.{method}'
    Serializer = serializers.get_serializer(method)
    serializer = Serializer()
    if not Path.exists(FILE_NAME):
        with open(FILE_NAME, "w", encoding="utf-8") as out:
            serializer.serialize([allikas], stream=out)

# Salvestame ainult kasutatud viited
def serverless_save_viited(path, method, obj):
    viited = obj.viited.all()
    if viited:
        SAVE_PATH = path / method / 'viited'
        for viide in viited:
            # print(viide.id)
            FILE_NAME = SAVE_PATH / f'viide_{viide.id}.{method}'
            Serializer = serializers.get_serializer(method)
            serializer = Serializer()
            if not Path.exists(FILE_NAME):
                with open(FILE_NAME, "w", encoding="utf-8") as out:
                    serializer.serialize([viide], stream=out)
                if viide.allikas:
                    serverless_save_allikad(path, method, viide.allikas)

# Salvestame ainult kasutatud pildid
def serverless_save_pildid(path, method, obj, verbose_name_plural, base_dir, pildifailid):
    filterset = {f'{verbose_name_plural}__in': [obj]}
    pildid = Pilt.objects.filter(**filterset)
    if pildid:
        SAVE_PATH = path / method / 'pildid'
        for pilt in pildid:
            FILE_NAME = SAVE_PATH / f'pilt_{pilt.id}.{method}'
            Serializer = serializers.get_serializer(method)
            serializer = Serializer()
            if not Path.exists(FILE_NAME):
                with open(FILE_NAME, "w", encoding="utf-8") as out:
                    serializer.serialize([pilt], stream=out)
                serverless_save_viited(path, method, pilt)
            pildifail = str(pilt.pilt)
            if Path.exists(base_dir / 'media' / pildifail) and (pildifail not in pildifailid):
                pildifailid.append(pildifail)
    return pildifailid

# Kopeerime pildid BACKUP_DIRi
def serverless_copy_pildid(pildifailid, BACKUP_DIR, BASE_DIR):
    Path(BACKUP_DIR / 'media').mkdir(parents=True, exist_ok=True)
    for fail in pildifailid:
        src = Path(BASE_DIR / 'media' / fail)
        dst = Path(BACKUP_DIR / 'media' / fail)
        dst_dir = dst.parent
        Path(dst_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    print('Kopeeriti', len(pildifailid), 'pilti')

def serverless_make_index(objs, andmebaas, BACKUP_DIR):
    for method in ['xml', 'json']:
        Serializer = serializers.get_serializer(method)
        serializer = Serializer()
        file_name = BACKUP_DIR / method / f'{andmebaas["verbose_name_plural"]}.{method}'
        # with open(file_name, "w", encoding="utf-8") as out:
        #     serializer.serialize(objs, fields=('hist_year', 'hist_date', 'slug'), stream=out)

    # millisest andmebaasi tabelist andmed
    db_table = objs.model._meta.db_table

    # init xml-data
    xml_content = ET.Element('root', attrib={'lang': 'et', 'origin': 'https://valgalinn.ee', 'db_table': db_table})

    # init json-data
    json_content = {
        'origin': 'https://valgalinn.ee',
        'db_table': db_table,
        'data': []
    }

    # init html-data
    html_content = ET.Element('html', attrib={'lang': 'et'})
    html_content_h1 = ET.SubElement(html_content, 'h1')
    html_content_table = ET.SubElement(html_content, 'table')
    html_content_table_thead = ET.SubElement(html_content_table, 'thead')
    html_content_table_tbody = ET.SubElement(html_content_table, 'tbody')

    for obj in objs:
        object = {
            'pk': str(obj.pk),
            'hist_year': str(obj.hist_year),
            'hist_date': obj.hist_date.strftime('%Y-%m-%d') if obj.hist_date else str(obj.hist_date),
            'hist_enddate': obj.hist_enddate.strftime('%Y-%m-%d') if obj.hist_enddate else str(obj.hist_enddate),
            'obj': str(obj),
            'JSON': f'json/{andmebaas["verbose_name_plural"]}/{andmebaas["acronym"]}_{obj.id}.json',
            'XML':  f'xml/{andmebaas["verbose_name_plural"]}/{andmebaas["acronym"]}_{obj.id}.xml'
        }

        # Lisame xml elemendi
        xml_content_object = ET.SubElement(xml_content, 'object')
        for field in object.keys():
            xml_content_field = ET.SubElement(xml_content_object, 'field', attrib={'name': field})
            xml_content_field.text = object[field]

        # Lisame json elemendi
        json_content['data'].append(object)

        # Lisame html elemendi
        if not html_content_table_thead.findall("./tr"): # kui tabeli päist ei ole
            # link = '<a href="https://valgalinn.ee" target="_blank">valgalinn.ee</a>'
            link = 'https://valgalinn.ee'
            html_content_h1.text = f'Väljavõte {link} veebilehe andmetabelist {db_table}'
            html_content_table_thead_tr = ET.SubElement(html_content_table_thead, 'tr')
            for field in object.keys():
                html_content_table_thead_tr_th = ET.SubElement(html_content_table_thead_tr, 'th')
                html_content_table_thead_tr_th.text = field

        html_content_table_tbody_tr = ET.SubElement(html_content_table_tbody, 'tr')
        for field in object.keys():
            html_content_table_tbody_tr_td = ET.SubElement(html_content_table_tbody_tr, 'td')
            if field in ['JSON', 'XML']:
                html_content_table_tbody_tr_td_a = ET.SubElement(
                    html_content_table_tbody_tr_td,
                    'a',
                    attrib={'href': object[field]}
                )
                html_content_table_tbody_tr_td_a.text = field
            else:
                html_content_table_tbody_tr_td.text = object[field]

    xml_content_file_name = BACKUP_DIR / 'xml' / f'{andmebaas["verbose_name_plural"]}.xml'
    tree = ET.ElementTree(xml_content)
    tree.write(xml_content_file_name, encoding = "UTF-8", xml_declaration = True)

    json_content_file_name = BACKUP_DIR / 'json' / f'{andmebaas["verbose_name_plural"]}.json'
    with open(json_content_file_name, "w", encoding = "UTF-8") as write_file:
        json.dump(json_content, write_file)

    html_content_file_name = BACKUP_DIR / f'{andmebaas["verbose_name_plural"]}.html'
    # write_file.write(ET.dump(html_content))
    tree = ET.ElementTree(html_content)
    tree.write(html_content_file_name, encoding = "UTF-8")

def backup2serverless(objects=10):
    BASE_DIR = Path(__file__).resolve().parent
    print('Alustasime:', datetime.now())

    # Loome backup kataloogistruktuuri
    now = datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M')
    BACKUP_DIR = BASE_DIR / now_string
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    for method in ['xml', 'json']:
        Path(BACKUP_DIR / method / 'artiklid').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'isikud').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'organisatsioonid').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'objektid').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'viited').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'allikad').mkdir(parents=True, exist_ok=True)
        Path(BACKUP_DIR / method / 'pildid').mkdir(parents=True, exist_ok=True)

    pildifailid = []

    andmebaasid = [
        {'model': Artikkel, 'verbose_name_plural': 'artiklid', 'acronym': 'art'}, # Lood
        {'model': Isik, 'verbose_name_plural': 'isikud', 'acronym': 'isik'}, # Isikud
        {'model': Organisatsioon, 'verbose_name_plural': 'organisatsioonid', 'acronym': 'org'},  # Asutised
        {'model': Objekt, 'verbose_name_plural': 'objektid', 'acronym': 'obj'},  # Kohad
    ]

    for andmebaas in andmebaasid:
        objs = andmebaas['model'].objects.daatumitega(request=None)
        if objects > 0:
            objs = objs[:objects]
        print(f'Kopeerime {andmebaas["verbose_name_plural"]}:', len(objs), 'objekti...', end=' ')

        for method in ['xml', 'json']:
            print(method, end=' ')
            Serializer = serializers.get_serializer(method)
            serializer = Serializer()
            for obj in objs:
                serverless_save_viited(
                    BACKUP_DIR,
                    method,
                    obj
                )
                pildifailid = serverless_save_pildid(
                    BACKUP_DIR,
                    method,
                    obj,
                    andmebaas['verbose_name_plural'],
                    BASE_DIR,
                    pildifailid
                )
                file_name = BACKUP_DIR / method / andmebaas['verbose_name_plural'] / f'{andmebaas["acronym"]}_{obj.id}.{method}'

                serializer.serialize([obj])
                data = serializer.getvalue()

                # Lisame pildiviited
                filterset = {f"{andmebaas['verbose_name_plural']}__in": [obj]}
                pildid = [pilt.id for pilt in Pilt.objects.filter(**filterset)]

                if method == 'json':
                    json_src = json.loads(data)[0]
                    json_src['fields']['pildid'] = pildid
                    dst = json.dumps(json_src)
                    with open(file_name, "w", encoding="utf-8") as out:
                        out.write(dst)
                elif method == 'xml':
                    xml_src = ET.fromstring(data)
                    # <field name="viited" rel="ManyToManyRel" to="wiki.viide"><object pk="2459"></object>
                    fields = xml_src.find('object')
                    field_pildid = ET.SubElement(fields, "field", {"name": "pildid", "rel": "ManyToManyRel", "to": "wiki.pilt"})
                    for pilt in pildid:
                        object_pilt = ET.SubElement(field_pildid, 'object', attrib={'pk': str(pilt)})
                    dst = ET.ElementTree(xml_src)
                    # tree = ET.ElementTree(html_content)
                    dst.write(file_name, encoding="UTF-8", xml_declaration=True)
                else:
                    continue

        print('loome indeksi', end=' ')
        serverless_make_index(objs, andmebaas, BACKUP_DIR)

        print('OK')

    # kopeerime asjakohased pildid BACKUP_DIRi
    serverless_copy_pildid(pildifailid, BACKUP_DIR, BASE_DIR)

    print('Lõpetasime:', datetime.now())

if __name__ == "__main__":
    # backup2serverless(objects=10) # objects=0 = täiskoopia
    pass

# Andmete varundamiseks offline kasutuseks
# Loob valgalinn.ee ajalookroonika koopia pdf formaadis

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle as PS
from reportlab.lib.units import cm, inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame, FrameBreak,
    Image, Paragraph, Spacer,
    Table, TableStyle,
    NextPageTemplate, CondPageBreak, PageBreak, PageTemplate, KeepTogether
)
from reportlab.platypus.tableofcontents import TableOfContents, SimpleIndex

# we know some glyphs are missing, suppress warnings
# import reportlab.rl_config
# reportlab.rl_config.warnOnMissingFontGlyphs = 0
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
# pdfmetrics.registerFont(TTFont('VeraBd', 'VeraBd.ttf'))
# pdfmetrics.registerFont(TTFont('VeraIt', 'VeraIt.ttf'))
# pdfmetrics.registerFont(TTFont('VeraBI', 'VeraBI.ttf'))
#
# from reportlab.pdfbase.pdfmetrics import registerFontFamily
# registerFontFamily('Vera',normal='Vera',bold='VeraBd',italic='VeraIt',boldItalic='VeraBI')

from wiki.models import KUUD

PAGE_WIDTH, PAGE_HEIGHT = A4

TOP_MARGIN = A4[1] - inch
BOTTOM_MARGIN = inch
LEFT_MARGIN = inch
RIGHT_MARGIN = A4[0] - inch
FRAME_WIDTH = RIGHT_MARGIN - LEFT_MARGIN
FRAME_HEIGHT = TOP_MARGIN - BOTTOM_MARGIN

styles = getSampleStyleSheet()

# valgalinn.ee värvid
TEXT_ARTIKKEL_COLOR = '#00985F' # cmyk(100%, 0%, 38%, 40%)
TEXT_ISIK_COLOR = '#00aba9' # cmyk(100%, 0%, 1%, 33%)
TEXT_ORGANISATSIOON_COLOR = '#2d89ef' # cmyk(81%, 43%, 0%, 6%)
TEXT_OBJEKT_COLOR = '#2b5797' # cmyk(72%, 42%, 0%, 41%)

T = styles['Title']
C = PS(
    name='Chapter',
    parent=T
)
H1 = PS(
    name='Heading1',
    fontSize=16,
    leading=16,
    spaceAfter=6,
    spaceBefore=6,
    keepWithNext=1
)
TOC1 = PS(
    name='TOC1',
    fontSize=14,
    spaceAfter=12,
    spaceBefore=12,
    parent=H1
)
H2 = PS(
    name='Heading2',
    fontSize=14,
    leading=16,
    spaceAfter=12,
    spaceBefore=12,
    keepWithNext=1
)
TOC2 = PS(
    name='TOC2',
    spaceAfter=6,
    spaceBefore=6,
    keepWithNext=1,
    parent=H2
)

H3 = PS(
    name='Heading3',
    fontSize=12,
    leading=14,
    spaceAfter=12,
    spaceBefore=12,
    keepWithNext=1
)
TOC3 = PS(
    name='TOC3',
    leftIndent=2 * cm,
    spaceAfter=0,
    spaceBefore=0,
    keepWithNext=0,
    parent=H3
)
P = PS(
    name='kirjeldus',
    fontSize=10,
    spaceAfter=6
)
P_ARTIKKEL = PS(
    name='kirjeldus_colored',
    textColor=TEXT_ARTIKKEL_COLOR,
    parent=P
)
V = PS(
    name='viide',
    fontSize=8
)
V_ERROR = PS(
    name='viide_error',
    # fontSize=8,
    textColor='red',
    parent=V
)

# custom canvasmaker for multiple indecees
def myCanvasMaker(indeces=[], canvasmaker=canvas.Canvas):
    def newcanvasmaker(*args, **kwargs):
        c = canvasmaker(*args, **kwargs)
        for ix in indeces: # here's where we put the index
            setattr(c,ix.name,ix) # on the canvas
        return c
    return newcanvasmaker

# main document template
class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        self.section = ''
        BaseDocTemplate.__init__(self, filename, **kw)
        template = PageTemplate('normal', [Frame(inch, inch, FRAME_WIDTH, FRAME_HEIGHT, id='F1')])
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):

        def add_outline_entry(flowable, level):
            pass

        "Registers TOC entries."
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Chapter':
                self.notify('TOCEntry', (0, text, self.page))
                self.section = text.lower()
                key = f'ch_{text}'
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=0, closed=0)
            if style == 'Heading1':
                self.notify('TOCEntry', (0, text, self.page))
                self.section = text.lower()
                key = f'h1_{text}'
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=0, closed=0)
            if style == 'Heading2':
                self.notify('TOCEntry', (1, text, self.page))
                key = f'h2_{self.section}_{text}'
                self.canv.bookmarkPage(key)
                try:
                    self.canv.addOutlineEntry(text, key, level=1, closed=0)
                except:
                    self.canv.addOutlineEntry(text, key, level=0, closed=0)
            if style == 'Heading3':
                self.notify('TOCEntry', (2, text, self.page))

def story_seotud_viited(story, obj):
    viited =  obj.viited.all()
    if viited:
        for viide in viited:
            story.append(Paragraph(f'{viide}', V))
    # story.append(Spacer(18, 18))
    return story

def story_seotud_objectid(story, obj, seotud_model, seotud_objectid_index = ''):
    seotud_model_verbose = seotud_model._meta.verbose_name.lower()
    ids = [object.id for object in obj.__getattribute__(seotud_model_verbose).all()]
    seotud_objectid = seotud_model.objects.daatumitega(request=None).filter(id__in=ids)
    if seotud_objectid:
        if not isinstance(obj, Artikkel):
            story.append(Paragraph(f'Seotud {seotud_model_verbose}:', P))
        for seotud_object in seotud_objectid:
            seotud_object_clean = repr(seotud_object).replace(',', ',,').replace('"', '&quot')  # topeltkoma = ','
            if not isinstance(obj, Artikkel):
                story.append(
                    Paragraph(
                        f'<index name="{seotud_model_verbose}" item="{seotud_object_clean}" />{seotud_object}', V
                    )
                )
            seotud_objectid_index += f'<index name="{seotud_model_verbose}" item="{seotud_object_clean}" />'
    return story, seotud_objectid_index

from reportlab.lib import utils
def get_image_withwidth(path, width=inch):
    img = utils.ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return Image(path, width=width, height=(width * aspect))

def get_image_withheight2(path, height=inch):
    img = utils.ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    width = height / aspect
    if width > FRAME_WIDTH / 2:
        height = height * ((FRAME_WIDTH / 2) / float(width))
        width = FRAME_WIDTH / 2
    print(path, width, height)
    return Image(path, width=width, height=height)

from reportlab.lib.styles import ParagraphStyle
def get_image_withheight(path, height=inch):
    image = Image(path)
    # print(image.imageHeight / 72, end=' ')
    width, height = image._restrictSize(height, FRAME_WIDTH / 2)
    # print(image.imageHeight/72, end=' ')
    image = Image(path, width=width, height=height)
    # print(image.imageHeight / 72, path)
    # print(image.wrap(FRAME_WIDTH, FRAME_WIDTH), path)
    return image

def story_seotud_pildid(obj):
    pilt = obj.profiilipilt()
    flowables = []
    if pilt:
        pildi_fail = MEDIA_DIR / pilt.pilt.name
        flowables.append(Spacer(6, 6))
        flowables.append(get_image_withheight(pildi_fail, height=2 * inch))
        if pilt.viited.first():
            flowables.append(Paragraph(f'Allikas: {pilt.viited.first()}', V))
            fmt = V
        else:
            fmt = V_ERROR
        flowables.append(Paragraph(f'Fail: {pilt.pilt}', fmt))
        flowables.append(Spacer(12, 12))
    return flowables

def story_artiklid(story, objects=10, algus_aasta=0, l6pp_aasta=1899):
    filterset = {'hist_year__lte': l6pp_aasta}
    if algus_aasta:
        filterset['hist_year__gte'] = algus_aasta

    objs = Artikkel.objects.daatumitega(request=None).filter(**filterset)
    if objects > 0:
        objs = objs[:objects]
    jooksev_aasta = 0
    jooksev_kuu = 0
    for obj in objs:
        if obj.hist_year != jooksev_aasta:
            jooksev_aasta = obj.hist_year
            story.append(Paragraph(f'<font color="{TEXT_ARTIKKEL_COLOR}">{obj.hist_year}</font>', H2))
        if obj.hist_date:
            hist_dates = obj.hist_date.strftime(settings.DATE_INPUT_FORMATS[0])
            kuu = obj.hist_date.month
            if obj.hist_enddate:
                hist_dates = '-'.join([hist_dates, obj.hist_enddate.strftime('%d.%m.%Y')])
        else:
            if obj.hist_month:
                kuu = obj.hist_month
                hist_dates = f'{obj.hist_year} {KUUD[obj.hist_month-1][1]}'
            else:
                kuu = 0
                hist_dates = str(obj.hist_year)
        if obj.viited.exists():
            color = TEXT_ARTIKKEL_COLOR
        else:
            color = 'red'
        if hist_dates:
            hist_dates = f'<font color="{color}"><strong>{hist_dates}</strong></font>'
        if kuu != jooksev_kuu:
            jooksev_kuu = kuu
            if kuu > 0:
                story.append(Paragraph(f'<font color="{TEXT_ARTIKKEL_COLOR}">{KUUD[jooksev_kuu-1][1]}</font>', H3))

        seotud_objectid_index = ''
        story, seotud_objectid_index = story_seotud_objectid(
            story, obj,
            seotud_model=Isik,
            seotud_objectid_index=seotud_objectid_index
        )
        story, seotud_objectid_index = story_seotud_objectid(
            story, obj,
            seotud_model=Organisatsioon,
            seotud_objectid_index=seotud_objectid_index)
        story, seotud_objectid_index = story_seotud_objectid(
            story, obj,
            seotud_model=Objekt,
            seotud_objectid_index=seotud_objectid_index
        )

        story.append(Spacer(18, 18))

        body_text = ' '.join([hist_dates, obj.body_text]).strip()
        profiilipilt = story_seotud_pildid(obj)
        if profiilipilt:
            story.append(KeepTogether(profiilipilt))

        story.append(Paragraph(f'{body_text}{seotud_objectid_index}', P))
        url = obj.get_absolute_url()
        story.append(
            Paragraph(
                f'<link color="{TEXT_ARTIKKEL_COLOR}" href="https://valgalinn.ee{url}">https://valgalinn.ee{url}</link>', V
            )
        )

        viited = obj.viited.all()
        if viited:
            for viide in viited:
                story.append(Paragraph(f'{viide}', V))
    print('Lugusid:', objs.count())
    return story

def story_isikud(story, objects=10):
    objs = Isik.objects.daatumitega(request=None)
    if objects > 0:
        objs = objs[:objects]
    jooksev_t2ht = ''
    for obj in objs:
        t2ht = obj.perenimi[0].upper()
        if t2ht in ['V', 'W']:
            t2ht = 'V,W'
        if t2ht != jooksev_t2ht:
            jooksev_t2ht = t2ht
            story.append(Paragraph(f'<font color="{TEXT_ISIK_COLOR}">{jooksev_t2ht}</font>', H2))

        if obj.viited.exists():
            color = TEXT_ISIK_COLOR
        else:
            color = 'red'
        story.append(Spacer(12, 12))
        isik_index = repr(obj).replace(',', ',,')  # topeltkoma = ','
        story.append(
            Paragraph(
                f'<index name="isikud" item="{isik_index}" /><font color="{color}"><strong>{obj}</strong></font>', P
            )
        )

        url = obj.get_absolute_url()
        story.append(
            Paragraph(
                f'<link color="{TEXT_ISIK_COLOR}" href="https://valgalinn.ee{url}">https://valgalinn.ee{url}</link>', V
            )
        )

        # sünniandmed
        daatumid = []
        dob_string = ''
        if obj.hist_date:
            dob_string = obj.hist_date.strftime(settings.DATE_INPUT_FORMATS[0])
        elif obj.hist_year:
            dob_string = str(obj.hist_year)
        if obj.synd_koht:
            dob_string = ' '.join([dob_string, obj.synd_koht])
        if dob_string:
            daatumid.append(Paragraph(f'Sündinud: {dob_string}'))
        # surmaandmed
        doe_string = ''
        if obj.hist_enddate:
            doe_string = obj.hist_enddate.strftime(settings.DATE_INPUT_FORMATS[0])
        elif obj.hist_endyear:
            doe_string = str(obj.hist_enddate)
        if obj.surm_koht:
            doe_string = ' '.join([doe_string, obj.surm_koht])
        if obj.maetud:
            doe_string = ' '.join([doe_string, 'maetud:', obj.maetud])
        if doe_string:
            daatumid.append(Paragraph(f'Surnud: {doe_string}'))

        profiilipilt = story_seotud_pildid(obj)
        if profiilipilt:
            data = [[profiilipilt, daatumid]]
            t = Table(data, hAlign='LEFT')
            t.setStyle(
                TableStyle(
                    [
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]
                )
            )
            story.append(t)
        story.append(Paragraph(f'{obj.kirjeldus}', P))

        story = story_seotud_viited(story, obj)
        story, _ = story_seotud_objectid(
            story, obj,
            seotud_model=Organisatsioon,
            seotud_objectid_index=''
        )
        story, _ = story_seotud_objectid(
            story, obj,
            seotud_model=Objekt,
            seotud_objectid_index=''
        )
    print('Isikuid:', objs.count())
    return story

def story_organisatsioonid(story, objects=10):
    objs = Organisatsioon.objects.daatumitega(request=None)
    if objects > 0:
        objs = objs[:objects]
    jooksev_t2ht = ''
    for obj in objs:
        t2ht = obj.slug[0].upper()
        if t2ht in ['V', 'W']:
            t2ht = 'V,W'
        if t2ht != jooksev_t2ht: # kasutame slug välja, et ignoreerida jutumärke nime alguses
            jooksev_t2ht = t2ht
            story.append(Paragraph(f'<font color="{TEXT_ORGANISATSIOON_COLOR}">{jooksev_t2ht}</font>', H2))
        if obj.viited.exists():
            color = TEXT_ORGANISATSIOON_COLOR
        else:
            color = 'red'
        story.append(Spacer(12, 12))
        organisatsioon_index = repr(obj).replace(',', ',,').replace('"', '&quot')  # topeltkoma = ','
        story.append(
            Paragraph(
                f'<index name="organisatsioonid" item="{organisatsioon_index}" /><font color="{color}"><strong>{obj}</strong></font>', P
            )
        )

        url = obj.get_absolute_url()
        story.append(
            Paragraph(
                f'<link color="{TEXT_ORGANISATSIOON_COLOR}" href="https://valgalinn.ee{url}">https://valgalinn.ee{url}</link>', V
            )
        )

        daatumid = []
        # sünniandmed
        dob_string = ''
        if obj.hist_date:
            dob_string = obj.hist_date.strftime(settings.DATE_INPUT_FORMATS[0])
        elif obj.hist_year:
            dob_string = str(obj.hist_year)
        if dob_string:
            daatumid.append(Paragraph(f'Asutatud: {dob_string}'))
        # surmaandmed
        doe_string = ''
        if obj.hist_enddate:
            doe_string = obj.hist_enddate.strftime(settings.DATE_INPUT_FORMATS[0])
        elif obj.hist_endyear:
            doe_string = str(obj.hist_endyear)
        if doe_string:
            daatumid.append(Paragraph(f'Lõpetatud: {doe_string}'))

        profiilipilt = story_seotud_pildid(obj)
        if profiilipilt:
            data = [[profiilipilt, daatumid]]
            t = Table(data, hAlign='LEFT')
            t.setStyle(
                TableStyle(
                    [
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]
                )
            )
            story.append(t)
        story.append(Paragraph(f'{obj.kirjeldus}', P))

        story = story_seotud_viited(story, obj)
        story, _ = story_seotud_objectid(
            story, obj,
            seotud_model=Objekt,
            seotud_objectid_index=''
        )
    print('Asutisi:', objs.count())
    return story

def story_objektid(story, objects=10):
    objs = Objekt.objects.daatumitega(request=None)
    if objects > 0:
        objs = objs[:objects]
    jooksev_t2ht = ''
    for obj in objs:
        t2ht = obj.slug[0].upper()
        if t2ht in ['V', 'W']:
            t2ht = 'V,W'
        if t2ht != jooksev_t2ht:
            jooksev_t2ht = t2ht
            story.append(Paragraph(f'<font color="{TEXT_OBJEKT_COLOR}">{jooksev_t2ht}</font>', H2))
        if obj.viited.exists():
            color = TEXT_OBJEKT_COLOR
        else:
            color = 'red'
        story.append(Spacer(12, 12))
        objekt_index = repr(obj).replace(',', ',,').replace('"', '&quot')  # topeltkoma = ','
        story.append(
            Paragraph(
                f'<index name="objektid" item="{objekt_index}" /><font color="{color}"><strong>{obj}</strong></font>', P
            )
        )

        url = obj.get_absolute_url()
        story.append(
            Paragraph(
                f'<link color="{TEXT_OBJEKT_COLOR}" href="https://valgalinn.ee{url}">https://valgalinn.ee{url}</link>', V
            )
        )

        daatumid = []
        # sünniandmed
        dob_string = ''
        if obj.hist_date:
            dob_string = obj.hist_date.strftime(settings.DATE_INPUT_FORMATS[0])
        elif obj.hist_year:
            dob_string = str(obj.hist_year)
        if dob_string:
            daatumid.append(Paragraph(f'Ehitatud/avatud: {dob_string}'))
        # surmaandmed
        doe_string = ''
        if obj.hist_enddate:
            doe_string = obj.hist_enddate.strftime(settings.DATE_INPUT_FORMATS[0])
        elif obj.hist_endyear:
            doe_string = str(obj.hist_endyear)
        if doe_string:
            daatumid.append(Paragraph(f'Likvideeritud: {doe_string}'))

        profiilipilt = story_seotud_pildid(obj)
        if profiilipilt:
            data = [[profiilipilt, daatumid]]
            t = Table(data, hAlign='LEFT')
            t.setStyle(
                TableStyle(
                    [
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]
                )
            )
            story.append(t)
        story.append(Paragraph(f'{obj.kirjeldus}', P))

        story = story_seotud_viited(story, obj)
        story, _ = story_seotud_objectid(
            story, obj,
            seotud_model=Objekt,
            seotud_objectid_index=''
        )
    print('Kohti:', objs.count())
    return story

def backup2pdf_job(objects=10, content='lood', algus_aasta=0, l6pp_aasta=1899):
    dump_date = datetime.now().strftime(settings.DATE_INPUT_FORMATS[0])

    sisupealkiri = ''
    if content and content=='lood':
        if algus_aasta == 0:
            sisupealkiri = f'lood kuni {l6pp_aasta}'
        else:
            sisupealkiri = f'lood {algus_aasta}-{l6pp_aasta}'
    else:
        sisupealkiri = 'lisad'
    doc = MyDocTemplate(f'valgalinn.ee_{sisupealkiri.replace(" ","_")}_{dump_date}.pdf')

    print(sisupealkiri, datetime.now().strftime(settings.DATE_INPUT_FORMATS[0]))

    # normal frame as for SimpleFlowDocument
    frameT = Frame(LEFT_MARGIN, BOTTOM_MARGIN, FRAME_WIDTH, FRAME_HEIGHT, id='normal')
    # Two Columns
    frame1 = Frame(LEFT_MARGIN, BOTTOM_MARGIN, FRAME_WIDTH / 2 - 6, FRAME_HEIGHT, id='col1')
    frame2 = Frame(LEFT_MARGIN + FRAME_WIDTH / 2 + 6, BOTTOM_MARGIN, FRAME_WIDTH / 2 - 6, FRAME_HEIGHT, id='col2')

    def headerfooter(canvas, doc):
        canvas.saveState()

        # üla- ja alaäärised
        canvas.line(LEFT_MARGIN, TOP_MARGIN + 6, RIGHT_MARGIN, TOP_MARGIN + 6)
        canvas.line(LEFT_MARGIN, BOTTOM_MARGIN - 6, RIGHT_MARGIN, BOTTOM_MARGIN - 6)

        canvas.setFillColor(TEXT_ARTIKKEL_COLOR)
        canvas.setStrokeColor(TEXT_ARTIKKEL_COLOR)

        # header
        canvas.drawCentredString(
            0.5 * A4[0],
            A4[1] - 0.5 * inch,
            f'valgalinn.ee {sisupealkiri}',
        )
        # footer
        canvas.drawCentredString(
            0.5 * A4[0],
            0.5 * inch,
            f'{canvas.getPageNumber()}'
        )

        canvas.restoreState()

    def progress(canvas, doc):
        if doc.page % 100 == 0:
            print(doc.page, end=' ')

    # Build story.
    story = []

    # tiitelleht
    story.append(Spacer(inch, 2 * inch))
    story.append(Image(MEDIA_DIR.parent / 'wiki/static/wiki/img/android-chrome-192x192.png'))
    story.append(Spacer(inch, 1 * inch))
    story.append(Paragraph(f'valgalinn.ee väljatrükk - {sisupealkiri}', T))
    story.append(Spacer(inch, 3 * inch))
    story.append(Paragraph(f'Valga {dump_date}', P))

    #sisukord
    story.append(PageBreak())
    story.append(Paragraph('Sisukord', H2))
    toc = TableOfContents()
    toc.levelStyles = [TOC1, TOC2, TOC3]
    story.append(toc)

    if content and content == 'lood':
        # lood
        story.append(PageBreak())
        story.append(Paragraph(f'<font color="{TEXT_ARTIKKEL_COLOR}">Lood</font>', C))
        story.append(NextPageTemplate('OneColPageNr'))
        story.append(PageBreak())
        story = story_artiklid(story, objects=objects, algus_aasta=algus_aasta, l6pp_aasta=l6pp_aasta)
    else:
        # isikud
        story.append(NextPageTemplate('OneCol'))
        story.append(PageBreak())
        story.append(Paragraph(f'<font color="{TEXT_ISIK_COLOR}">Isikud</font>', C))
        story.append(NextPageTemplate('OneColPageNr'))
        story.append(PageBreak())
        story = story_isikud(story, objects=objects)
        # asutised
        story.append(NextPageTemplate('OneCol'))
        story.append(PageBreak())
        story.append(Paragraph(f'<font color="{TEXT_ORGANISATSIOON_COLOR}">Asutised</font>', C))
        story.append(NextPageTemplate('OneColPageNr'))
        story.append(PageBreak())
        story = story_organisatsioonid(story, objects=objects)
        # kohad
        story.append(NextPageTemplate('OneCol'))
        story.append(PageBreak())
        story.append(Paragraph(f'<font color="{TEXT_OBJEKT_COLOR}">Kohad</font>', C))
        story.append(NextPageTemplate('OneColPageNr'))
        story.append(PageBreak())
        story = story_objektid(story, objects=objects)

    # nimeregistrid
    story.append(NextPageTemplate('OneCol'))
    story.append(PageBreak())
    story.append(Paragraph('Registrid', C))
    story.append(NextPageTemplate('TwoCol'))

    story.append(PageBreak())
    story.append(Paragraph('Isikute register', H2))
    index_isikud = SimpleIndex(
        name='isikud',
        dot=' . ',
        headers=True
    )
    story.append(index_isikud)
    story.append(PageBreak())

    story.append(Paragraph('Asutiste register', H2))
    index_organisatsioonid = SimpleIndex(
        name='organisatsioonid',
        dot=' . ',
        headers=True
    )
    story.append(index_organisatsioonid)
    story.append(PageBreak())

    story.append(Paragraph('Kohtade register', H2))
    index_objektid = SimpleIndex(
        name='objektid',
        dot=' . ',
        headers=True
    )
    story.append(index_objektid)

    doc.addPageTemplates(
        [
            PageTemplate(id='OneCol', frames=frameT),
            PageTemplate(id='OneColPageNr', frames=frameT, onPage=headerfooter, onPageEnd=progress),
            PageTemplate(id='TwoCol', frames=[frame1, frame2]),
        ]
    )

    print('Alustame genereerimist...', end=' ')
    doc.multiBuild(
        story,
        canvasmaker=myCanvasMaker(
            indeces=[
                index_isikud,
                index_organisatsioonid,
                index_objektid
            ],
            # canvasmaker=MyCanvas
        ),
    )
    print('valmis!')

def backup2pdf(objects=10):
    backup2pdf_job(objects=objects, content='lood', algus_aasta=0, l6pp_aasta=1899)
    backup2pdf_job(objects=objects, content='lood', algus_aasta=1900, l6pp_aasta=1919)
    backup2pdf_job(objects=objects, content='lood', algus_aasta=1920, l6pp_aasta=1930)
    backup2pdf_job(objects=objects, content='lisad')

if __name__ == "__main__":
    # backup2pdf(objects=10) # objects=0 = täiskoopia
    pass
