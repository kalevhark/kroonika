from datetime import datetime, timezone
import time

from django import template
from django.conf import settings

register = template.Library()

@register.filter
def timestamp_to_time(timestamp):
    return datetime.fromtimestamp(int(timestamp), timezone.utc)
