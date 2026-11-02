"""Environment-only deployment settings. Local credential-bearing settings are not imported."""
import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def required(name):
    value = os.environ.get(name, '')
    if not value or value.startswith('replace-'):
        raise ImproperlyConfigured(f'Set the {name} environment variable before deployment.')
    return value


SECRET_KEY = required('DJANGO_SECRET_KEY')
DEBUG = False
# Render supplies the exact assigned hostname after service creation.
# Trust only its process environment value, never the incoming Host header.
_render_host = ''
if os.environ.get('RENDER') == 'true':
    import re
    _render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip().lower()
    if _render_host and not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.onrender\.com', _render_host):
        raise ImproperlyConfigured('Invalid Render-assigned hostname.')
_configured_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
if not _configured_hosts and not _render_host:
    required('DJANGO_ALLOWED_HOSTS')
ALLOWED_HOSTS = [value.strip() for value in _configured_hosts.split(',') if value.strip()]
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'base', 'rest_framework', 'rest_framework_simplejwt.token_blacklist']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'backend.production_urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'backend.wsgi.application'
ASGI_APPLICATION = 'backend.asgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': required('DB_NAME'), 'USER': required('DB_USER'), 'PASSWORD': required('DB_PASSWORD'), 'HOST': required('DB_HOST'), 'PORT': os.environ.get('DB_PORT', '5432'), 'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True, 'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'require'), 'connect_timeout': 5}}}
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/images/'
MEDIA_ROOT = BASE_DIR / 'media'
PRIVATE_MEDIA_ROOT = Path(os.environ.get('PRIVATE_MEDIA_ROOT', '/data/private_media'))
FRONTEND_DIST = BASE_DIR.parent / 'frontend' / 'dist'
WHITENOISE_ROOT = str(FRONTEND_DIST)
WHITENOISE_INDEX_FILE = True
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
CSRF_FAILURE_VIEW = 'base.api.csrf_failure'
CSRF_TRUSTED_ORIGINS = [value.strip() for value in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if value.strip()]
if _render_host and 'https://' + _render_host not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append('https://' + _render_host)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# Set this only when the deployment platform supplies a trusted HTTPS reverse proxy.
if os.environ.get('TRUST_PROXY_HEADERS', '').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 4
REST_FRAMEWORK = {'DEFAULT_PARSER_CLASSES': ('base.parsers.ObjectJSONParser', 'rest_framework.parsers.FormParser', 'rest_framework.parsers.MultiPartParser'), 'DEFAULT_AUTHENTICATION_CLASSES': ('base.authentication.SchoolJWTAuthentication',), 'EXCEPTION_HANDLER': 'base.exceptions.api_exception_handler', 'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'], 'DEFAULT_THROTTLE_RATES': {'anon': '120/min', 'user': '240/min'}}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5), 'REFRESH_TOKEN_LIFETIME': timedelta(days=1), 'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': True, 'CHECK_REVOKE_TOKEN': True, 'SIGNING_KEY': required('JWT_SIGNING_KEY'), 'ISSUER': 'tipped-api', 'AUTH_HEADER_TYPES': ('Bearer',)}

GOOGLE_CLIENT_ID = required('GOOGLE_CLIENT_ID')
if not GOOGLE_CLIENT_ID.endswith('.apps.googleusercontent.com'):
    raise ImproperlyConfigured('Set a valid Google Web Client ID.')
ALLOW_PASSWORD_AUTH = False
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Do not accept attacker-controlled X-Forwarded-For as a rate-limit identity.
REST_FRAMEWORK['NUM_PROXIES'] = 0
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'tipped_shared_cache', 'TIMEOUT': 300}}

# A free web host must never write evidence onto its ephemeral filesystem.
PRIVATE_STORAGE_BACKEND = os.environ.get('PRIVATE_STORAGE_BACKEND', 'filesystem')
if PRIVATE_STORAGE_BACKEND not in {'filesystem', 's3'}:
    raise ImproperlyConfigured('Unsupported PRIVATE_STORAGE_BACKEND.')
if os.environ.get('RENDER') == 'true' and PRIVATE_STORAGE_BACKEND != 's3':
    raise ImproperlyConfigured('Render requires configured private object storage.')
if PRIVATE_STORAGE_BACKEND == 's3':
    from urllib.parse import urlsplit
    PRIVATE_STORAGE_ENDPOINT = required('PRIVATE_STORAGE_ENDPOINT')
    endpoint = urlsplit(PRIVATE_STORAGE_ENDPOINT)
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ImproperlyConfigured('Private storage requires a plain HTTPS endpoint without embedded credentials.')
    PRIVATE_STORAGE_ACCESS_KEY = required('PRIVATE_STORAGE_ACCESS_KEY')
    PRIVATE_STORAGE_SECRET_KEY = required('PRIVATE_STORAGE_SECRET_KEY')
    PRIVATE_STORAGE_BUCKET = required('PRIVATE_STORAGE_BUCKET')
    PRIVATE_STORAGE_REGION = required('PRIVATE_STORAGE_REGION')
