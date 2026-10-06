"""
Django settings for config project.

Proyecto VillaTech — Django 5.2 LTS.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent  # RUTA DENTRO DEL BACKEND
BASE_DIR_TEMPLATES = (
    Path(__file__).resolve().parent.parent.parent
)  # RUTA PARA TEMPLATES


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/



# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    # local apps
    "apps.landing",
    "apps.inventary",
    "apps.organizations",
    "apps.management",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.management.middleware.LoginRateLimitMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # BASE_DIR / "templates", #ruta base de templates
            os.path.join(
                BASE_DIR_TEMPLATES, "templates"
            ),  # ruta con templates fuera del directorio local
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"







############################################################################################

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT=587
EMAIL_USE_TLS=True


IS_RAILWAY = bool(os.environ.get('RAILWAY_ENVIRONMENT_ID')) or os.environ.get('DEPLOY_TARGET') == 'railway'
IS_PRODUCTION = IS_RAILWAY or os.environ.get('IS_PRODUCTION', '').lower() in ('s','true','1')
SECRET_KEY = os.environ.get('DJ_KEY_SECRET') or ('development-only-change-before-deploy' if not IS_PRODUCTION else '')
if not SECRET_KEY:
    raise RuntimeError('Configura DJ_KEY_SECRET para producción.')
DEBUG = not IS_PRODUCTION
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJ_ALLOWED_HOSTS', '' if IS_PRODUCTION else 'localhost,127.0.0.1,testserver').split(',') if h.strip()]
if IS_RAILWAY and os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS.append(os.environ['RAILWAY_PUBLIC_DOMAIN'])
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR.parent / 'db.sqlite3'}}
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'noreply@localhost'
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
SECURE_SSL_REDIRECT = IS_PRODUCTION
SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
MEDIA_ROOT = BASE_DIR.parent / 'media'
MEDIA_URL = '/media/'
STATIC_ROOT = BASE_DIR.parent / 'staticfiles'
LOGIN_URL = '/gestion/ingresar/'
LOGIN_REDIRECT_URL = '/gestion/'
LOGOUT_REDIRECT_URL = '/gestion/ingresar/'
REST_FRAMEWORK = {'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly']}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-co"

TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"


# carpeta de estaticos en la raiz
STATICFILES_DIRS = [
    BASE_DIR_TEMPLATES / "static",
]


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configure a shared Redis cache in multi-worker production deployments.
if os.environ.get('REDIS_URL'):
    CACHES = {'default': {'BACKEND':'django.core.cache.backends.redis.RedisCache','LOCATION':os.environ['REDIS_URL']}}
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get('CSRF_TRUSTED_ORIGINS','').split(',') if v.strip()]
if IS_RAILWAY and os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    CSRF_TRUSTED_ORIGINS.append('https://' + os.environ['RAILWAY_PUBLIC_DOMAIN'])

# Production deployment overrides. Local development retains SQLite.
DB_ENGINE = os.environ.get('DB_ENGINE', 'postgresql' if IS_RAILWAY or os.environ.get('DATABASE_URL') else 'sqlite')
if DB_ENGINE == 'postgresql' and os.environ.get('DATABASE_URL'):
    from urllib.parse import urlparse, unquote, parse_qs
    db_url = urlparse(os.environ['DATABASE_URL'])
    if db_url.scheme not in ('postgres', 'postgresql') or not db_url.hostname:
        raise RuntimeError('DATABASE_URL debe ser una URL PostgreSQL válida.')
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(db_url.path.lstrip('/')),
        'USER': unquote(db_url.username or ''),
        'PASSWORD': unquote(db_url.password or ''),
        'HOST': db_url.hostname, 'PORT': db_url.port or 5432,
        'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {k: v[-1] for k, v in parse_qs(db_url.query).items() if k in ('sslmode', 'connect_timeout')},
    }}
elif DB_ENGINE == 'postgresql':
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'villatech'),
        'USER': os.environ.get('POSTGRES_USER', 'villatech'),
        'PASSWORD': os.environ['POSTGRES_PASSWORD'],
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True,
    }}
elif DB_ENGINE != 'sqlite':
    raise RuntimeError('DB_ENGINE debe ser sqlite o postgresql.')
else:
    DATABASES['default']['NAME'] = os.environ.get('SQLITE_PATH', str(BASE_DIR.parent / 'db.sqlite3'))
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', '/data/media' if IS_RAILWAY else str(MEDIA_ROOT)))
STATIC_ROOT = Path(os.environ.get('STATIC_ROOT', str(STATIC_ROOT)))
STATIC_URL = '/static/'
if IS_PRODUCTION:
    if len(SECRET_KEY) < 50 or SECRET_KEY == 'development-only-change-before-deploy':
        raise RuntimeError('Usa una DJ_KEY_SECRET aleatoria de al menos 50 caracteres.')
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise RuntimeError('Configura DJ_ALLOWED_HOSTS con dominios explícitos.')
    if DB_ENGINE != 'postgresql' or not os.environ.get('REDIS_URL'):
        raise RuntimeError('Producción requiere PostgreSQL y Redis.')
# Enable only behind the supplied trusted Nginx proxy; Gunicorn is not published.
TRUST_PROXY_HEADERS = os.environ.get('TRUST_PROXY_HEADERS', 'true' if IS_RAILWAY else '').lower() in ('1','true')
if TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '3600' if IS_PRODUCTION else '0'))
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'false').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@localhost')
LOGGING = {'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'}}

# Railway serves TLS at its edge; WhiteNoise serves only collected static assets.
if IS_RAILWAY:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    }
    # Internal Railway health probes use this host and plain HTTP.
    if 'healthcheck.railway.app' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('healthcheck.railway.app')
    SECURE_REDIRECT_EXEMPT = [r'^healthz/$']

# Customer confirmation + private team notification.
CONTACT_NOTIFICATION_EMAIL = os.environ.get('CONTACT_NOTIFICATION_EMAIL', EMAIL_HOST_USER)
PUBLIC_SITE_URL = os.environ.get('PUBLIC_SITE_URL', 'https://' + os.environ['RAILWAY_PUBLIC_DOMAIN'] if os.environ.get('RAILWAY_PUBLIC_DOMAIN') else 'http://localhost:8000')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'resend' if IS_RAILWAY else 'smtp').lower()
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'apps.landing.email_backend.ResendEmailBackend' if EMAIL_PROVIDER == 'resend' else 'django.core.mail.backends.smtp.EmailBackend')
