import os

from .settings import *

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = INSTALLED_APPS + [
    'whitenoise.runserver_nostatic',
    'django_browser_reload',
    'debug_toolbar'
]

MIDDLEWARE = MIDDLEWARE + [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware'
]

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}

# Celery
REDIS_URL = 'redis://127.0.0.1:6379/0'
CELERY_BROKER_URL = REDIS_URL
result_backend = REDIS_URL
