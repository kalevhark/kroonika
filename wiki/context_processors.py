from django.conf import settings

from wiki.forms import VihjeForm

# Lisab contexti vihjevormi
def add_vihjevorm(request):
    return {
        'feedbackform': VihjeForm()
    }

# Lisab contexti m2rke, kas cookie consent FF on sisse lülitatud
def get_cookie_consent_inuse(request):
    return {
        'COOKIE_CONSENT_INUSE': settings.COOKIE_CONSENT_INUSE,
    }
