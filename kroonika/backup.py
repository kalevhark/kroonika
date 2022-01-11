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

from django.core import serializers

from wiki.models import (
    Artikkel, Isik, Organisatsioon, Objekt, Pilt,
    Kaardiobjekt,
    Viide, Allikas
)


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
    # backup2serverless(objects=3) # objects=0 = täiskoopia
    pass

# Andmete varundamiseks offline kasutuseks
# Loob valgalinn.ee ajalookroonika koopia json ja xml formaatides

from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.platypus import PageBreak
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.tableofcontents import TableOfContents, SimpleIndex
from reportlab.platypus.frames import Frame
from reportlab.lib.units import cm, inch, mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from wiki.models import KUUD

PAGE_WIDTH, PAGE_HEIGHT = A4
styles = getSampleStyleSheet()

# Custom Canvas class for automatically adding page-numbers
# class MyCanvas(canvas.Canvas):
#     def __init__(self, *args, **kwargs):
#         canvas.Canvas.__init__(self, *args, **kwargs)
#         self.pages = []
#
#     def showPage(self):
#         self.pages.append(dict(self.__dict__))
#         self._startPage()
#
#     def draw_page_frame(self):
#         top_margin = A4[1] - inch
#         bottom_margin = inch
#         left_margin = inch
#         right_margin = A4[0] - inch
#         frame_width = right_margin - left_margin
#
#         self.line(left_margin, top_margin + 2, right_margin, top_margin + 2)
#         self.drawString(left_margin, top_margin + 4, 'valgalinn.ee')
#         self.line(left_margin, bottom_margin, right_margin, bottom_margin)
#
#     def draw_page_number(self, page_count):
#         # Modify the content and styles according to the requirement
#         page = "{curr_page} of {total_pages}".format(curr_page=self._pageNumber, total_pages=page_count)
#         self.setFont("Helvetica", 10)
#         # self.drawRightString(195*mm, 272*mm, page)
#         self.drawCentredString(0.5*A4[0], 0.5 * inch, "%d" % self.getPageNumber())
#
#     def save(self):
#         # Modify the save() function to add page-number before saving every page
#         page_count = len(self.pages)
#         for page in self.pages:
#             self.__dict__.update(page)
#             self.draw_page_frame()
#             self.draw_page_number(page_count)
#             canvas.Canvas.showPage(self)
#         canvas.Canvas.save(self)

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
        BaseDocTemplate.__init__(self, filename, **kw)
        template = PageTemplate('normal', [Frame(2.5*cm, 2.5*cm, 15*cm, 25*cm, id='F1')])
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        "Registers TOC entries."
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                self.notify('TOCEntry', (0, text, self.page))
            if style == 'Heading2':
                self.notify('TOCEntry', (1, text, self.page))
            if style == 'Heading3':
                self.notify('TOCEntry', (2, text, self.page))

def story_artiklid(story, h1, h2, h3, p, v, objects=3):
    objs = Artikkel.objects.daatumitega(request=None)
    if objects > 0:
        objs = objs[:objects]
    jooksev_aasta = 0
    for obj in objs:
        if obj.hist_year != jooksev_aasta:
            jooksev_aasta = obj.hist_year
            story.append(Paragraph(f'{obj.hist_year}', h2))
        jooksev_kuu = 0
        if obj.hist_date:
            hist_date = obj.hist_date.strftime('<strong>%d.%m.%Y</strong> ')
            kuu = obj.hist_date.month
        else:
            hist_date = ''
            if obj.hist_month:
                kuu = obj.hist_month
            else:
                kuu = 0
        if kuu and kuu != jooksev_kuu:
            jooksev_kuu = kuu
            story.append(Paragraph(f'{KUUD[jooksev_kuu-1][1]}', h3))

        isikud = obj.isikud.all()
        isik_index = ''
        if isikud:
            for isik in isikud:
                isik_clean = repr(isik).replace(',', ',,') # topeltkoma = ','
                # story.append(Paragraph(f'<index name="isikud" item="{isik_clean}" />', v))
                isik_index += f'<index name="isikud" item="{isik_clean}" />'

        organisatsioonid = obj.organisatsioonid.all()
        organisatsioon_index = ''
        if organisatsioonid:
            for organisatsioon in organisatsioonid:
                organisatsioon_clean = str(organisatsioon).replace(',', ',,').replace('"', '&quot') # topeltkoma = ','
                # story.append(Paragraph(f'<index name="organisatsioonid" item="{organisatsioon_clean}" />', v))
                organisatsioon_index += f'<index name="organisatsioonid" item="{organisatsioon_clean}" />'

        objektid = obj.objektid.all()
        objekt_index = ''
        if objektid:
            for objekt in objektid:
                objekt_clean = str(objekt).replace(',', ',,') # topeltkoma = ','
                # story.append(Paragraph(f'<index name="objektid" item="{objekt_clean}" />', v))
                objekt_index += f'<index name="objektid" item="{objekt_clean}" />'

        story.append(Paragraph(f'{hist_date}{obj.body_text}{isik_index}{organisatsioon_index}{objekt_index}', p))

        viited = obj.viited.all()
        if viited:
            for viide in viited:
                story.append(Paragraph(f'{viide}', v))
    return story

def story_isikud(story, h1, h2, h3, p, v, objects=3):
    objs = Isik.objects.daatumitega(request=None)
    if objects > 0:
        objs = objs[:objects]
    jooksev_t2ht = ''
    for obj in objs:
        if obj.perenimi[0].upper() != jooksev_t2ht:
            jooksev_t2ht = obj.perenimi[0].upper()
            story.append(Paragraph(f'{obj.perenimi[0].upper()}', h2))

        isik_index = repr(obj).replace(',', ',,')  # topeltkoma = ','
        story.append(Paragraph(f'<index name="isikud" item="{isik_index}" /><strong>{obj}</strong>', p))
        story.append(Paragraph(f'{obj.kirjeldus}', p))

        viited =  obj.viited.all()
        if viited:
            for viide in viited:
                story.append(Paragraph(f'{viide}', v))

        organisatsioonid = obj.organisatsioonid.all()
        if organisatsioonid:
            for organisatsioon in organisatsioonid:
                organisatsioon_index = str(organisatsioon).replace(',', ',,').replace('"', '&quot') # topeltkoma = ','
                story.append(Paragraph(f'<index name="organisatsioonid" item="{organisatsioon_index}" />{organisatsioon}', p))

        objektid = obj.objektid.all()
        if objektid:
            for objekt in objektid:
                objekt_index = str(objekt).replace(',', ',,') # topeltkoma = ','
                story.append(Paragraph(f'<index name="objektid" item="{objekt_index}" />{objekt}', v))
    return story

from reportlab.platypus import BaseDocTemplate, Frame, Paragraph, NextPageTemplate, PageBreak, PageTemplate
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet

def backup2pdf(objects=3):
    # styles = getSampleStyleSheet()

    h1 = PS(
        name='Heading1',
        fontSize=14,
        leading=16,
        spaceAfter=6,
        spaceBefore=6,
        keepWithNext=1
    )
    toc1 = PS(
        name='TOC1',
        fontSize=14,
        leading=16,
        spaceAfter=6,
        spaceBefore=6,
        keepWithNext=1
    )
    h2 = PS(
        name='Heading2',
        fontSize=14,
        leading=16,
        spaceAfter=6,
        spaceBefore=6,
        keepWithNext=1
    )
    toc2 = PS(
        name='TOC2',
        fontSize=14,
        leading=16,
        spaceAfter=6,
        spaceBefore=6,
        keepWithNext=1
    )

    h3 = PS(
        name='Heading3',
        fontSize=12,
        leading=14,
        # leftIndent=2*cm,
        spaceAfter=6,
        spaceBefore=6,
        keepWithNext=1
    )
    toc3 = PS(
        name='TOC3',
        fontSize=12,
        leading=14,
        leftIndent=2 * cm,
        spaceAfter=6,
        spaceBefore=6
    )
    p = PS(
        name='kirjeldus',
        fontSize=10,
        spaceAfter=6
    )
    v = PS(
        name='viide',
        fontSize=8
    )

    doc = MyDocTemplate('mintoc.pdf')

    # normal frame as for SimpleFlowDocument
    frameT = Frame(inch, inch, 6 * inch, 9 * inch, id='normal')

    # Two Columns
    frame1 = Frame(inch, inch, 6 * inch / 2 - 6, 9 * inch, id='col1')
    frame2 = Frame(inch + 6 * inch / 2 + 6, inch, 6 * inch / 2 - 6, 9 * inch, id='col2')

    def headerfooter(canvas, doc):
        canvas.saveState()

        top_margin = A4[1] - inch
        bottom_margin = inch
        left_margin = inch
        right_margin = A4[0] - inch
        frame_width = right_margin - left_margin

        canvas.line(left_margin, top_margin + 2, right_margin, top_margin + 2)
        # canvas.drawString(left_margin, top_margin + 4, 'valgalinn.ee')
        canvas.drawCentredString(0.5 * A4[0], A4[1] - 0.5 * inch, 'valgalinn.ee')

        canvas.line(left_margin, bottom_margin, right_margin, bottom_margin)
        canvas.drawCentredString(0.5 * A4[0], 0.5 * inch, "%d" % canvas.getPageNumber())

        canvas.restoreState()

    # Build story.
    story = []
    toc = TableOfContents()
    toc.levelStyles = [toc1, toc2, toc3]

    story.append(Paragraph('Tiitelleht', h1))

    story.append(PageBreak())
    story.append(Paragraph('Sisukord', h2))
    story.append(toc)

    story.append(PageBreak())
    story.append(Paragraph('Lood', h1))
    story.append(NextPageTemplate('OneColPageNr'))
    story.append(PageBreak())
    story = story_artiklid(story, h1, h2, h3, p, v, objects=objects)

    story.append(NextPageTemplate('OneCol'))
    story.append(PageBreak())
    story.append(Paragraph('Isikud', h1))
    story.append(NextPageTemplate('OneColPageNr'))
    story.append(PageBreak())
    story = story_isikud(story, h1, h2, h3, p, v, objects=objects)

    story.append(NextPageTemplate('OneCol'))
    story.append(PageBreak())
    story.append(Paragraph('Registrid', h1))
    story.append(NextPageTemplate('TwoCol'))
    story.append(PageBreak())
    story.append(Paragraph('Isikute register', h2))
    index_isikud = SimpleIndex(
        name='isikud',
        dot=' . ',
        headers=True
    )
    story.append(index_isikud)
    story.append(PageBreak())

    story.append(Paragraph('Asutiste register', h2))
    index_organisatsioonid = SimpleIndex(
        name='organisatsioonid',
        dot=' . ',
        headers=True
    )
    story.append(index_organisatsioonid)
    story.append(PageBreak())

    story.append(Paragraph('Kohtade register', h2))
    index_objektid = SimpleIndex(
        name='objektid',
        dot=' . ',
        headers=True
    )
    story.append(index_objektid)

    doc.addPageTemplates(
        [
            PageTemplate(id='OneCol', frames=frameT),
            PageTemplate(id='OneColPageNr', frames=frameT, onPage=headerfooter),
            PageTemplate(id='TwoCol', frames=[frame1, frame2]),
        ]
    )

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


if __name__ == "__main__":
    backup2pdf(objects=100) # objects=0 = täiskoopia
    pass
