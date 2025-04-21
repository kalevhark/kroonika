# Python-Markdown Custom Extensions
# ===============================

"""
preporcessor AddEscapeBetweenNumberAndDot: Lisab numbri ja punkti vahele backslashi
blockprocessor WikiObjectLinkProcessor: Loob markdown lingid wiki objectidele
blockprocessor WikiPiltProcessor: Teeb tekstisisesed pildid markdown jaoks sobivaks
"""

from __future__ import annotations
import re
import xml.etree.ElementTree as etree

from django.apps import apps
from django.conf import settings

from markdown import Extension
from markdown.preprocessors import Preprocessor
from markdown.blockprocessors import BlockProcessor

from wiki.models import Pilt

PATTERN_OBJECTS = settings.KROONIKA['PATTERN_OBJECTS']

## preprocessors

# Lisab numbri ja punkti vahele backslashi
# Vajalik AddEscapeBetweenNumberAndDot jaoks
def add_escape_between_number_and_dot(matchobj):
    leiti = matchobj.group(0)
    return "\\".join([leiti[:-1], "."])

class AddEscapeBetweenNumberAndDot(Preprocessor):
    """ Otsime kas rea alguses on arv ja punkt """
    def run(self, lines):
        new_lines = []
        for line in lines:
            line_modified = re.sub(r"(\A)(\d+)*\.", add_escape_between_number_and_dot, line)
            new_lines.append(line_modified)
        return new_lines


# blockprocessors

class WikiObjectLinkProcessor(BlockProcessor):
    """ Process link references. """
    """ 'PATTERN_OBJECTS': r'\[([\wÀ-ÿ\s\"\-\,\.\(\)]+)\]\(\[(artikkel|isik|organisatsioon|objekt)_([0-9]*)\]\)' """
    RE = re.compile(
        PATTERN_OBJECTS, 
        re.MULTILINE
    )

    def test(self, parent: etree.Element, block: str) -> bool:
        return bool(self.RE.search(block))

    def run(self, parent: etree.Element, blocks: list[str]) -> bool:
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            tekst, model_name, id = m.groups()
            pos = m.span()[0]
            model = apps.get_model('wiki', model_name)
            obj = model.objects.get(id=id)
            url = obj.get_absolute_url()
            data_attrs = f'data-model="{model_name}" data-id="{obj.id}"'
            span = f'<span id="{model_name}_{obj.id}_pos{pos}" title="{obj}" {data_attrs}>{tekst}</span>'
            html = f'<a class="text-{model_name} hover-{model_name} tooltip-content" href="{url}">{span}</a>'
            blocks.insert(0, block[:m.start()] + html + block[m.end():])
            return True
        # No match. Restore block.
        blocks.insert(0, block)
        return False


class WikiPiltProcessor(BlockProcessor):
    """ Process link references. """
    """ PATTERN: r'\[pilt_([0-9]*)]' """
    PATTERN = r'\[pilt_([0-9]*)]'
    RE = re.compile(PATTERN)

    def test(self, parent: etree.Element, block: str) -> bool:
        return bool(self.RE.search(block))

    def run(self, parent: etree.Element, blocks: list[str]) -> bool:
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            id = m.groups()[0]
            pilt = Pilt.objects.get(id=id)
            if pilt:
                pildi_url = pilt.pilt.url
                pildi_caption = pilt.caption()
                img = f'<img src="{pildi_url}" class="pilt-pildidtekstis" alt="{pildi_caption}" data-pilt-id="{pilt.id}" >'
                caption = f'<p><small>{pildi_caption}</small></p>'
                html = f'<div class="w3-row">{img}{caption}</div>'
            if block[m.end():].strip():
                # Add any content after match back to blocks as separate block
                blocks.insert(0, block[m.end():].lstrip('\n'))
            blocks.insert(0, html)
            if block[:m.start()].strip():
                # Add any content before match back to blocks as separate block
                blocks.insert(0, block[:m.start()].rstrip('\n'))
            return True
        # No match. Restore block.
        blocks.insert(0, block)
        return False
    

class ExtraExtension(Extension):
    """ Add various extensions to Markdown class."""

    def extendMarkdown(self, md):
        """ Register extension instances. """
        md.preprocessors.register(AddEscapeBetweenNumberAndDot(md), 'addescapebetweennumberanddot', 20)
        md.parser.blockprocessors.register(WikiObjectLinkProcessor(md.parser), 'wikiobjectlinkprocessor', 15)
        md.parser.blockprocessors.register(WikiPiltProcessor(md.parser), 'wikipiltprocessor', 25)

        
def makeExtension(**kwargs):  # pragma: no cover
    return ExtraExtension(**kwargs)