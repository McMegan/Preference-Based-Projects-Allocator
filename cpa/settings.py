from pathlib import Path
import environ
import os

env = environ.Env()
environ.Env.read_env()

print('PRODUCTION' if 'WEBSITE_HOSTNAME' in os.environ else 'TESTING')
print(os.getenv('DJANGO_SETTINGS_MODULE')
      if 'DJANGO_SETTINGS_MODULE' in os.environ else 'NO SETTINGS SET')

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = []

if 'CODESPACE_NAME' in os.environ:
    CSRF_TRUSTED_ORIGINS = [
        f'https://{os.getenv("CODESPACE_NAME")}-8000.{os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")}']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'core',
    'manager',
    'student',

    'crispy_forms',
    'crispy_bootstrap5',

    'django_tables2',
    'django_filters',
    'django_bootstrap5',

    'celery',

    'django_browser_reload',
    'debug_toolbar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

ROOT_URLCONF = 'cpa.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'cpa.wsgi.application'


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


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Australia/Melbourne'

USE_I18N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

STATICFILES_DIRS = [BASE_DIR / 'static',]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django Debug Toolbar
INTERNAL_IPS = [
    # ...
    '127.0.0.1',
    # ...
]

# Custom Auth User

AUTH_USER_MODEL = 'core.User'

# LOGIN / LOGOUT REDIRECTION
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = '/login/'

# CRISPY FORMS
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# EMAIL -> BACKEND
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery Settings
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_TIMEZONE = 'Australia/Melbourne'

DJANGO_CELERY_RESULTS_TASK_ID_MAX_LENGTH = 191

# Tables
DJANGO_TABLES2_TEMPLATE = 'django_tables2/bootstrap5-responsive.html'
