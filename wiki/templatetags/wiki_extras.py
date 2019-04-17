from django import template
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
