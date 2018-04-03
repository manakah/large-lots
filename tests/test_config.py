import os
import pytz
from datetime import datetime

SECRET_KEY = 'running man was a good movie'

CARTODB_API_KEY = ''

CURRENT_CARTODB = ''

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'lots_client',
    'lots_admin',
    'bootstrap_pagination',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'lots.urls'

APPLICATION_DISPLAY = False

DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.postgresql',
       'NAME': 'largelots',
       'USER': '',
       'PASSWORD': '',
       'HOST': 'localhost',
       'PORT': '5432',
   }
}

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "lots", "static"),
)

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

STATIC_ROOT = os.path.join(BASE_DIR, 'lots', 'static')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

CURRENT_PILOT = "pilot_6_dev"

timezone = pytz.timezone('America/Chicago')

CHICAGO_TIME = datetime.now(timezone)

START_DATE = timezone.localize(datetime(2016, 11, 29, 0, 0))

END_DATE = timezone.localize(datetime(2017, 1, 31, 23, 59))

SENTRY_DSN=''