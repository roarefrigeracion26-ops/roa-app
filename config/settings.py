"""
Django settings for ROA APP — SGMAA (Sistema de Gestión de Mantenimiento de Aire Acondicionado).
"""
from pathlib import Path

import environ

env = environ.Env(DEBUG=(bool, False))

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='dev-change-me-in-production')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '.onrender.com'])
# Render inyecta RENDER_EXTERNAL_HOSTNAME; añadirlo si existe
if env('RENDER_EXTERNAL_HOSTNAME', default=''):
    ALLOWED_HOSTS.append(env('RENDER_EXTERNAL_HOSTNAME'))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'inventory',
    'operations',
    'analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db(),
}

# SSL solo para PostgreSQL (evita error en desarrollo con SQLite)
if DATABASES['default'].get('ENGINE', '').endswith('postgresql'):
    DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = 'require'

AUTH_USER_MODEL = 'users.Tecnico'
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'inventory:clientes'
LOGOUT_REDIRECT_URL = 'users:login'

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Archivos subidos por usuarios (fotos). En producción Cloudflare R2 (S3-compatible);
# en desarrollo, disco local.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

R2_ENDPOINT = env('R2_ENDPOINT', default='')
R2_BUCKET = env('R2_BUCKET', default='')

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'OPTIONS': {},
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

if R2_ENDPOINT and R2_BUCKET:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'access_key': env('R2_ACCESS_KEY_ID'),
            'secret_key': env('R2_SECRET_ACCESS_KEY'),
            'bucket_name': R2_BUCKET,
            'endpoint_url': R2_ENDPOINT,
            'region_name': env('R2_REGION', default='auto'),
            'signature_version': 's3v4',
            'addressing_style': 'virtual',
            'querystring_auth': True,
            'querystring_expire': 3600,
            'default_acl': None,
            'file_overwrite': False,
        },
    }

# Límites de subida (fotos comprimidas nunca llegan cerca de esto, es defensa).
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True