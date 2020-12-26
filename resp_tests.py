from datetime import datetime
from functools import reduce
import logging
from operator import or_
import os

import django
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import reverse

os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
django.setup()
setup_test_environment()

from wiki.models import Artikkel, Isik, Organisatsioon, Objekt

# create an instance of the client for our use
client = Client()

def check_urls():
    urls = [
        '/',
        # '/wiki/kroonika/1922/',
        # '/wiki/kroonika/1922/4/',
        # '/wiki/kroonika/1922/4/20/',
    ]

    for url in urls:
        time_start = datetime.now()
        response = client.get(url)
        time_stopp = datetime.now() - time_start
        logging.info(f'{url}, {response.status_code}, {time_stopp.seconds},{time_stopp.microseconds}s')

def check_names():
    pages = [
        'algus',
        'wiki:info',
        'wiki:otsi',
        'ilm:index',
        'ilm:history',
        'ilm:mixed_ilmateade',
        'blog:blog_index',
        'vgvk:vgvk_index'
    ]

    for page in pages:
        time_start = datetime.now()
        response = client.get(reverse(page))
        time_stopp = datetime.now() - time_start
        logging.info(f'{page} {response.status_code} {time_stopp.seconds},{time_stopp.microseconds}s')
        # print(response.context.keys())

def check_public_artikkel():
    print('Kontrollime avalikult nähtavaid artikleid:')
    objs = Artikkel.objects.filter(kroonika__isnull=True)
    OK = objs.count()
    NOK = 0
    for obj in objs:
        url = f'/wiki/{obj.id}-{obj.slug}/'
        time_start = datetime.now()
        response = client.get(url)
        time_stopp = datetime.now() - time_start
        if response.status_code != 200 or time_stopp.seconds > 1:
            NOK += 1
            logging.warning(f'{url} {response.status_code} {time_stopp.seconds},{time_stopp.microseconds}s')
    logging.info(f'Avalikud ariklid NOK: {NOK}/{OK}')

def check_nonpublic_artikkel():
    print('Kontrollime avalikult mittenähtavaid artikleid:')
    objs = Artikkel.objects.filter(kroonika__isnull=False)
    ALL = objs.count()
    NOK = 0
    for obj in objs:
        url = f'/wiki/{obj.id}-{obj.slug}/'
        response = client.get(url)
        if response.status_code != 404:
            NOK += 1
            logging.warning(f'{url} {response.status_code}')
    logging.info(f'Mitteavalikud ariklid NOK: {NOK}/{ALL}')

def check_public_object(model):
    print(f'Kontrollime avalikult nähtavad {model._meta.verbose_name_plural}:')
    # Anonymous user filter
    artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
    initial_queryset = model.objects.all()
    artikliga = initial_queryset. \
        filter(artikkel__in=artikkel_qs). \
        values_list('id', flat=True)
    viitega = initial_queryset. \
        filter(viited__isnull=False). \
        values_list('id', flat=True)
    viiteta_artiklita = initial_queryset. \
        filter(viited__isnull=True, artikkel__isnull=True). \
        values_list('id', flat=True)
    model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])
    objs = initial_queryset.filter(id__in=model_ids)
    ALL = objs.count()
    NOK = 0
    for obj in objs:
        url = f'/wiki/{model._meta.model_name}/{obj.id}-{obj.slug}/'
        time_start = datetime.now()
        response = client.get(url)
        time_stopp = datetime.now() - time_start
        if response.status_code != 200 or time_stopp.seconds > 1:
            NOK += 1
            logging.warning(f'{url} {response.status_code} {time_stopp.seconds},{time_stopp.microseconds}s')
            # print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
    logging.info(f'Avalikud {model._meta.verbose_name_plural} NOK: {NOK}/{ALL}')

def check_nonpublic_object(model):
    print(f'Kontrollime avalikult mittenähtavad {model._meta.verbose_name_plural}')
    # Anonymous user filter
    artikkel_qs = Artikkel.objects.filter(kroonika__isnull=True)
    initial_queryset = model.objects.all()
    artikliga = initial_queryset. \
        filter(artikkel__in=artikkel_qs). \
        values_list('id', flat=True)
    viitega = initial_queryset. \
        filter(viited__isnull=False). \
        values_list('id', flat=True)
    viiteta_artiklita = initial_queryset. \
        filter(viited__isnull=True, artikkel__isnull=True). \
        values_list('id', flat=True)
    model_ids = reduce(or_, [artikliga, viitega, viiteta_artiklita])
    objs = initial_queryset.exclude(id__in=model_ids)
    ALL = objs.count()
    NOK = 0
    for obj in objs:
        url = f'/wiki/{model._meta.model_name}/{obj.id}-{obj.slug}/'
        time_start = datetime.now()
        response = client.get(url)
        time_stopp = datetime.now() - time_start
        if 'Lehekülge ei leitud' not in response.content.decode():
            NOK += 1
            # print(url, response.status_code, f'{time_stopp.seconds},{time_stopp.microseconds}s')
            logging.warning(f'{url} {response.status_code} {time_stopp.seconds},{time_stopp.microseconds}s')
    logging.info(f'Mitteavalikud {model._meta.verbose_name_plural} NOK: {NOK}/{ALL}')

if __name__ == '__main__':
    # logger = logging.getLogger('resp_tests')
    logging.basicConfig(
        filename='logs/resp_tests.log',
        encoding='utf-8',
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%d.%m.%Y %H:%M:%S'
    )
    logging.info('Test started')
    print('Kontrollime põhilinke:')
    check_urls()
    check_names()
    # check_public_artikkel()
    # check_nonpublic_artikkel()
    test_model = Objekt
    # check_public_object(test_model)
    check_nonpublic_object(test_model)
    logging.info('Test completed')