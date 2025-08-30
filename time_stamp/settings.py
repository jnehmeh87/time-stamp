"""
Django settings for time_stamp project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Add this line near the top of your settings.py file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = []

# If running on Heroku or another production environment
if not DEBUG:
    ALLOWED_HOSTS = ['timestamp-trackr-68fdb365e285.herokuapp.com']
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']


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
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.apple',
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


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

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
if DEBUG:
    # During development, print emails to the console.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # In production, also print emails to the console (Heroku logs) to prevent crashes.
    # For a real application, you would configure a service like SendGrid here.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allauth settings
ACCOUNT_LOGIN_METHODS = ['username', 'email']
ACCOUNT_EMAIL_VERIFICATION = 'optional' # Can be 'mandatory' in production
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
SOCIALACCOUNT_AUTO_SIGNUP = True

# Session duration settings
# Default session expires after 1 day (in seconds)
SESSION_COOKIE_AGE = 86400  # 24 * 60 * 60
# When "Remember Me" is checked, session lasts for 1 year
ACCOUNT_SESSION_COOKIE_AGE = 31536000  # 365 * 24 * 60 * 60
# Ensure the "Remember Me" checkbox is displayed
ACCOUNT_SESSION_REMEMBER = None
SOCIALACCOUNT_ADAPTER = 'tracker.adapters.CustomSocialAccountAdapter'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_SECRET_KEY'), # Corrected typo from GOOGLE_SECRET_SECRET
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    },
    'apple': {
        'APP': {
            # Your service id.
            'client_id': os.environ.get('APPLE_CLIENT_ID'),
            # The Key ID of the private key used to sign the client secret.
            'secret': os.environ.get('APPLE_KEY_ID'),
        },
        # The private key found in your Apple developer account.
        'certificate_key': os.environ.get('APPLE_PRIVATE_KEY'),
        'TEAM': os.environ.get('APPLE_TEAM_ID'),
        'SCOPE': ['name', 'email'],
        'EMAIL_AUTHENTICATION': True,
    }
}

ACCOUNT_FORMS = {
    'signup': 'tracker.forms.CustomSignupForm',
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
