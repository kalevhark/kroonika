from datetime import date, timedelta

from django import template
from django.conf import settings

from wiki.models import VIGA_TEKSTIS, Artikkel, Isik, Organisatsioon, Objekt
from wiki.views import get_all_logged_in_users, artikkel_qs_userfilter

register = template.Library()

@register.inclusion_tag('wiki/includes/logged_in_user_list.html', takes_context=True)
def render_logged_in_user_list(context):
    return {
        'user': context['user'],
        'users': get_all_logged_in_users()
    }

# Tagastab konkreetsele kasutajale filtreeritud loetelu objectiga (Isik, Organisatsioon, Objekt) seotud artiklitega
@register.inclusion_tag('wiki/includes/object_mainitud_artiklites.html', takes_context=True)
def object_mainitud_artiklites(context, object, model):
    # Filtreerime kasutajatüübi järgi
    artikkel_qs = artikkel_qs_userfilter(context['user'])
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


@register.filter
def ukj(date_vkj):
    if date(1918, 1, 31) >= date_vkj >= date(1582, 10, 5):
        nihe = 0
        if date(1918, 1, 31) >= date_vkj > date(1900, 2, 28):
            nihe = 13
        if date(1900, 2, 28) >= date_vkj > date(1800, 2, 28):
            nihe = 12
        if date(1800, 2, 28) >= date_vkj > date(1700, 2, 28):
            nihe = 11
        if date(1800, 2, 28) >= date_vkj >= date(1582, 10, 5):
            nihe = 10
        date_ukj = date_vkj + timedelta(days=nihe)
        return f'(ukj: {date_ukj:%d.%m.%Y})'
    else:
        return ''

@register.simple_tag
def kalev():
    return 'Kalev Härk'

# Vigast kohta tähistav sümbol
@register.simple_tag
def viga_tekstis():
    return VIGA_TEKSTIS

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
def recaptcha_public_key():
    return settings.GOOGLE_RECAPTCHA_PUBLIC_KEY


