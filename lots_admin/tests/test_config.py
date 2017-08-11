SECRET_KEY = 'running man was a good movie'

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