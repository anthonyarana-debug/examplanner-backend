from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-cambia-esto-en-produccion')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'api',
    'pagos',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'examplanner.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'examplanner.wsgi.application'

# Base de datos — SQLite para desarrollo, PostgreSQL para producción
if os.getenv('USE_POSTGRES', 'False') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'examplanner'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'api.Estudiante'

LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# JWT — tokens con duración razonable para el uso académico
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS — permite solicitudes desde el emulador Android y web
CORS_ALLOW_ALL_ORIGINS = True

# Canvas API
CANVAS_BASE_URL = os.getenv('CANVAS_BASE_URL', 'https://tecsup.instructure.com')
CANVAS_CLIENT_ID = os.getenv('CANVAS_CLIENT_ID', '')
CANVAS_CLIENT_SECRET = os.getenv('CANVAS_CLIENT_SECRET', '')
CANVAS_REDIRECT_URI = os.getenv('CANVAS_REDIRECT_URI', 'http://localhost:8000/api/canvas/callback/')

# Izipay Sandbox
IZIPAY_SHOP_ID    = os.getenv('IZIPAY_SHOP_ID', '78170250')
IZIPAY_API_KEY    = os.getenv('IZIPAY_API_KEY', 'testpassword_IkSmgnGk8aQ32o1UeeztOgPRayVRLkmHCh3DKRrjhrvHv')
IZIPAY_PUBLIC_KEY = os.getenv('IZIPAY_PUBLIC_KEY', '78170250:testpublickey_0k6QXWZPq5364wp6jSm9ShleP49w2lXoPYVuYpJVZzq7m')
IZIPAY_API_URL    = 'https://api.micuentaweb.pe/api-payment/V4/Charge/CreatePayment'

CSRF_TRUSTED_ORIGINS = ['https://api.stackpe.online', 'https://secure.micuentaweb.pe']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
IZIPAY_HMAC_KEY = os.getenv('IZIPAY_HMAC_KEY', 'VMhd7u3EL6Titj2XfL4AEkehVQ9Vdgb5xU0m6TX1RNN1E')
