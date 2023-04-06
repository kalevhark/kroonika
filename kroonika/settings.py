"""
Django settings for kroonika project.

"""
import configparser
import os
from pathlib import Path

# Starting with 3.2 new projects are generated with DEFAULT_AUTO_FIELD set to BigAutoField
# To avoid unwanted migrations in the future, either explicitly set DEFAULT_AUTO_FIELD to AutoField
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

PROJECT_DIR = Path(__file__).resolve().parent
print('settings.PROJECT_DIR:', PROJECT_DIR)

# Access configparser to load variable values
config = configparser.SafeConfigParser(allow_no_value=True)
config.read('%s/settings.ini' % (PROJECT_DIR))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = PROJECT_DIR.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config['django']['SECRET_KEY']

DEBUG = config['django'].getboolean('DEBUG', fallback=False)

# DEV, TEST or Live server
SERVER_TYPE = config['django'].get('SERVER_TYPE', '')

ALLOWED_HOSTS = [
    'valgalinn.ee', 'www.valgalinn.ee', '18.217.172.167', # a1.medium
    # 'test.valgalinn.ee', '18.217.179.154', # t4g.nano
    '127.0.0.1', 'localhost',
]

ADMINS = [
    ('Kalev', config['superuser']['ADMINEMAIL']),
    # ('Mary', 'mary@example.com')
]

INSTALLED_APPS = [
    'wiki.apps.WikiConfig',
    'ilm.apps.IlmConfig',
    'blog.apps.BlogConfig',
    'kiri.apps.KiriConfig',
    'django_filters', # Laiendatud filtrite jaoks
    'widget_tweaks', # Lisavidinad sisestusvormidele
    'rest_framework', # API liidese jaoks
    'captcha', # Robot vs inimene sisestuse kontroll
    'crispy_forms', # Vormide kujundamiseks
    'markdownx', # MarkDown teksti kasutamiseks
    'ajax_select', # ajax selectväljad
    'corsheaders', # https://github.com/adamchainz/django-cors-headers
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # https://github.com/adamchainz/django-cors-headers
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.PersistentRemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware', # site info lisamiseks
]

ROOT_URLCONF = 'kroonika.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            # PROJECT_DIR.parent / 'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'wiki.context_processors.add_vihjevorm', # Tagasiside vormi lisamine kõigile lehtedele
                'wiki.context_processors.get_cookie_consent_inuse', # cookie consent FF oleku lisamine
            ],
        },
    },
]

WSGI_APPLICATION = 'kroonika.wsgi.application'

LOGIN_REDIRECT_URL = 'algus'
LOGOUT_REDIRECT_URL = 'algus'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'kroonika_db',
        'USER':     config['postgresql']['PSQL_USER'],
        'PASSWORD': config['postgresql']['PSQL_PSWD'],
        'HOST':     'localhost',
        'PORT':     '5432',
        'CONN_MAX_AGE': 600,
        'TEST': {
            'MIRROR': 'default',
        }
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'et'

TIME_ZONE = 'Europe/Tallinn'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATIC_ROOT = BASE_DIR / 'static/'
STATIC_URL = '/static/'

MEDIA_ROOT = BASE_DIR / 'media/'
MEDIA_URL = '/media/'

def FILTERS_VERBOSE_LOOKUPS():
    from django_filters.conf import DEFAULTS
    verbose_lookups = DEFAULTS['VERBOSE_LOOKUPS'].copy()
    verbose_lookups.update({
        'icontains': 'sisaldab',
        'contains': 'sisaldab',
    })
    return verbose_lookups

DATE_INPUT_FORMATS = [
    '%d.%m.%Y',
    '%d.%m.%y',
    ]

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}

# https://www.google.com/recaptcha/intro/v3.html
SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
GOOGLE_RECAPTCHA_SECRET_KEY = config['recaptcha']['GOOGLE_RECAPTCHA_SECRET_KEY']
GOOGLE_RECAPTCHA_PUBLIC_KEY = config['recaptcha']['GOOGLE_RECAPTCHA_PUBLIC_KEY']

# Markdown settings https://python-markdown.github.io/extensions/index.html
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.nl2br',
    'markdown.extensions.sane_lists'
]
MARKDOWNX_SERVER_CALL_LATENCY = 1000 # kujundatud teksti värskendamise viivitus (ms)

# Kroonika üldised seaded
KROONIKA = {
    'TITLE': 'Valga linna kroonika',
    'DESCRIPTION':
        """
        Valga linna kroonika. Lood Valga linna ajaloost seotuna isikute, asutiste ja kohtadega. 
        Kasutamiseks informatsioonilistel ja hariduslikel eesmärkidel.
        """.strip(),
    'KEYWORDS': ['Valga', 'linn', 'Valga linn', 'kroonika', 'ajalugu']
}

# sites framework: django.contrib.sites
SITE_ID = 1

# OpenWeatherMap API
OWM_APIKEY = config['OpenWeatherMap']['OWM_APIKEY']

# DEFINE THE SEARCH CHANNELS:

# AJAX_LOOKUP_CHANNELS = {
#     # simplest way, automatically construct a search channel by passing a dict
#     # 'label': {'model': 'example.label', 'search_field': 'name'},
#
#     # Custom channels are specified with a tuple
#     # channel: ( module.where_lookup_is, ClassNameOfLookup )
#     'objektid': ('wiki.lookups', 'ObjektLookup'),
# }

# Otsingutes kasutamiseks
TRANSLATION = {
    'w': '[vw]',
    'v': '[vw]',
    'y': '[yiī]',
    'ī': '[yiī]',
    'i': '[yiī]',
    's': '[sšzž]',
    'š': '[sšzž]',
    'z': '[sšzž]',
    'ž': '[sšzž]',
    'ā': '[aā]',
    'a': '[aā]',
    'ņ': '[nņ]',
    'n': '[nņ]',
}

# Kasutamiseks genereeritud piltidel
DEFAULT_FONT = "wiki/css/fonts/Raleway/Raleway-Regular.ttf"

# AWS SES credentials
EMAIL_HOST = config['aws_mail']['HOST']
EMAIL_HOST_PASSWORD = config['aws_mail']['PASSWORD_SMTP']
EMAIL_HOST_USER = config['aws_mail']['USERNAME_SMTP']
EMAIL_PORT = config['aws_mail']['PORT']
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = config['aws_mail']['DEFAULT_FROM_EMAIL']

# Indicates the frontend framework django crispy forms use
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# ajax-select no js & css download
# AJAX_SELECT_BOOTSTRAP  = False

# https://github.com/adamchainz/django-cors-headers
CORS_ALLOW_ALL_ORIGINS = True # Lubatakse k6ik
CORS_URLS_REGEX = r"^/api/.*$"

# cookie consent in use?
COOKIE_CONSENT_INUSE = False

# leafleti jaoks
DEFAULT_CENTER = (57.7769268, 26.0308911) # {'lon': 26.0308911, 'lat': 57.7769268} # Jaani kiriku koordinaadid
# DEFAULT_MAP = Kaart.objects.filter(aasta='2021').first() # Vaikimisi OpenStreetMap internetikaart
DEFAULT_MAP_AASTA = '2021'
DEFAULT_MAP_ZOOM_START = 16
DEFAULT_MIN_ZOOM = 13

FUCHSIA = '#FF00FF'
OBJEKT_COLOR = '#2b5797'

GEOJSON_STYLE = {
    'H': {'fill': FUCHSIA, 'color': FUCHSIA, 'weight': 3}, # hoonestus (default)
    'A': {'fill': None, 'color': FUCHSIA, 'weight': 3}, # ala (default)
    'M': {'fill': None, 'color': FUCHSIA, 'weight': 3}, # muu (default)
    'HH': {'fill': 'red', 'color': 'red', 'weight': 3}, # hoonestus (puudub kaasajal)
    'AH': {'fill': None, 'color': 'red', 'weight': 3}, # ala (puudub kaasajal)
    'MH': {'fill': None, 'color': 'red', 'weight': 3}, # muu (puudub kaasajal)
    'HE': {'fill': OBJEKT_COLOR, 'color': OBJEKT_COLOR, 'weight': 3}, # hoonestus (olemas kaasajal)
    'AE': {'fill': None, 'color': OBJEKT_COLOR, 'weight': 3}, # ala (olemas kaasajal)
    'ME': {'fill': None, 'color': OBJEKT_COLOR, 'weight': 3}, # muu (olemas kaasajal),
    'HV': {'fill': FUCHSIA, 'color': FUCHSIA, 'weight': 2, 'dashArray': '2, 5'},  # hoonestus (virtual)
    'AV': {'fill': None, 'color': FUCHSIA, 'weight': 2, 'dashArray': '2, 5'},  # ala (virtual)
    'MV': {'fill': None, 'color': FUCHSIA, 'weight': 2, 'dashArray': '2, 5'},  # muu (virtual)
}

# https://python-visualization.github.io/folium/modules.html#module-folium.map
LEAFLET_DEFAULT_CSS = [
    # ('leaflet_css', 'https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/leaflet.css'),
    ("leaflet_css", "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"),
    ('bootstrap_css', 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css'),
    ('bootstrap_theme_css', 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css'),
    ('awesome_markers_font_css', 'https://maxcdn.bootstrapcdn.com/font-awesome/4.6.3/css/font-awesome.min.css'),
    ('awesome_markers_css', 'https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css'),
    ('awesome_rotate_css', 'https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css')
]
LEAFLET_DEFAULT_JS = [
    # ('leaflet', 'https://unpkg.com/leaflet@1.8.0/dist/leaflet.js'),
    ("leaflet", "https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"),
    ('jquery', 'https://code.jquery.com/jquery-1.12.4.min.js'),
    ('bootstrap', 'https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js'),
    ('awesome_markers', 'https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js')
]

from branca.element import Element
# Kroonika default font kasutamiseks + custom elementide css
LEAFLET_DEFAULT_HEADER = Element(
    '<frame-options policy="SAMEORIGIN" />'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Raleway">'
    '<style>'
    '.kaart-control-layers,'
    '.kaardiobjekt-tooltip,'
    '.kaart-tooltip {'
    '  font-size: 14px;'
    '  font-family: "Raleway", sans-serif;'
    '}'
    '</style>'
)
