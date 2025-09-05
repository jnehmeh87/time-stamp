"""
Django settings for time_stamp project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Add this line near the top of your settings.py file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to False in production by default.
# It will be True locally unless DEBUG is set to 'False' in the environment.
# On Heroku, set the DEBUG config var to 'False'.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
 
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = []
 
 # Get the production hostname from an environment variable
HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME')
if HEROKU_APP_NAME:
    HEROKU_HOSTNAME = f"{HEROKU_APP_NAME}.herokuapp.com"
    ALLOWED_HOSTS.append(HEROKU_HOSTNAME)
    # This is crucial for allowing logins and form submissions on your deployed site.
    CSRF_TRUSTED_ORIGINS.append(f'https://{HEROKU_HOSTNAME}')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites', # Required by allauth

    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'widget_tweaks',
    'django_countries',
    'crispy_forms',
    'crispy_bootstrap5',

    # Local
    'tracker.apps.TrackerConfig',

]

# Add this setting. It's required by django-allauth.
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'tracker.middleware.TimezoneMiddleware',
    'tracker.middleware.ClearSocialSessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'time_stamp.urls'

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

WSGI_APPLICATION = 'time_stamp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Default to SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
# If DATABASE_URL is set in the environment, use it for production (e.g., on Heroku)
if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

    # --- Production Security Settings ---
    # These settings are crucial for security when DEBUG is False.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # This header is used by Heroku to tell Django that the request is secure.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
# During development and for this Heroku setup, print emails to the console.
# For a real production app, you would configure a service like SendGrid or Mailgun.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allauth settings
ACCOUNT_LOGIN_METHODS = ['username', 'email']
ACCOUNT_EMAIL_VERIFICATION = 'optional' # Can be 'mandatory' in production
LOGIN_REDIRECT_URL = 'tracker:home'
LOGOUT_REDIRECT_URL = 'tracker:home'
SOCIALACCOUNT_AUTO_SIGNUP = True

# Session duration settings
# Default session expires after 1 day (in seconds)
SESSION_COOKIE_AGE = 86400  # 24 * 60 * 60
# When "Remember Me" is checked, session lasts for 1 year
# Update the session cookie on every request to prevent timeouts during active use.
SESSION_SAVE_EVERY_REQUEST = True
ACCOUNT_SESSION_COOKIE_AGE = 31536000  # 365 * 24 * 60 * 60
# Ensure the "Remember Me" checkbox is displayed
ACCOUNT_SESSION_REMEMBER = None
SOCIALACCOUNT_ADAPTER = 'tracker.adapters.CustomSocialAccountAdapter'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {}

# Conditionally enable Google provider if credentials are set
if os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_SECRET_KEY'):
    INSTALLED_APPS.append('allauth.socialaccount.providers.google')
    SOCIALACCOUNT_PROVIDERS['google'] = {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_SECRET_KEY'),
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
            'prompt': 'select_account', # This will force the account chooser
        }
    }

# Conditionally enable Apple provider if all credentials are set
# This prevents crashes if environment variables are missing.
if all(os.environ.get(key) for key in ['APPLE_CLIENT_ID', 'APPLE_KEY_ID', 'APPLE_PRIVATE_KEY', 'APPLE_TEAM_ID']):
    INSTALLED_APPS.append('allauth.socialaccount.providers.apple')
    SOCIALACCOUNT_PROVIDERS['apple'] = {
        'APP': {
            'client_id': os.environ.get('APPLE_CLIENT_ID'),
            'secret': os.environ.get('APPLE_KEY_ID'),
        },
        'certificate_key': os.environ.get('APPLE_PRIVATE_KEY'),
        'TEAM': os.environ.get('APPLE_TEAM_ID'),
        'SCOPE': ['name', 'email'],
        'EMAIL_AUTHENTICATION': True,
    }

ACCOUNT_FORMS = {
    'signup': 'tracker.forms.CustomSignupForm',
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
