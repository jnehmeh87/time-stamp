"""
Django settings for time_stamp project.
"""

from pathlib import Path
import os
import sys
import dj_database_url
from dotenv import load_dotenv
import io
from google.cloud import secretmanager

# Add this line near the top of your settings.py file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

with open(os.path.join(BASE_DIR, 'VERSION')) as f:
    APP_VERSION = f.read().strip()


# Fetch secrets from Google Cloud Secret Manager
try:
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Your project ID and secret names.
    project_id = "puncha-mera"
    secret_key_name = "django_secret_key"
    database_url_name = "database_url"

    # Build the resource name of the secret version.
    secret_key_version_name = f"projects/{project_id}/secrets/{secret_key_name}/versions/latest"
    database_url_version_name = f"projects/{project_id}/secrets/{database_url_name}/versions/latest"

    # Access the secret versions.
    response = client.access_secret_version(request={"name": secret_key_version_name})
    SECRET_KEY = response.payload.data.decode("UTF-8")

    response = client.access_secret_version(request={"name": database_url_version_name})
    DATABASE_URL = response.payload.data.decode("UTF-8")

except Exception as e:
    # Fallback for local development or if secrets are not found
    print(f"Could not fetch secrets from Secret Manager: {e}")
    SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-development')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')


# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to False in production by default.
# It will be True locally if DATABASE_URL is not set, and False otherwise.
# You can override this by setting the DEBUG environment variable to 'True' or 'False'.
DEBUG = os.environ.get('DEBUG', str('DATABASE_URL' not in os.environ)) == 'True'
 
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'timestamp-trackr-68fdb365e285.herokuapp.com']
CSRF_TRUSTED_ORIGINS = ['https://timestamp-trackr-68fdb365e285.herokuapp.com']


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
    'users.apps.UsersConfig',
    'workspaces',
    'reports.apps.ReportsConfig',
    'invoicing.apps.InvoicingConfig',
    'subscriptions.apps.SubscriptionsConfig',

]

AUTH_USER_MODEL = 'users.CustomUser'

# Add this setting. It's required by django-allauth.
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
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
                'time_stamp.context_processors.version',
            ],
        },
    },
]

WSGI_APPLICATION = 'time_stamp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Use the fetched DATABASE_URL
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL)
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
LOGIN_REDIRECT_URL = 'workspaces:home'
LOGOUT_REDIRECT_URL = 'workspaces:home'
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
    'signup': 'users.forms.CustomSignupForm',
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_dummy')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_dummy')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_dummy')