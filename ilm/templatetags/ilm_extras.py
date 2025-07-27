from datetime import datetime, timezone
import time

from django import template
from django.conf import settings

register = template.Library()

KUUD = [
    '', # Tühi selleks et kuunumber=indeks
    'jaanuar',
    'veebruar',
    'märts',
    'aprill',
    'mai',
    'juuni',
    'juuli',
    'august',
    'september',
    'oktoober',
    'november',
    'detsember'
]

@register.filter
def timestamp_to_time(timestamp):
    return datetime.fromtimestamp(int(timestamp), timezone.utc)

@register.filter
def integer_to_monthname(kuunumber):
    return KUUD[kuunumber]
