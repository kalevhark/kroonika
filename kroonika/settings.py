"""
Django settings for kroonika project.

"""
import configparser
import os
from pathlib import Path

# Starting with 3.2 new projects are generated with DEFAULT_AUTO_FIELD set to BigAutoField
# To avoid unwanted migrations in the future, either explicitly set DEFAULT_AUTO_FIELD to AutoField
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = Path(__file__).resolve().parent

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
    'test.valgalinn.ee', '18.217.179.154', # t4g.nano
    '127.0.0.1', 'localhost',
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
        # 'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'wiki.context_processors.add_vihjevorm', # Tagasiside vormi lisamine kõigile lehtedele
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
        # 'ENGINE': 'django.db.backends.postgresql_psycopg2',
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

# STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATIC_ROOT = BASE_DIR / 'static/'
STATIC_URL = '/static/'

# MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
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
    'PAGE_SIZE': 20
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
    'y': '[yi]',
    'i': '[yi]',
    's': '[sšz]',
    'š': '[sšz]',
    'z': '[sšz]'
}

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