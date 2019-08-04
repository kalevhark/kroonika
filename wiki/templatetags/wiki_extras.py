from django import template

from wiki.models import VIGA_TEKSTIS
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

# Sektsioonide nimetused
@register.simple_tag
def model_name():
    model_names = dict()
    model_names['artikkel'] = 'Lood'
    model_names['isik'] = 'Isikud'
    model_names['organisatsioon'] = 'Asutised'
    model_names['objekt'] = 'Kohad'
    return model_names

