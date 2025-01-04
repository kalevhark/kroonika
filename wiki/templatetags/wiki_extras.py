from datetime import date, timedelta
import uuid

from django import template
from django.conf import settings

from wiki.models import VIGA_TEKSTIS, Artikkel, Isik, Organisatsioon, Objekt, Kaart, Kaardiobjekt
from wiki.views import get_all_logged_in_users #, artikkel_qs_userfilter

register = template.Library()

ICONS = {
    'artikkel': 'fa fa-comment',
    'isik': 'fa fa-address-card-o',
    'organisatsioon': 'fa fa-group',
    'objekt': 'fa fa-map-marker',
    'kaart': 'fa fa-map',
    'kaardiobjekt': 'fa fa-map',
    'pilt': 'fa fa-camera-retro',
    'viide': 'fa fa-binoculars'
}

@register.inclusion_tag('wiki/includes/logged_in_user_list.html', takes_context=True)
def render_logged_in_user_list(context):
    return {
        'user': context['user'],
        'users': get_all_logged_in_users()
    }

# 'Artikkel', 'Isik', 'Organisatsioon', 'Objekt', ...
@register.filter
def get_model_name(object):
    # name = str(value.__class__.__name__)
    # return name
    return object.__class__.__name__

# 'artikkel', 'isik', 'organisatsioon', 'objekt', ...
@register.filter
def to_model_name_lower(object):
    return object.__class__.__name__.lower()

# Tagastab konkreetsele kasutajale filtreeritud loetelu objectiga (Isik, Organisatsioon, Objekt) seotud artiklitega
@register.inclusion_tag('wiki/includes/object_mainitud_artiklites.html', takes_context=True)
def object_mainitud_artiklites(context, object, model):
    # Filtreerime kasutajatüübi järgi
    # artikkel_qs = artikkel_qs_userfilter(context['user'])
    artikkel_qs = Artikkel.objects.daatumitega(context['request'])
    if model == 'isik':
        artikkel_qs = artikkel_qs.filter(isikud__in=[object])
    elif model == 'organisatsioon':
        artikkel_qs = artikkel_qs.filter(organisatsioonid__in=[object])
    elif model == 'objekt':
        artikkel_qs = artikkel_qs.filter(objektid__in=[object])
    return {
        # 'user': context['user'],
        'artikkel_qs': artikkel_qs
    }

# Tagastab konkreetsele kasutajale filtreeritud loetelu objectiga (Isik, Organisatsioon, Objekt) seotud artiklitega
@register.inclusion_tag('wiki/includes/object_mainitud_artiklites2.html', takes_context=True)
def object_mainitud_artiklites2(context, object, model):
    # Filtreerime kasutajatüübi järgi
    artikkel_qs = Artikkel.objects.daatumitega(context['request'])
    if model == 'isik':
        artikkel_qs = artikkel_qs.filter(isikud=object)
    elif model == 'organisatsioon':
        artikkel_qs = artikkel_qs.filter(organisatsioonid=object)
    elif model == 'objekt':
        artikkel_qs = artikkel_qs.filter(objektid=object)

    return {
        # 'user': context['user'],
        'artiklid': artikkel_qs.values_list('id', 'slug', 'hist_year', flat=False, named=True)
    }


@register.filter
def ukj(date_vkj):
    try:
        date2compare = date(date_vkj.year, date_vkj.month, date_vkj.day) # et tekiks kindlasti date() tyyp
    except:
        return date_vkj
    nihe = 0
    if date(1918, 1, 31) >= date2compare >= date(1582, 10, 5):
        if date(1918, 1, 31) >= date2compare > date(1900, 2, 28):
            nihe = 13
        if date(1900, 2, 28) >= date2compare > date(1800, 2, 28):
            nihe = 12
        if date(1800, 2, 28) >= date2compare > date(1700, 2, 28):
            nihe = 11
        if date(1700, 2, 28) >= date2compare >= date(1582, 10, 5):
            nihe = 10
    return date_vkj + timedelta(days=nihe)

# Kas tegemist on vana kalendri kuup2evaga?
@register.filter
def vkj(date):
    return date != ukj(date)

# Mis tüüpi server DEV, TEST või Live
@register.simple_tag
def server_type():
    return settings.SERVER_TYPE

# ikoonid andmebaasidele Artikkel, Isik, Organisatsioon, Objekt
@register.simple_tag
def icon_artikkel():
    return 'fa fa-comment'

@register.simple_tag
def icon_isik():
    return 'fa fa-address-card-o'

@register.simple_tag
def icon_organisatsioon():
    return 'fa fa-group'

@register.simple_tag
def icon_objekt():
    return 'fa fa-map-marker'
    # return 'fa fa-bank'

@register.simple_tag
def icon_kaart():
    return 'fa fa-map'

@register.simple_tag
def icon_kaardiobjekt():
    return 'fa fa-map'

@register.simple_tag
def icon_pilt():
    return 'fa fa-camera-retro'

@register.simple_tag
def icon_viide():
    return 'fa fa-binoculars'

# kasutamine {% icon_object object %}
@register.simple_tag
def icon_object(object=None):
    if object:
        return ICONS[object.__class__.__name__.lower()]

@register.simple_tag
def kalev():
    return 'Kalev Härk'

# Vigast kohta tähistav sümbol
@register.simple_tag
def viga_tekstis():
    return VIGA_TEKSTIS

# Vaikimisi märksõnad
@register.simple_tag
def keywords():
    return ','.join(settings.KROONIKA['KEYWORDS'])

@register.simple_tag
def description():
    return settings.KROONIKA['DESCRIPTION']

# Sektsioonide nimetused
@register.simple_tag
def model_name_artikkel():
    return Artikkel._meta.verbose_name_plural

@register.simple_tag
def model_name_isik():
    return Isik._meta.verbose_name_plural

@register.simple_tag
def model_name_organisatsioon():
    return Organisatsioon._meta.verbose_name_plural

@register.simple_tag
def model_name_objekt():
    return Objekt._meta.verbose_name_plural

@register.simple_tag
def model_name_kaart():
    return Kaart._meta.verbose_name_plural

@register.simple_tag
def model_name_kaardiobjekt():
    return Kaardiobjekt._meta.verbose_name_plural

@register.simple_tag
def recaptcha_public_key():
    return settings.GOOGLE_RECAPTCHA_PUBLIC_KEY

@register.simple_tag
def get_verbose_name(object):
    return object._meta.verbose_name.lower()

@register.simple_tag
def get_verbose_name_plural(object):
    return object._meta.verbose_name_plural.lower()

@register.filter
def duration(td):
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    remaining_hours = total_seconds % 86400
    remaining_minutes = remaining_hours % 3600
    hours = remaining_hours // 3600
    minutes = remaining_minutes // 60
    seconds = remaining_minutes % 60
    # microseconds = td.microseconds

    days_str = f'{days}d ' if days else ''
    hours_str = f'{hours}:' if hours else ''
    minutes_str = f'{minutes}:' if minutes else ''
    seconds_str = f'{seconds}' if seconds and not hours_str else '0'

    return f'{days_str}{hours_str}{minutes_str}{seconds_str},{td.microseconds}'

@register.simple_tag
def get_uuid():
    return uuid.uuid4()
