#!/home/ec2-user/django/kroonika_env/bin/python3

#
# Salvestatud kaardivaadete regulaarseks uuendamiseks
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-wiki-app/tasks.py

from pathlib import Path

if __name__ == "__main__":
    import os
    import django
    from django.test.utils import setup_test_environment

    os.environ['DJANGO_SETTINGS_MODULE'] = 'kroonika.settings'
    django.setup()
    setup_test_environment()
    from django.conf import settings
    UTIL_DIR = Path(__file__).resolve().parent  / 'utils'
    # Build paths inside the project like this: UTIL_DIR / 'subdir'.
    # print('Töökataloog:', UTIL_DIR)
else:
    from django.conf import settings
    UTIL_DIR = settings.BASE_DIR / 'wiki' / 'utils'

try:
    from wiki.utils import shp_util
except: # kui käivitatakse lokaalselt
    from utils import shp_util

if __name__ == '__main__':
    path = UTIL_DIR / 'geojson' / "big_maps_default.pickle"
    if path.is_file():
        os.remove(path)
    shp_util.make_big_maps_leaflet(aasta=None, objekt=None)