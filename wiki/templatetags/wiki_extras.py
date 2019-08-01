from django import template
from django.conf import settings
from django.db.models import Max, Min

from wiki.models import Artikkel, VIGA_TEKSTIS
from wiki.views import get_all_logged_in_users


register = template.Library()

@register.inclusion_tag('wiki/includes/logged_in_user_list.html', takes_context=True)
def render_logged_in_user_list(context):
    return {
        'user': context['user'],
        'users': get_all_logged_in_users()
    }

@register.simple_tag
def kalev():
    return 'Kalev Härk'

# Vigast kohta tähistav sümbol
@register.simple_tag
def viga_tekstis():
    return VIGA_TEKSTIS

# Andmebaasi perioodi valik
@register.simple_tag
def periood():
    min_year, max_year = Artikkel.objects.aggregate(Min('hist_year'), Max('hist_year')).values()
    return ' kõik'
